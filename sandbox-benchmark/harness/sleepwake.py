"""Persistence and sleep/wake for a long-running agent. One instance per provider: write a file and start a background counter process,
then CYCLES x (sleep -> wait IDLE s -> first command) and record wake latency, file survival, process survival.
Agent37: POST /sleep (checkpoint) and exec wakes it. Daytona: stop/start (no checkpointed sleep). InstaBox: POST /suspend (memory saved to disk) and POST /resume, then exec (a manual pause does not wake on exec). Vercel: sandbox.stop() (automatic filesystem snapshot, memory and processes dropped), woken either by an explicit resume_sandbox (default, VC_WAKE=resume) or by the first command, which auto-resumes it (VC_WAKE=auto; use a distinct rep such as a0 so result files do not collide).
Usage: sleepwake.py <provider> <shape> <cycles> <idle_s> <outdir> [rep]"""

import json
import os
import sys
import time
import traceback


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import providers as P

prov, shape, C, idle, outdir = (
    sys.argv[1],
    sys.argv[2],
    int(sys.argv[3]),
    int(sys.argv[4]),
    sys.argv[5],
)
rep = sys.argv[6] if len(sys.argv) > 6 else "0"
os.makedirs(outdir, exist_ok=True)
pv = P.provider(prov)
R = {
    "retries_note": "instabox and vercel retries are in R.retries",
    "wake_mode": os.environ.get("VC_WAKE", "resume") if prov == "vercel" else None,
    "provider": prov,
    "shape": shape,
    "cycles": [],
    "start": time.time(),
}
b = None
try:
    b, cs = pv.create(shape, "default", f"sleepwake-keep-{rep}")
    R.update(id=b.id, create_s=round(cs, 2))
    pv.exec(
        b,
        f"echo persisted > {b.home}/marker && (nohup sh -c 'i=0; while true; do i=$((i+1)); echo $i > /tmp/counter; sleep 1; done' >/dev/null 2>&1 &) ; echo started",
    )
    for c in range(C):
        time.sleep(20)
        rc, before = pv.exec(b, "cat /tmp/counter")
        t = time.time()
        pv.sleep(b)
        sl = time.time() - t
        time.sleep(idle)
        t = time.time()
        err = None
        for a in range(30):
            try:
                if prov in ("daytona", "instabox") or (
                    prov == "vercel" and os.environ.get("VC_WAKE", "resume") == "resume"
                ):
                    pv.wake(b)
                rc, out = pv.exec(
                    b,
                    f'cat {b.home}/marker; cat /tmp/counter 2>/dev/null || echo NOCOUNTER; pgrep -f "sleep 1" >/dev/null && echo PROC || echo NOPROC',
                )
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                time.sleep(5)
        R["cycles"].append(
            {
                "cycle": c,
                "sleep_call_s": round(sl, 2),
                "wake_to_first_cmd_s": round(time.time() - t, 2),
                "resume_call_s": getattr(b, "last_wake_s", None),
                "counter_before": before.strip(),
                "after": out.strip().splitlines(),
                "last_err": err,
            }
        )
        print(prov, c, R["cycles"][-1], flush=True)
except Exception:  # noqa: BLE001
    R["error"] = traceback.format_exc()[-1500:]
finally:
    if b:
        R["deleted"] = pv.delete(b, "sleepwake")
    if prov in ("instabox", "vercel"):
        R["retries"] = dict(pv.retries)
    R["life_s"] = round(time.time() - R["start"], 2)
    _dump_json(f"{outdir}/sleepwake__{prov}__{shape}__r{rep}.json", "w", R)
