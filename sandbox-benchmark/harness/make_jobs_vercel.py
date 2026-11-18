"""Vercel Sandbox job grid. Same job kinds, repos, modes, and reps per cell as
make_jobs.py / make_jobs_instabox.py. Two cells: Vercel default Medium (2 vCPU / 4 GiB)
and Large (4 / 8). Writes vercel/results/jobs_vercel*.json."""

import json
import os


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(H)
OUT = f"{ROOT}/vercel/results"
os.makedirs(OUT, exist_ok=True)
CELLS = [("vercel", "default", s) for s in ("medium", "large")]
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
_dump_json(f"{OUT}/jobs_vercel.json", "w", J, indent=0)
_dump_json(
    f"{OUT}/jobs_vercel_pilot.json",
    "w",
    [
        {"provider": "vercel", "type": "default", "shape": s, "kind": "lifecycle", "rep": 0}
        for s in ("medium", "large")
    ],
    indent=0,
)
print(len(J), "jobs")
