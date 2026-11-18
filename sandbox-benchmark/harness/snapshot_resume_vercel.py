"""Vercel only: snapshot-based resume, the closest equivalent to a checkpointed
sleep when explicit stop/resume is already covered by sleepwake.py.

One chain per run: create a sandbox, write a marker file and start a background
counter, then CYCLES x (snapshot the current sandbox -> idle IDLE s -> create a
NEW sandbox from that snapshot -> first command -> read marker + two counter
reads 2 s apart). The restored sandbox becomes the next producer.

Records snapshot time, restore create time, restore + first command, file kept,
process kept (counter advances), snapshot size. Deletes every sandbox and
snapshot it made (also on error).

Usage: snapshot_resume_vercel.py <shape> <cycles> <idle_s> <outdir> [rep]
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
from vercel.sandbox import SandboxResources, SnapshotSource

shape, C, idle, outdir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
rep = sys.argv[5] if len(sys.argv) > 5 else "0"
os.makedirs(outdir, exist_ok=True)
pv = P.provider("vercel")
S = pv.S
R = {
    "provider": "vercel",
    "shape": shape,
    "cycles": [],
    "start": time.time(),
    "mode": "snapshot-restore",
}
b = None
snaps = []
made = []
try:
    b, cs = pv.create(shape, "default", f"snaprestore-keep-{rep}")
    R.update(id=b.id, create_s=round(cs, 2))
    made.append(b)
    pv.exec(
        b,
        f"echo persisted > {b.home}/marker && (nohup sh -c 'i=0; while true; do i=$((i+1)); echo $i > /tmp/counter; sleep 1; done' >/dev/null 2>&1 &) ; echo started",
    )
    c_, m_, d_ = P.SHAPES[shape]
    for c in range(C):
        time.sleep(20)
        rc, before = pv.exec(b, "cat /tmp/counter")
        t = time.time()
        snap = b.raw.snapshot()
        sn = time.time() - t
        snaps.append(snap)
        time.sleep(idle)
        t = time.time()
        err = None
        nb = None
        out = ""
        create_s = None
        first = None
        for a in range(5):
            try:
                tc = time.time()
                name = f"snap-{rep}-{c}-{int(time.time()) % 100000}-{a}"
                sb = S.create_sandbox(
                    source=SnapshotSource(snapshot_id=snap.id),
                    resources=SandboxResources(vcpus=c_, memory=m_ * 1024),
                    execution_time_limit=3600,
                    tags={"exp": P.LABEL, "tag": f"snaprestore-{rep}"},
                )
                create_s = time.time() - tc
                nb = P.Box("vercel", sb.name, b.home, sb, shape, "default")
                P.track(
                    {
                        "provider": "vercel",
                        "id": sb.name,
                        "tag": "snaprestore",
                        "event": "created",
                        "shape": shape,
                        "type": "default",
                        "from_snapshot": snap.id,
                    }
                )
                made.append(nb)
                t1 = time.time()
                rc, out = pv.exec(
                    nb,
                    f'cat {b.home}/marker; a=$(cat /tmp/counter 2>/dev/null || echo NOCOUNTER); sleep 2; b=$(cat /tmp/counter 2>/dev/null || echo NOCOUNTER); echo "$a $b"',
                )
                first = time.time() - t1
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                time.sleep(5)
        lines = out.strip().splitlines() if nb else []
        kept = None
        try:
            a_, b_ = lines[1].split()
            kept = a_ != "NOCOUNTER" and int(b_) > int(a_)
        except Exception:  # noqa: BLE001, S110
            pass
        R["cycles"].append(
            {
                "cycle": c,
                "snapshot_call_s": round(sn, 2),
                "snapshot_id": snap.id,
                "snapshot_size_b": getattr(snap, "size_bytes", None),
                "restore_create_s": round(create_s, 2) if nb else None,
                "restore_to_first_cmd_s": round(time.time() - t, 2),
                "first_cmd_s": round(first, 3) if nb else None,
                "file_kept": bool(lines and "persisted" in lines[0]),
                "process_kept": kept,
                "counter_before": before.strip(),
                "after": lines,
                "last_err": err,
            }
        )
        print(R["cycles"][-1], flush=True)
        if nb:
            pv.delete(b, "snaprestore")
            b = nb
        else:
            break
except Exception:  # noqa: BLE001
    R["error"] = traceback.format_exc()[-1500:]
finally:
    ok = []
    for x in made:
        try:
            ok.append(pv.delete(x, "snaprestore"))
        except Exception:  # noqa: BLE001
            ok.append(False)
    sd = []
    for sn in snaps:
        try:
            sn.delete()
            sd.append(True)
        except Exception as e:  # noqa: BLE001
            sd.append(str(e)[:100])
    R["deleted_sandboxes"] = ok
    R["deleted_snapshots"] = sd
    R["retries"] = dict(pv.retries)
    R["life_s"] = round(time.time() - R["start"], 2)
    _dump_json(f"{outdir}/snapshot_resume__vercel__{shape}__r{rep}.json", "w", R)
