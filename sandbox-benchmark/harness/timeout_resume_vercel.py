"""Vercel only: the session-timeout analogue of an auto-sleep.

A sandbox is created with a short session time limit (execution_time_limit).
Vercel stops the session itself when it expires (persistent sandbox: filesystem
snapshotted), and the next plain command auto-resumes it (no explicit resume
call). Records how long the stop took after the limit and the command that
wakes it.

Usage: timeout_resume_vercel.py <shape> <cycles> <limit_s> <outdir> [rep]
"""

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

shape, C, limit, outdir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
rep = sys.argv[5] if len(sys.argv) > 5 else "0"
os.makedirs(outdir, exist_ok=True)
pv = P.provider("vercel")
R = {
    "provider": "vercel",
    "shape": shape,
    "limit_s": limit,
    "cycles": [],
    "start": time.time(),
    "mode": "session-timeout-autoresume",
}
b = None
try:
    b, cs = pv.create(shape, "default", f"timeout-keep-{rep}", timeout_s=limit)
    R.update(id=b.id, create_s=round(cs, 2))
    t_create = time.time()
    pv.exec(b, f"echo persisted > {b.home}/marker")
    for c in range(C):
        t0 = time.time()
        st = None
        stopped_after = None
        while time.time() - t0 < limit * 3 + 120:
            time.sleep(5)
            try:
                st = str(pv.S.get_sandbox(name=b.id).status)
            except Exception as e:  # noqa: BLE001
                st = "err " + str(e)[:60]
                continue
            if "stopped" in st.lower():
                stopped_after = time.time() - t_create
                break
        time.sleep(10)
        t = time.time()
        err = None
        out = ""
        for a in range(5):
            try:
                rc, out = pv.exec(b, f"cat {b.home}/marker")
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                time.sleep(5)
        w = time.time() - t
        R["cycles"].append(
            {
                "cycle": c,
                "status_before": st,
                "stopped_after_session_start_s": round(stopped_after, 1) if stopped_after else None,
                "wake_to_first_cmd_s": round(w, 2),
                "file_kept": "persisted" in out,
                "last_err": err,
            }
        )
        print(R["cycles"][-1], flush=True)
        t_create = t  # a new session started at the first command
except Exception:  # noqa: BLE001
    R["error"] = traceback.format_exc()[-1500:]
finally:
    if b:
        R["deleted"] = pv.delete(b, "timeout")
    R["retries"] = dict(pv.retries)
    R["life_s"] = round(time.time() - R["start"], 2)
    _dump_json(f"{outdir}/timeout_resume__vercel__{shape}__r{rep}.json", "w", R)
