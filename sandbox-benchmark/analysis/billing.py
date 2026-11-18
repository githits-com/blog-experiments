"""Billed vs modeled, Agent37: GET /v1/usage lists compute spend per instance id (settled hourly; run this >1 h after the last job).
Compares each instance's billed compute_micros with life_s x published rate, exact and rounded up to whole minutes. Writes out/billing.json and out/billing.md.
Daytona has no per-sandbox billing endpoint in our harness; its billed total is read from the Daytona dashboard by hand and recorded in out/billing.md."""

import datetime
import glob
import json
import math
import os
import sys


def _load_json(path):
    with open(path) as handle:
        return json.load(handle)


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


def _write_open(path, mode, text):
    with open(path, mode) as handle:
        handle.write(text)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/harness")
import providers as P

if not (glob.glob(f"{ROOT}/results/runs*/*.json") or glob.glob(f"{ROOT}/results/smoke/*.json")):
    sys.exit(
        "No benchmark JSON under results/. This repository stores code only; run output is not committed.\n"
        "Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n"
        "Reproduce with ./run.sh, or the InstaBox commands in README.md, then re-run this script."
    )
pv = P.Agent37()
today = datetime.date.today()
u = pv.get("/usage", params={"from": str(today - datetime.timedelta(days=3)), "to": str(today)})
billed = {i["id"]: i["compute_micros"] / 1e6 for i in u.get("instances", [])}
life = {}
for f in glob.glob(f"{ROOT}/results/runs*/*.json") + glob.glob(f"{ROOT}/results/smoke/*.json"):
    r = _load_json(f)
    j = r.get("job") or r
    if r.get("id") and j.get("provider") == "agent37":
        life[r["id"]] = (r["life_s"], j["shape"], j["type"])
rows = []
for i, (s, sh, ty) in life.items():
    rt = P.rate_per_s("agent37", sh, ty)
    rows.append(
        {
            "id": i,
            "life_s": s,
            "billed": billed.get(i),
            "exact": s * rt,
            "minutes": math.ceil(s / 60) * 60 * rt,
        }
    )
tot = lambda k: round(sum(r[k] or 0 for r in rows), 4)
out = {
    "instances": len(rows),
    "billed_found": sum(1 for r in rows if r["billed"] is not None),
    "billed": tot("billed"),
    "modeled_exact": tot("exact"),
    "modeled_whole_minutes": tot("minutes"),
    "workspace_compute_total": u["by_integration"]["compute"]["cost_micros"] / 1e6,
}
os.makedirs(f"{ROOT}/out", exist_ok=True)
_dump_json(f"{ROOT}/out/billing.json", "w", {"summary": out, "rows": rows}, indent=1)
_write_open(
    f"{ROOT}/out/billing.md",
    "w",
    "# Billed vs modeled (Agent37)\n\n" + "\n".join(f"- {k}: {v}" for k, v in out.items()) + "\n",
)
print(out)
