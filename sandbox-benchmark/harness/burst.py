"""Burst creation: fire N creates at once on one provider (default type, medium), record per-create latency and every API error, then delete all.
Usage: burst.py <provider> <N> <wave> <outdir> [retry]. N must fit the account's instance limit (Agent37 tier 2 = 50 instances, counting every undeleted one)."""

import json
import os
import sys
import threading
import time


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import providers as P

prov, N, wave, outdir = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
os.makedirs(outdir, exist_ok=True)
retry = (
    len(sys.argv) > 5 and sys.argv[5] == "retry"
)  # InstaBox and Vercel: honour 429 retries (default off). For Vercel, retry also leaves the SDK's own 2 retries on; without it they are switched off so errors are recorded, as for the others.
pv = P.provider(prov)
res = [None] * N
go = threading.Event()
if hasattr(pv, "retry"):
    pv.retry = retry


def one(i):
    go.wait()
    t = time.time()
    r = {"i": i, "t0": t}
    try:
        b, cs = pv.create("medium", "default", f"burst-{wave}-{i}")
        r.update(id=b.id, create_s=round(cs, 2))
        t1 = time.time()
        pv.exec(b, "true")
        r["first_cmd_s"] = round(time.time() - t1, 3)
        r["box"] = b
    except P.ProviderError as e:
        r["error"] = {"http": e.http, "code": e.code, "msg": str(e)[:200]}
    except Exception as e:  # noqa: BLE001
        r["error"] = {"exc": str(e)[:300]}
    r["ready_s"] = round(time.time() - t, 2)
    res[i] = r


ts = [threading.Thread(target=one, args=(i,)) for i in range(N)]
[t.start() for t in ts]
T = time.time()
go.set()
[t.join() for t in ts]
wall = time.time() - T
for r in res:
    b = r.pop("box", None)
    if b:
        td = time.time()
        r["deleted"] = pv.delete(b, f"burst-{wave}")
        r["delete_s"] = round(time.time() - td, 2)
_dump_json(
    f"{outdir}/burst__{prov}__N{N}__{wave}.json",
    "w",
    {
        "provider": prov,
        "N": N,
        "wave": wave,
        "retry": retry,
        "retries": getattr(pv, "retries", None),
        "wall_s": round(wall, 2),
        "runs": res,
    },
)
ok = sum(1 for r in res if "error" not in r)
print(
    prov,
    N,
    wave,
    "ok",
    ok,
    "wall",
    round(wall, 1),
    "errors",
    [r["error"] for r in res if "error" in r][:5],
)
