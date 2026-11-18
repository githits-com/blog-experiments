"""InstaBox billed vs modeled. Reads GET /v1/usage (cost for the month so far, rated hourly, so it lags up to an hour) and the sandboxes the harness created
(results/sandboxes.jsonl). Pro includes monthly credits and 200 GiB of disk across machines, so billed cost shows up as credit use.
Writes out/billing_instabox.md and out/billing_instabox.json. Needs INSTABOX_API_KEY (never printed)."""

import collections
import json
import os
import sys
import time


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


def _write_open(path, mode, text):
    with open(path, mode) as handle:
        handle.write(text)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = f"{ROOT}/results/sandboxes.jsonl"
if not os.path.isfile(path):
    sys.exit(
        "No results/sandboxes.jsonl. This repository stores code only; run output is not committed.\n"
        "Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n"
        "Reproduce with the InstaBox commands in README.md, then re-run this script."
    )
import requests

u = requests.get(
    "https://api.instabox.sh/v1/usage",
    headers={"X-API-Key": os.environ["INSTABOX_API_KEY"]},
    timeout=30,
).json()
c = u["cost"]
with open(path) as handle:
    ev = [json.loads(l) for l in handle if '"instabox"' in l]
life = collections.defaultdict(dict)
for e in ev:
    life[e["id"]][e["event"]] = e["t"]
sys.path.insert(0, f"{ROOT}/harness")

mod = 0.0
hrs = 0.0
n = 0
for d in life.values():
    if "created" in d and "deleted" in d:
        n += 1
        hrs += (d["deleted"] - d["created"]) / 3600
out = {
    "read_at": time.time(),
    "cost": c,
    "limits": u.get("limits"),
    "machines_now": u.get("machines"),
    "sandboxes_created_and_deleted": n,
    "wall_sandbox_hours_created_to_deleted": round(hrs, 3),
}
os.makedirs(f"{ROOT}/out", exist_ok=True)
_dump_json(f"{ROOT}/out/billing_instabox.json", "w", out, indent=1)
T = [
    "# InstaBox: billed (GET /v1/usage) vs sandbox lifetime\n",
    f"Read {time.strftime('%Y-%m-%d %H:%M %Z')}; the ledger is rated hourly, so figures lag by up to an hour (`ratedUntil` {c.get('ratedUntil')}).\n",
    "| field | value |\n|---|---|",
] + [
    f"| {k} | {c.get(k)} |"
    for k in (
        "vcpuHours",
        "memGiBHours",
        "storageGiBHours",
        "egressGiB",
        "vcpuUSD",
        "memUSD",
        "storageUSD",
        "egressUSD",
        "costUSD",
        "allowanceUSD",
        "creditRemainingUSD",
        "overageUSD",
        "creditsUSD",
        "creditsUsedUSD",
        "billableDiskGiB",
        "includedDiskGiB",
    )
]
T.append(
    f"\nSandboxes created and deleted by the harness (all, including pilot/smoke/soak): {n}; created-to-deleted wall time {round(hrs, 2)} h. Note `vcpuHours` counts only the time a machine is `running` (not paused, not starting)."
)
_write_open(f"{ROOT}/out/billing_instabox.md", "w", "\n".join(T) + "\n")
print("\n".join(T))
