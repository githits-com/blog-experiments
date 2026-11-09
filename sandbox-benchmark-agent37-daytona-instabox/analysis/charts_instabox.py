"""Charts with InstaBox next to Agent37 and Daytona (matched Medium/Large cells). Writes out/*.png. Uses the InstaBox lifecycle rerun for create/first-command/CPU
(the first grid's create_s includes 429 waits)."""

import glob
import json
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not any(
    glob.glob(f"{ROOT}/results/{d}/*.json")
    for d in ("runs_full", "runs_instabox", "runs_instabox_lifecycle_rerun", "sleepwake")
):
    sys.exit(
        "No benchmark JSON under results/. This repository stores code only; run output is not committed.\n"
        "Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n"
        "Reproduce with ./run.sh and the InstaBox commands in README.md, then re-run this script."
    )
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(d):
    return [json.load(open(f)) for f in glob.glob(f"{ROOT}/results/{d}/*.json")]


R = load("runs_full") + load("runs_instabox")
RR = load("runs_instabox_lifecycle_rerun")
cells = [
    ("daytona", "default"),
    ("agent37", "default"),
    ("agent37", "performance"),
    ("agent37", "vm"),
    ("instabox", "default"),
]
col = {"daytona": "#4c72b0", "agent37": "#dd8452", "instabox": "#55a868"}


def lab(c):
    return c[0] if c[1] == "default" else f"{c[0]} {c[1]}"


def g(r, *ks):
    for k in ks:
        r = r.get(k) if isinstance(r, dict) else None
    return r


def bars(fn, title, ylabel, out, log=False):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for a, sh in zip(ax, ("medium", "large")):
        xs = []
        ys = []
        cs = []
        for c in cells:
            v = fn(c, sh)
            if v:
                xs.append(lab(c))
                ys.append(st.median(v))
                cs.append(col[c[0]])
        a.bar(xs, ys, color=cs)
        a.set_title(f"{title} — {sh}")
        a.tick_params(axis="x", rotation=30)
        if log:
            a.set_yscale("log")
    ax[0].set_ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(f"{ROOT}/out/{out}", dpi=130)
    plt.close()


def runs(c, sh, kind, src=None):
    return [
        r
        for r in (src if src is not None else R)
        if (r["job"]["provider"], r["job"]["type"]) == c
        and r["job"]["shape"] == sh
        and r["job"]["kind"] == kind
    ]


def life(c, sh):
    return runs(c, sh, "lifecycle", RR if c[0] == "instabox" else None)


bars(
    lambda c, sh: [r["create_s"] for r in life(c, sh) if r.get("create_s")],
    "create → API returns (median)",
    "seconds",
    "create.png",
)
bars(
    lambda c, sh: [r["first_cmd_s"] for r in life(c, sh) if r.get("first_cmd_s")],
    "time to first command (median)",
    "seconds",
    "first_cmd.png",
)
bars(
    lambda c, sh: [
        g(r, "cpu", "out", "min") / g(r, "cpu", "out", "max")
        for r in life(c, sh)
        if g(r, "cpu", "out", "max")
    ],
    "CPU stability: slowest/fastest 5 s window (median)",
    "ratio",
    "cpu_ratio.png",
)
for m in ("full", "shallow"):
    bars(
        lambda c, sh, m=m: [
            g(r, "clone", "out", "seconds")
            for r in runs(c, sh, "clone")
            if r["job"]["mode"] == m and g(r, "clone", "out", "rc") == 0
        ],
        f"git clone {m}, 3 repos pooled (median)",
        "seconds",
        f"clone_{m}.png",
        log=True,
    )
plt.figure(figsize=(6, 4))
S = [json.load(open(f)) for f in glob.glob(f"{ROOT}/results/sleepwake/*.json")]
d = {}
for s in S:
    for c in s["cycles"]:
        d.setdefault(s["provider"], []).append(c["wake_to_first_cmd_s"])
plt.bar(list(d), [st.median(v) for v in d.values()], color=[col[p] for p in d])
plt.ylabel("seconds")
plt.title("sleep → wake → first command (median, 15 cycles)")
plt.tight_layout()
plt.savefig(f"{ROOT}/out/wake.png", dpi=130)
print("charts written")
