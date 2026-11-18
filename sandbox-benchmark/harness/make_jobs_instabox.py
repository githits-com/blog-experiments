"""InstaBox job grid (added after the Agent37/Daytona run; Pro workspace). Same job kinds, repos, modes and reps per cell as make_jobs.py,
two cells: instabox default Medium (2 vCPU / 4 GiB) and Large (4 / 8). Writes results/jobs_instabox.json (kept apart so the original jobs_full.json is untouched)."""

import json
import os


def _dump_json(path, mode, obj, **kwargs):
    with open(path, mode) as handle:
        json.dump(obj, handle, **kwargs)


H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(H)
CELLS = [("instabox", "default", s) for s in ("medium", "large")]
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
os.makedirs(f"{ROOT}/results", exist_ok=True)
_dump_json(f"{ROOT}/results/jobs_instabox.json", "w", J, indent=0)
_dump_json(
    f"{ROOT}/results/jobs_instabox_pilot.json",
    "w",
    [
        {"provider": "instabox", "type": "default", "shape": s, "kind": "lifecycle", "rep": 0}
        for s in ("medium", "large")
    ],
    indent=0,
)
# Follow-ups: lifecycle inside the 30-starts/minute limit, and a Large template check. Template comes from INSTABOX_TEMPLATE.
_dump_json(
    f"{ROOT}/results/jobs_instabox_lifecycle_rerun.json",
    "w",
    [
        {"provider": "instabox", "type": "default", "shape": s, "kind": "lifecycle", "rep": r}
        for s in ("medium", "large")
        for r in range(REPS["lifecycle"])
    ],
    indent=0,
)
_dump_json(
    f"{ROOT}/results/jobs_instabox_universal.json",
    "w",
    [
        {"provider": "instabox", "type": "default", "shape": "large", "kind": "lifecycle", "rep": r}
        for r in range(5)
    ],
    indent=0,
)
print(len(J), "jobs")
