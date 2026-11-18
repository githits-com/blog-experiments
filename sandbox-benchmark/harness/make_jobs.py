"""Writes the job grid. Reps per cell are set here; see DESIGN.md."""

import json
import os


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(H)
CELLS = [("daytona", "default", s) for s in ("medium", "large")] + [
    ("agent37", t, s) for t in ("default", "vm", "performance") for s in ("medium", "large")
]
REPOS = ["vercel/next.js", "pytorch/pytorch", "kubernetes/kubernetes"]
REPS = {"lifecycle": 10, "clone": 5, "mem": 5, "disk": 3}
J = []
for p, t, s in CELLS:
    base = {"provider": p, "type": t, "shape": s}
    J += [dict(base, kind="lifecycle", rep=r) for r in range(REPS["lifecycle"])]
    J += [
        dict(base, kind="clone", repo=repo, mode=m, rep=r)
        for repo in REPOS
        for m in ("full", "shallow")
        for r in range(REPS["clone"])
    ]
    J += [dict(base, kind="mem", rep=r) for r in range(REPS["mem"])]
    J += [dict(base, kind="disk", rep=r) for r in range(REPS["disk"])]
# interleave so every cell starts early and cold-start/time-of-day effects spread across cells
J.sort(
    key=lambda j: (
        j["rep"],
        j["kind"],
        j.get("repo", ""),
        j.get("mode", ""),
        j["provider"],
        j["type"],
        j["shape"],
    )
)
os.makedirs(f"{ROOT}/results", exist_ok=True)
_dump_json(f"{ROOT}/results/jobs_full.json", "w", J, indent=0)
smoke = [
    {"provider": p, "type": t, "shape": "medium", "kind": "lifecycle", "rep": 0}
    for p, t, _ in CELLS
    if _ == "medium"
]
_dump_json(f"{ROOT}/results/jobs_pilot.json", "w", smoke, indent=0)
from collections import Counter

print(len(J), "jobs", Counter((j["provider"], j["type"], j["shape"]) for j in J))
print("pilot", len(smoke))
