"""Modeled Vercel spend for everything this experiment created. Writes
vercel/out/spend.md and spend.json.

Model = Vercel list prices (Pro, iad1): provisioned memory $0.0212/GB-h
(1 min minimum), Active CPU $0.128/vCPU-h, creations $0.60 per million,
snapshot storage $0.08/GB-month.

- Grid jobs (runs_pilot, runs_vercel, runs_vercel_failed_first_attempt, smoke):
  memory over the job life + Active CPU from the guest busy time read at the
  end of each job (/proc/stat).
- Everything else (bursts, sleep/wake, snapshot-restore, timeout-resume, and
  any other tracked sandbox): charged from create to delete as if ALL its
  vCPUs were busy the whole time (a deliberate upper bound; stopped periods
  are not billed by Vercel, and these sandboxes run mostly idle).
- Snapshots: every snapshot recorded in the sleep/wake, snapshot-restore, and
  timeout-resume result files, charged at the storage rate for one hour each
  (upper bound; cleanup deletes them). Size defaults to 0.84 GB if the result
  file has no size_bytes.

This is a model, not a bill. Confirm billed amounts on the Vercel Usage page.
The harness cap (SPEND_CAP_VC) applies only to new grid jobs; total modeled
spend is compared here to SPEND_CAP_TOTAL_VC (default $25).
"""

import collections
import glob
import json
import os
import sys


def _load_json(path):
    with open(path) as handle:
        return json.load(handle)


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


def _read_open(*args):
    with open(*args) as handle:
        return handle.read()


def _write_open(path, mode, text):
    with open(path, mode) as handle:
        handle.write(text)


V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(V)
sys.path.insert(0, f"{ROOT}/harness")
import providers as P

CAP = float(os.environ.get("SPEND_CAP_TOTAL_VC", "25"))
SNAP_GB = 0.84
SNAP_GB_MONTH = 0.08


def L(pat):
    return [_load_json(f) for f in glob.glob(pat)]


def _need_results():
    if (
        L(f"{V}/results/runs_vercel/*.json")
        or L(f"{V}/results/runs_pilot/*.json")
        or L(f"{V}/results/burst/*.json")
        or L(f"{V}/results/sleepwake/*.json")
        or os.path.exists(f"{ROOT}/results/sandboxes.jsonl")
    ):
        return
    sys.exit(
        "No Vercel run output under vercel/results/ or results/sandboxes.jsonl. "
        "This repository stores code only. Reproduce with the commands in vercel/VERCEL.md, then re-run."
    )


_need_results()
parts = {}


def grid(name, pat):
    rs = L(pat)
    parts[name] = {
        "n": len(rs),
        "usd": sum(
            P.vc_cost(r["life_s"], r["job"]["shape"], r.get("vc_cpu_busy_s") or 0)
            for r in rs
            if r.get("id")
        ),
        "sandboxes": sum(1 for r in rs if r.get("id")),
    }


grid("grid (runs_vercel, final)", f"{V}/results/runs_vercel/*.json")
grid(
    "grid first attempts that failed",
    f"{V}/results/runs_vercel_failed_first_attempt/*.json",
)
grid("pilot", f"{V}/results/runs_pilot/*.json")
if L(f"{V}/results/smoke/*.json"):
    grid("smoke", f"{V}/results/smoke/*.json")
elif L(f"{ROOT}/results/smoke/vercel__*.json"):
    grid("smoke", f"{ROOT}/results/smoke/vercel__*.json")

ev = collections.defaultdict(dict)
tag = {}
tracker = f"{ROOT}/results/sandboxes.jsonl"
if os.path.exists(tracker):
    with open(tracker) as handle:
        for line in handle:
            e = json.loads(line)
            if e.get("provider") != "vercel":
                continue
            ev[e["id"]][e["event"]] = e["t"]
            tag[e["id"]] = e.get("tag", tag.get(e["id"], ""))
            ev[e["id"]]["shape"] = e.get("shape", ev[e["id"]].get("shape", "medium"))

other = collections.defaultdict(lambda: {"n": 0, "usd": 0.0, "hours": 0.0})
unclosed = []
for i, d in ev.items():
    tg = tag[i]
    if tg.startswith("vercel__default__") or tg == "smoke":
        continue  # grid and smoke jobs are costed from their result files
    if "created" not in d:
        continue
    end = d.get("deleted") or d.get("deleted_by_cleanup")
    if not end:
        unclosed.append(i)
        continue
    sh = d.get("shape") or "medium"
    c, m, _ = P.SHAPES[sh]
    h = (end - d["created"]) / 3600
    kind = (
        "burst"
        if tg.startswith("burst")
        else "sleepwake"
        if tg.startswith("sleepwake")
        else "snapshot-restore"
        if tg.startswith("snaprestore")
        else "timeout-resume"
        if tg.startswith("timeout")
        else "other"
    )
    cost = max(h * 3600, 60) / 3600 * m * P.VC_GB_H + h * c * P.VC_CPU_H + P.VC_CREATE
    o = other[kind]
    o["n"] += 1
    o["usd"] += cost
    o["hours"] += h

# One snapshot per recorded stop/snapshot cycle. Prefer measured size_bytes; else SNAP_GB.
snap_gb_hours = 0.0
snap_n = 0
for f in glob.glob(f"{V}/results/sleepwake/*.json"):
    rec = _load_json(f)
    for cyc in rec.get("cycles", []):
        snap_n += 1
        gb = (cyc.get("snapshot_size_b") or 0) / 1e9 or SNAP_GB
        snap_gb_hours += gb * 1.0  # 1 h upper bound
snap_usd = snap_n * 0 if snap_n == 0 else (snap_gb_hours * SNAP_GB_MONTH / 730)

tot = sum(p["usd"] for p in parts.values()) + sum(o["usd"] for o in other.values()) + snap_usd
out = {
    "parts": parts,
    "other": {k: dict(v) for k, v in other.items()},
    "snapshot_count": snap_n,
    "snapshot_storage_usd_upper_bound": snap_usd,
    "sandboxes_unclosed_in_tracker": unclosed,
    "total_modeled_usd": round(tot, 3),
    "cap_usd": CAP,
    "under_cap": tot <= CAP,
}
os.makedirs(f"{V}/out", exist_ok=True)
_dump_json(f"{V}/out/spend.json", "w", out, indent=1)
T = [
    f"# Vercel modeled spend (cap ${CAP:g})\n",
    "| part | sandboxes | USD (modeled) |\n|---|---|---|",
]
T += [f"| {k} | {v['sandboxes']} | {v['usd']:.3f} |" for k, v in parts.items()]
T += [
    f"| {k} (upper bound, all vCPUs busy while alive) | {v['n']} | {v['usd']:.3f} |"
    for k, v in sorted(other.items())
]
T += [
    f"| snapshot storage (~{snap_n} snapshots, 1 h each, upper bound) | | {snap_usd:.5f} |",
    f"| **total** | | **{tot:.3f}** |",
    "",
    f"Sandboxes with a create but no delete in the tracker: {unclosed or 'none'}.",
    f"Compared to cap ${CAP:g}: {'under' if tot <= CAP else 'OVER'} cap.",
    "",
    _read_open(__file__).split('"""')[1].strip(),
]
_write_open(f"{V}/out/spend.md", "w", "\n".join(T) + "\n")
print("\n".join(T[:20]))
