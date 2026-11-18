"""Aggregate results/runs*/ , results/burst/, results/sleepwake/ into out/tables.md and out/summary.json.
Medians with bootstrap 95% CIs over sandboxes (2,000 resamples, seed 0). Every failure is counted, nothing is dropped."""

import collections
import glob
import itertools
import json
import os
import random
import statistics as st
import sys


def _load_json(path):
    with open(path) as handle:
        return json.load(handle)


def _write_open(path, mode, text):
    with open(path, mode) as handle:
        handle.write(text)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/harness")
import providers as P


def _need_results():
    pats = (
        f"{ROOT}/results/runs_full/*.json",
        f"{ROOT}/results/runs_instabox/*.json",
        f"{ROOT}/results/runs_instabox_lifecycle_rerun/*.json",
        f"{ROOT}/results/runs_instabox_universal/*.json",
        f"{ROOT}/results/burst/*.json",
        f"{ROOT}/results/sleepwake/*.json",
        f"{ROOT}/results/soak/*.json",
        f"{ROOT}/results/runs_full_harness_failed/*.json",
    )
    if any(glob.glob(p) for p in pats):
        return
    sys.exit(
        "No benchmark JSON under results/. This repository stores code only; run output is not committed.\n"
        "Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n"
        "Reproduce with ./run.sh, or the InstaBox / Vercel commands in README.md, then re-run this script.\n"
        "Vercel tables: python3 vercel/analysis/analyze_vercel.py"
    )


_need_results()
random.seed(0)


def ci(xs, f=st.median, B=2000):
    xs = sorted(
        x for x in xs if x is not None
    )  # sorted and re-seeded per call so every row is reproducible regardless of file order (added with the InstaBox rows; CI endpoints of older rows can differ in the last digit from the first tables)
    random.seed(0)
    if not xs:
        return None
    bs = sorted(f(random.choices(xs, k=len(xs))) for _ in range(B))
    return (round(f(xs), 3), round(bs[int(0.025 * B)], 3), round(bs[int(0.975 * B)], 3), len(xs))


def fmt(c):
    return "" if not c else f"{c[0]} [{c[1]}–{c[2]}] (n={c[3]})"


R = [
    _load_json(f)
    for f in glob.glob(f"{ROOT}/results/runs_full/*.json")
    + glob.glob(f"{ROOT}/results/runs_instabox/*.json")
]  # InstaBox grid (Pro workspace, run later) sits in runs_instabox/   # pilot and harness-failed attempts reported separately
HF = [_load_json(f) for f in glob.glob(f"{ROOT}/results/runs_full_harness_failed/*.json")]


def _load(d, typ):
    out = []
    for f in glob.glob(f"{ROOT}/results/{d}/*.json"):
        r = _load_json(f)
        r["job"] = dict(r["job"], type=typ)
        out.append(r)
    return out


RR = _load("runs_instabox_lifecycle_rerun", "default")
RU = _load("runs_instabox_universal", "universal")


def _retry_after_wait(r):
    return (r.get("create_rl_wait_s") or 0) > 0 or (r.get("create_s") or 0) > 30


_ib_grid = [r for r in R if r["job"]["provider"] == "instabox"]
_ib_rl = sum(1 for r in _ib_grid if _retry_after_wait(r))
cell = lambda r: (r["job"]["provider"], r["job"]["type"], r["job"]["shape"])
C = sorted({cell(r) for r in R})
T = ["# Agent37 vs Daytona vs InstaBox: generated tables\n"]


def g(r, *ks):
    for k in ks:
        r = r.get(k) if isinstance(r, dict) else None
    return r


T.append(
    "## Lifecycle (seconds, median [95% CI])\n\n| Provider | Type | Shape | create → API returns | first command | exec round trip | create errors |\n|---|---|---|---|---|---|---|"
)
for c in C:
    rs = [r for r in R if cell(r) == c]
    if c[0] == "instabox":
        r2 = [r for r in RR if cell(r) == c]
        T.append(
            f"| instabox | default, clean rerun (10 lifecycle jobs per shape, 20 workers, 429 waits excluded) | {c[2]} | {fmt(ci([r.get('create_s') for r in r2]))} | {fmt(ci([r.get('first_cmd_s') for r in r2]))} | {fmt(ci([st.median(r['exec_rtt_s']) for r in r2 if r.get('exec_rtt_s')]))} | {sum(1 for r in r2 if r.get('create_error'))}/{len(r2)} |"
        )
        T.append(
            f"| instabox | default, grid run as run (50 workers; create includes 60 s Retry-After waits in {_ib_rl} of {len(_ib_grid)} jobs) | {c[2]} | {fmt(ci([r.get('create_s') for r in rs]))} | {fmt(ci([r.get('first_cmd_s') for r in rs]))} | {fmt(ci([st.median(r['exec_rtt_s']) for r in rs if r.get('exec_rtt_s')]))} | {sum(1 for r in rs if r.get('create_error'))}/{len(rs)} |"
        )
        continue
    T.append(
        f"| {c[0]} | {c[1]} | {c[2]} | {fmt(ci([r.get('create_s') for r in rs]))} | {fmt(ci([r.get('first_cmd_s') for r in rs]))} | {fmt(ci([st.median(r['exec_rtt_s']) for r in rs if r.get('exec_rtt_s')]))} | {sum(1 for r in rs if r.get('create_error'))}/{len(rs)} |"
    )
T.append(
    "\n## CPU under 180 s sustained all-core load (sha256 rounds per 5 s window, all cores)\n\n| Provider | Type | Shape | first window | last window | min/max ratio |\n|---|---|---|---|---|---|"
)
for c in C:
    rs = [g(r, "cpu", "out") for r in R if cell(r) == c and r["job"]["kind"] == "lifecycle"]
    rs = [x for x in rs if x]
    T.append(
        f"| {c[0]} | {c[1]} | {c[2]} | {fmt(ci([x['first'] for x in rs]))} | {fmt(ci([x['last'] for x in rs]))} | {fmt(ci([x['min'] / x['max'] for x in rs if x['max']]))} |"
    )
T.append(
    "\n## git clone (wall seconds; Mbit/s received)\n\n| Provider | Type | Shape | Repo | Mode | seconds | Mbit/s | failures |\n|---|---|---|---|---|---|---|---|"
)
for c in C:
    for repo in ("next.js", "pytorch", "kubernetes"):
        for m in ("full", "shallow"):
            rs = [
                r
                for r in R
                if cell(r) == c
                and r["job"]["kind"] == "clone"
                and r["job"]["repo"].endswith(repo)
                and r["job"]["mode"] == m
            ]
            if not rs:
                continue
            o = [g(r, "clone", "out") for r in rs]
            ok = [x for x in o if x and x["rc"] == 0]
            T.append(
                f"| {c[0]} | {c[1]} | {c[2]} | {repo} | {m} | {fmt(ci([x['seconds'] for x in ok]))} | {fmt(ci([x['mbit_s'] for x in ok]))} | {len(rs) - len(ok)}/{len(rs)} |"
            )
T.append(
    "\n## git clone summary per cell (all three repos pooled)\n\n| Provider | Type | Shape | Mode | runs | failed (clone >25 min or error) | median s | median Mbit/s |\n|---|---|---|---|---|---|---|---|"
)
for c in C:
    for m in ("full", "shallow"):
        rs = [
            r for r in R if cell(r) == c and r["job"]["kind"] == "clone" and r["job"]["mode"] == m
        ]
        ok = [
            g(r, "clone", "out")
            for r in rs
            if g(r, "clone", "out") and g(r, "clone", "out")["rc"] == 0
        ]
        if rs:
            T.append(
                f"| {c[0]} | {c[1]} | {c[2]} | {m} | {len(rs)} | {len(rs) - len(ok)} | {fmt(ci([x['seconds'] for x in ok]))} | {fmt(ci([x['mbit_s'] for x in ok]))} |"
            )
T.append(
    "\n## Published price per sandbox-hour (USD)\n\n| Provider | Type | Medium 2/4/8 | Large 4/8/10 |\n|---|---|---|---|"
)
for p_, t_ in (
    ("daytona", "default"),
    ("agent37", "default"),
    ("agent37", "vm"),
    ("agent37", "performance"),
):
    T.append(
        f"| {p_} | {t_} | {P.rate_per_s(p_, 'medium', t_) * 3600:.5f} | {P.rate_per_s(p_, 'large', t_) * 3600:.5f} |"
    )
T.append(
    "\n## Memory: allocate and touch 128 MB steps up to 2x the shape\n\nGiB reached = last step the probe logged before it stopped (read from its progress file afterwards).\n\n| Provider | Type | Shape | RAM GiB | GiB reached (median [CI]) | how it stopped | sandbox answered 5 s later |\n|---|---|---|---|---|---|---|"
)


def reached(r):
    o = g(r, "mem", "out")
    if o:
        return o["allocated_mb"] / 1024
    t = (g(r, "mem_after", "out") or "").strip().splitlines()
    try:
        return int(t[0].split()[0]) / 1024
    except Exception:  # noqa: BLE001
        return None


def how(r):
    ma = r.get("mem_after") or {}
    mo = ma.get("out") or ""
    if not ma.get("alive") or "No such file" in mo:
        return "whole sandbox restarted (instance not running, /tmp wiped)"
    o = g(r, "mem", "out")
    if o:
        return o["result"]
    rc = g(r, "mem", "rc")
    tail = str(g(r, "mem", "tail") or "")
    if rc == 137 or "Killed" in tail:
        return "process OOM-killed (137)"
    if "WaitPID" in tail:
        return "sandbox runtime lost the process"
    if rc == "timeout":
        return "sandbox stopped answering"
    return f"other (rc {rc})"


for c in C:
    rs = [r for r in R if cell(r) == c and r["job"]["kind"] == "mem"]
    T.append(
        f"| {c[0]} | {c[1]} | {c[2]} | {P.SHAPES[c[2]][1]} | {fmt(ci([reached(r) for r in rs]))} | {dict(collections.Counter(how(r) for r in rs))} | {sum(1 for r in rs if g(r, 'mem_after', 'alive'))}/{len(rs)} |"
    )
T.append(
    "\n## Disk: write until ENOSPC (GB written; MB/s)\n\n| Provider | Type | Shape | home volume GB | home MB/s | OS layer GB |\n|---|---|---|---|---|---|"
)
for c in C:
    rs = [r for r in R if cell(r) == c and r["job"]["kind"] == "disk"]
    T.append(
        f"| {c[0]} | {c[1]} | {c[2]} | {fmt(ci([(g(r, 'disk_home', 'out', 'written_b') or 0) / 1e9 for r in rs if g(r, 'disk_home', 'out')]))} | {fmt(ci([g(r, 'disk_home', 'out', 'mb_per_s') for r in rs]))} | {fmt(ci([(g(r, 'disk_root', 'out', 'written_b') or 0) / 1e9 for r in rs if g(r, 'disk_root', 'out')]))} |"
    )
B = [_load_json(f) for f in glob.glob(f"{ROOT}/results/burst/*.json")]
if B:
    T.append(
        "\n## Burst creation (all creates fired at once)\n\n| Provider | N | wave | succeeded | errors | create s median [CI] | p95 | wall s |\n|---|---|---|---|---|---|---|---|"
    )
    for b in sorted(B, key=lambda x: (x["provider"], x["N"], x["wave"])):
        ok = [r for r in b["runs"] if "error" not in r]
        cs = sorted(r["create_s"] for r in ok)
        T.append(
            f"| {b['provider']} | {b['N']} | {b['wave']} | {len(ok)}/{b['N']} | {dict(collections.Counter(str(r['error'].get('code') or r['error'].get('exc', '')[:40]) for r in b['runs'] if 'error' in r))} | {fmt(ci(cs))} | {cs[int(0.95 * (len(cs) - 1))] if cs else ''} | {b['wall_s']} |"
        )
S = [_load_json(f) for f in glob.glob(f"{ROOT}/results/sleepwake/*.json")]
if S:
    T.append(
        '\n## Sleep/wake and persistence (5 cycles: sleep, 120 s idle, first command)\n\nA background counter (one increment per second) is started over exec before the first sleep. "Process kept" = the counter advanced between one wake and the next sleep (pgrep was not used: it matches its own command line).\n\n| Provider | cycles | wake → first command s (median [CI]) | file kept | background process kept |\n|---|---|---|---|---|'
    )
    for p in sorted({s["provider"] for s in S}):
        cy = [c for s in S if s["provider"] == p for c in s["cycles"]]
        kept = tot = 0
        for s_ in S:
            if s_["provider"] != p:
                continue
            c = s_["cycles"]
            for a, b in itertools.pairwise(c):
                tot += 1
                try:
                    kept += int(b["counter_before"]) > int(a["after"][1])
                except Exception:  # noqa: BLE001, S110
                    pass
        T.append(
            f"| {p} | {len(cy)} | {fmt(ci([c['wake_to_first_cmd_s'] for c in cy]))} | {sum(1 for c in cy if 'persisted' in c['after'])}/{len(cy)} | {kept}/{tot} |"
        )
SK = [_load_json(f) for f in sorted(glob.glob(f"{ROOT}/results/soak/*.json"))]
if SK:
    T.append(
        "\n## 24 h soak (M10): one Medium instance per provider, slept/stopped, woken every 30 min with `cat marker`\n\nIf the harness host is paused, wake attempts are skipped for that interval and the instances sit asleep or stopped through it. Those gaps show up as large intervals between checks. Idle cost is modeled at each provider's published parked rate (disk only: Agent37 $0.09/GB-month on 8 GB; Daytona $0.000108/GB-h on the 3 GB above its 5 GB free) against the always-on rate for the same life.\n\n| Provider | life h | wake attempts | woke and file kept | failed wakes | sleep/stop errors | wake s median [CI] | min-max | longest idle h | modeled parked $ | always-on $ | deleted |\n|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    for r in SK:
        if "life_s" not in r:
            r["life_s"] = max([x["t"] for x in r["checks"]] + [r["start"]]) - r["start"]
            r["deleted"] = "IN PROGRESS (life to last check)"
        c = r["checks"]
        w = [x for x in c if "wake_s" in x]
        ws = [x["wake_s"] for x in w]
        ts = [r["start"]] + [x["t"] for x in c]
        p = r["provider"]
        c_, m_, d_ = P.SHAPES["medium"]
        park = (
            (d_ * 0.09 / 730 / 3600)
            if p == "agent37"
            else (20 * 0.00011 / 3600 if p == "instabox" else max(0, d_ - 5) * 0.000108 / 3600)
        )
        p_label = p + (f" ({r['mode']})" if r.get("mode") and r["mode"] != "manual" else "")
        T.append(
            f"| {p_label} | {round(r['life_s'] / 3600, 2)} | {len(w) + sum(1 for x in c if 'err' in x)} | {sum(1 for x in w if x['ok'])}/{len(w)} | {sum(1 for x in c if 'err' in x)} | {sum(1 for x in c if 'sleep_err' in x)} | {fmt(ci(ws))} | {min(ws) if ws else ''}-{max(ws) if ws else ''} | {round(max(b - a for a, b in itertools.pairwise(ts)) / 3600, 1)} | {round(r['life_s'] * park, 4)} | {round(r['life_s'] * P.rate_per_s(p, 'medium'), 3)} | {r.get('deleted')} |"
        )
IBR = [r for r in R if r["job"]["provider"] == "instabox"]
if IBR:
    T.append(
        "\n## InstaBox: retried API answers (honouring Retry-After; not counted as failures)\n\nStarts are limited to 30 a minute on Pro (create/start/resume/wake), so a burst of simultaneous creates gets retryable `429 rate_limited`; the harness waits the Retry-After and tries again. `create s` above is the successful attempt only. Cumulative per-process counters, read at each create (the maximum is a lower bound of the total):\n"
    )
    mx = collections.Counter()
    for r in IBR:
        for k, v in (r.get("retries_so_far") or {}).items():
            mx[k] = max(mx[k], v)
    T.append("| answer | retries (max counter seen) |\n|---|---|")
    [T.append(f"| {k} | {v} |") for k, v in sorted(mx.items())]
    T.append(
        "\n## InstaBox: create step detail (seconds, median [CI])\n\n| Shape | POST /v1/machines answered (202) | create → machine running (op succeeded) | delete (op succeeded) |\n|---|---|---|---|"
    )
    for sh in ("medium", "large"):
        for lab, rs in (
            ("clean rerun", [r for r in RR if r["job"]["shape"] == sh]),
            (
                "grid as run, jobs with no 429 wait (create_s < 30)",
                [r for r in IBR if r["job"]["shape"] == sh and (r.get("create_s") or 99) < 30],
            ),
            ("grid as run, all (waits included)", [r for r in IBR if r["job"]["shape"] == sh]),
        ):
            T.append(
                f"| {sh}, {lab} | {fmt(ci([r.get('create_post_s') for r in rs]))} | {fmt(ci([r.get('create_s') for r in rs]))} | {fmt(ci([r.get('delete_s') for r in rs]))} |"
            )

if RR or RU:
    T.append(
        "\n## InstaBox lifecycle, clean rerun and template check\n\n"
        "The first InstaBox grid fired 50 jobs at once against Pro's 30 starts a minute, "
        f"so {_ib_rl} of its {len(_ib_grid)} creates waited out a 60 s `Retry-After` "
        "and their `create_s` includes it (the Lifecycle table above shows that grid as run). "
        "The rerun below repeats the 10 lifecycle jobs per shape at 20 workers, inside the limit, "
        "with the wait excluded from `create_s` and recorded as `create_rl_wait_s`. "
        "The `universal` rows are 5 Large runs from the template without a pre-booted pool "
        "(the default `agent-browser` has one).\n\n"
        "| Run | Shape | create → running (s) | first command (s) | exec round trip (s) | CPU min/max (180 s) | first-window rate | creates that hit a 429 wait |\n|---|---|---|---|---|---|---|---|"
    )
    for lab, rs in (
        (
            "grid run (as run)",
            [
                r
                for r in R
                if r["job"]["provider"] == "instabox" and r["job"]["kind"] == "lifecycle"
            ],
        ),
        ("rerun, agent-browser (default)", RR),
        ("template check, universal", RU),
    ):
        for sh in ("medium", "large"):
            x = [r for r in rs if r["job"]["shape"] == sh]
            if not x:
                continue
            cp = [g(r, "cpu", "out") for r in x]
            cp = [c for c in cp if c]
            T.append(
                f"| {lab} | {sh} | {fmt(ci([r.get('create_s') for r in x]))} | {fmt(ci([r.get('first_cmd_s') for r in x]))} | {fmt(ci([st.median(r['exec_rtt_s']) for r in x if r.get('exec_rtt_s')]))} | {fmt(ci([c['min'] / c['max'] for c in cp if c['max']]))} | {fmt(ci([c['first'] for c in cp]))} | {sum(1 for r in x if (r.get('create_rl_wait_s') or 0) > 0 or (r.get('create_s') or 0) > 30)}/{len(x)} |"
            )
T.append(
    "\n## Harness failures (kept in results/runs_full_harness_failed/, rerun, not counted above)\n\n| Provider | cause | attempts |\n|---|---|---|"
)
for k, v in sorted(
    collections.Counter((h["job"]["provider"], h["harness_failure"]) for h in HF).items()
):
    T.append(f"| {k[0]} | {k[1]} | {v} |")
# modeled cost (sandbox life x published rate; Agent37 also with per-minute round-up)
import math

T.append(
    "\n## Modeled sandbox cost of this grid\n\n| Provider | Type | Shape | sandboxes | sandbox-hours | modeled $ (exact) | modeled $ (whole minutes) |\n|---|---|---|---|---|---|---|"
)
for c in C:
    rs = [r for r in R if cell(r) == c and r.get("id")]
    rt = P.rate_per_s(c[0], c[2], c[1])
    T.append(
        f"| {c[0]} | {c[1]} | {c[2]} | {len(rs)} | {round(sum(r['life_s'] for r in rs) / 3600, 2)} | {round(sum(r['life_s'] for r in rs) * rt, 4)} | {round(sum(math.ceil(r['life_s'] / 60) * 60 for r in rs) * rt, 4)} |"
    )
os.makedirs(f"{ROOT}/out", exist_ok=True)
_write_open(f"{ROOT}/out/tables.md", "w", "\n".join(T) + "\n")
print("\n".join(T))
