"""Charts with Vercel Sandbox next to Agent37 (default), Daytona, and InstaBox.
Writes vercel/out/*.png. Numbers are recomputed from the result files (same
loaders as analyze_vercel.py), nothing typed in by hand.

Optional brand fonts: place Onest-Regular.ttf, Onest-Medium.ttf, and
Lexend-SemiBold.ttf in this directory (vercel/analysis/). If they are missing,
matplotlib's default sans-serif is used.
"""

import collections
import glob
import json
import os
import statistics as st
import sys
import textwrap

import matplotlib


def _load_json(path):
    with open(path) as handle:
        return json.load(handle)


matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm

V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(V)
sys.path.insert(0, f"{ROOT}/harness")
import providers as P

FONT_DIR = os.path.dirname(os.path.abspath(__file__))
HAVE_FONTS = True
for f in ("Onest-Regular.ttf", "Onest-Medium.ttf", "Lexend-SemiBold.ttf"):
    path = f"{FONT_DIR}/{f}"
    if os.path.exists(path):
        fm.fontManager.addfont(path)
    else:
        HAVE_FONTS = False
FAMILY = "Onest" if HAVE_FONTS else "sans-serif"
TITLE_FAM = "Lexend" if HAVE_FONTS else "sans-serif"

BG, PANEL, GRID = "#13161a", "#1b2028", "#2a303a"
T1, T2, T3, PINK, LP = "#ffffff", "#d5d9df", "#abb2bf", "#ff4fae", "#ffb8de"
plt.rcParams.update(
    {
        "font.family": FAMILY,
        "text.color": T2,
        "axes.labelcolor": T3,
        "xtick.color": T3,
        "ytick.color": T3,
        "axes.facecolor": PANEL,
        "figure.facecolor": BG,
        "axes.edgecolor": GRID,
        "axes.grid": True,
        "grid.color": GRID,
        "axes.axisbelow": True,
        "font.size": 10.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
    }
)
COL = {
    "agent37": "#5c616b",
    "daytona": "#8b919c",
    "instabox": "#b9c0cb",
    "vercel": PINK,
}
NAME = {
    "agent37": "Agent37",
    "daytona": "Daytona",
    "instabox": "InstaBox",
    "vercel": "Vercel",
}
PROV = ["agent37", "daytona", "instabox", "vercel"]


def title(fig, t, sub):
    fig.text(
        0.02,
        0.965,
        t,
        fontfamily=TITLE_FAM,
        fontweight="semibold",
        fontsize=16,
        color=T1,
        va="top",
    )
    fig.text(
        0.02,
        0.905,
        "\n".join(textwrap.wrap(sub, 115)),
        fontsize=10.5,
        color=T3,
        va="top",
    )


def save(fig, name):
    os.makedirs(f"{V}/out", exist_ok=True)
    fig.savefig(f"{V}/out/{name}", dpi=150, facecolor=BG)
    plt.close(fig)
    print("wrote vercel/out/" + name)


def L(pat):
    return [_load_json(f) for f in glob.glob(pat)]


def g(r, *ks):
    for k in ks:
        r = r.get(k) if isinstance(r, dict) else None
    return r


def _need_results():
    if (
        L(f"{V}/results/runs_vercel/*.json")
        or L(f"{V}/results/burst/*.json")
        or L(f"{V}/results/sleepwake/*.json")
    ):
        return
    sys.exit(
        "No Vercel benchmark JSON under vercel/results/. This repository stores code only; "
        "run output is not committed. Reproduce with the commands in vercel/VERCEL.md, then re-run."
    )


RUNS = {
    "agent37": L(f"{ROOT}/results/runs_full/agent37__default__*.json"),
    "daytona": L(f"{ROOT}/results/runs_full/daytona__*.json"),
    "instabox": L(f"{ROOT}/results/runs_instabox/*.json"),
    "vercel": L(f"{V}/results/runs_vercel/*.json"),
}
IBR = L(f"{ROOT}/results/runs_instabox_lifecycle_rerun/*.json")


def runs(p, sh, kind):
    src = IBR if (p == "instabox" and kind == "lifecycle" and IBR) else RUNS[p]
    return [r for r in src if r["job"]["shape"] == sh and r["job"]["kind"] == kind]


def clone(p, sh, m):
    o = [g(r, "clone", "out") for r in runs(p, sh, "clone") if r["job"]["mode"] == m]
    return [x["seconds"] for x in o if x and x["rc"] == 0]


def lab(ax, xs, ys, fmt, color=T2, dy=0):
    for x, y in zip(xs, ys):
        ax.text(x, y + dy, fmt(y), ha="center", va="bottom", color=color, fontsize=9.5)


def four(fn, name, t, sub, ylabel, fmt="{:.2f}", log=False):
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
    fig.subplots_adjust(top=0.74, left=0.07, right=0.98, bottom=0.12, wspace=0.06)
    for ax, sh, lb in zip(
        axs, ("medium", "large"), ("Medium  2 vCPU / 4 GiB", "Large  4 vCPU / 8 GiB")
    ):
        ys = [st.median(fn(p, sh)) if fn(p, sh) else 0 for p in PROV]
        ax.bar(range(4), ys, 0.62, color=[COL[p] for p in PROV])
        ax.set_xticks(range(4))
        ax.set_xticklabels([NAME[p] for p in PROV])
        ax.set_title(lb, color=T1, fontsize=11, loc="left")
        ax.grid(axis="x", visible=False)
        if log:
            ax.set_yscale("log")
        lab(
            ax,
            range(4),
            ys,
            lambda v: fmt.format(v),
            color=T1,
            dy=0 if log else max(ys or [0]) * 0.012,
        )
    axs[0].set_ylabel(ylabel)
    title(fig, t, sub)
    save(fig, name)


if __name__ == "__main__":
    _need_results()
    os.makedirs(f"{V}/out", exist_ok=True)
    four(
        lambda p, sh: [r["create_s"] for r in runs(p, sh, "lifecycle") if r.get("create_s")],
        "create.png",
        "Create: time until the create call returns",
        "Median over lifecycle jobs. InstaBox is its clean rerun (20 workers). Vercel create excludes SDK retry waits.",
        "seconds",
    )
    four(
        lambda p, sh: [r["first_cmd_s"] for r in runs(p, sh, "lifecycle") if r.get("first_cmd_s")],
        "first_cmd.png",
        "Time to the first command after create",
        "Median over lifecycle jobs; one trivial `true` through each provider's exec API.",
        "seconds",
        fmt="{:.3f}",
    )
    four(
        lambda p, sh: [
            g(r, "cpu", "out", "min") / g(r, "cpu", "out", "max")
            for r in runs(p, sh, "lifecycle")
            if g(r, "cpu", "out", "max")
        ],
        "cpu_ratio.png",
        "CPU stability under 180 s of all-core load",
        "Slowest 5 s window divided by the fastest, median per shape. 1.0 = no throttling or noisy-neighbour dip.",
        "ratio",
        fmt="{:.2f}",
    )
    for m in ("full", "shallow"):
        four(
            lambda p, sh, m=m: clone(p, sh, m),
            f"clone_{m}.png",
            f"git clone {m}: next.js, pytorch, kubernetes pooled",
            "Median wall seconds over 15 clones per cell. Different days and network paths per provider: indicative.",
            "seconds",
            fmt="{:.0f}",
        )

    sw = collections.defaultdict(list)
    for f in glob.glob(f"{ROOT}/results/sleepwake/*.json"):
        s = _load_json(f)
        sw[s["provider"]] += [c["wake_to_first_cmd_s"] for c in s["cycles"]]
    for f in glob.glob(f"{V}/results/sleepwake/sleepwake__vercel__*.json"):
        s = _load_json(f)
        sw["vercel_" + (s.get("wake_mode") or "resume")] += [
            c["wake_to_first_cmd_s"] for c in s["cycles"]
        ]
    snap = [
        c["restore_to_first_cmd_s"]
        for f in glob.glob(f"{V}/results/sleepwake/snapshot_resume__*.json")
        for c in _load_json(f)["cycles"]
    ]
    items = [
        ("Agent37\nsleep → exec", "agent37", sw["agent37"]),
        ("Daytona\nstop → start", "daytona", sw["daytona"]),
        ("InstaBox\nsuspend → resume", "instabox", sw["instabox"]),
        ("Vercel\nstop → resume", "vercel", sw["vercel_resume"]),
        ("Vercel\nstop → first cmd\n(auto-resume)", "vercel", sw["vercel_auto"]),
        ("Vercel\nsnapshot → new\nsandbox from it", "vercel", snap),
    ]
    items = [i for i in items if i[2]]
    if items:
        fig, ax = plt.subplots(figsize=(11, 5.2))
        fig.subplots_adjust(top=0.74, left=0.07, right=0.98, bottom=0.24)
        ys = [st.median(i[2]) for i in items]
        ax.bar(range(len(items)), ys, 0.62, color=[COL[i[1]] for i in items])
        ax.set_xticks(range(len(items)))
        ax.set_xticklabels([i[0] + f"\n(n={len(i[2])})" for i in items], fontsize=9.5)
        ax.grid(axis="x", visible=False)
        ax.set_ylabel("seconds, median")
        lab(
            ax,
            range(len(items)),
            ys,
            lambda v: f"{v:.2f} s",
            color=T1,
            dy=max(ys) * 0.012,
        )
        title(
            fig,
            "Back from sleep: seconds until the first command answers",
            "Agent37, Daytona and InstaBox: 5 cycles x 3 instances, 120 s idle. Only InstaBox keeps running processes; Vercel keeps the filesystem, not memory.",
        )
        save(fig, "wake.png")

    OB = L(f"{ROOT}/results/burst/*.json")
    VB = L(f"{V}/results/burst/*.json")
    pools = {
        "agent37": (OB, ("a", "b")),
        "daytona": (OB, ("a", "b")),
        "instabox": (OB, ("c", "d")),
        "vercel": (VB, ("a", "b", "c", "d")),
    }
    Ns = [10, 25, 45]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    fig.subplots_adjust(top=0.74, left=0.07, right=0.98, bottom=0.12)
    w = 0.2
    for k, p in enumerate(PROV):
        pool, ws = pools[p]
        ys = []
        for n in Ns:
            bs = [b for b in pool if b["provider"] == p and b["N"] == n and b["wave"] in ws]
            tot = sum(b["N"] for b in bs)
            ok = sum(sum(1 for r in b["runs"] if "error" not in r) for b in bs)
            ys.append(100 * ok / tot if tot else 0)
        xs = np.arange(len(Ns)) + (k - 1.5) * w
        ax.bar(xs, ys, w * 0.92, color=COL[p], label=NAME[p])
        lab(ax, xs, ys, lambda v: f"{v:.0f}%", color=T1, dy=1)
    ax.set_xticks(range(len(Ns)))
    ax.set_xticklabels([f"{n} creates at once" for n in Ns])
    ax.set_ylim(0, 135)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("% of creates that succeeded (no retries)")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, ncol=4, loc="upper center", labelcolor=T2)
    title(
        fig,
        "Burst creation: how many of N simultaneous creates succeed",
        "Medium, default type, no retries, two waves each (InstaBox: the clean 75 s-gap waves). Vercel Pro starts at 150 vCPUs a minute (75 Medium sandboxes).",
    )
    save(fig, "burst.png")

    fig, axs = plt.subplots(1, 2, figsize=(11, 5.2), sharey=False)
    fig.subplots_adjust(top=0.74, left=0.07, right=0.98, bottom=0.12, wspace=0.18)
    for ax, sh, lb in zip(
        axs, ("medium", "large"), ("Medium  2 vCPU / 4 GiB", "Large  4 vCPU / 8 GiB")
    ):
        c, m, d = P.SHAPES[sh]
        ys = [
            P.rate_per_s("agent37", sh, "default") * 3600,
            P.rate_per_s("daytona", sh) * 3600,
            c * 0.004 + m * 0.00225,
            m * P.VC_GB_H + c * P.VC_CPU_H,
        ]
        ax.bar(range(4), ys, 0.62, color=[COL[p] for p in PROV])
        idle = m * P.VC_GB_H + c * P.VC_CPU_H * 0.01
        ax.plot([2.69, 3.31], [idle, idle], color=LP, lw=2)
        ax.text(
            3.33,
            idle,
            f"idle (1% CPU)\n${idle:.3f}",
            color=LP,
            fontsize=8.5,
            va="center",
        )
        ax.set_xticks(range(4))
        ax.set_xticklabels([NAME[p] for p in PROV])
        ax.set_title(lb, color=T1, fontsize=11, loc="left")
        ax.grid(axis="x", visible=False)
        ax.set_xlim(-0.5, 4.15)
        lab(ax, range(4), ys, lambda v: f"${v:.3f}", color=T1, dy=max(ys) * 0.012)
    axs[0].set_ylabel("USD per sandbox-hour, list price")
    title(
        fig,
        "Price per sandbox-hour (list prices, before credits)",
        "Vercel bills memory all the time but CPU only while it is busy: the bar assumes every vCPU busy, the line a mostly idle agent sandbox (1% CPU). Others bill CPU by allocation.",
    )
    save(fig, "cost_per_hour.png")
