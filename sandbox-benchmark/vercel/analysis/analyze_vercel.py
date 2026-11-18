"""Vercel Sandbox tables and the matched comparison with Agent37 (default),
Daytona, and InstaBox. Writes vercel/out/tables.md and vercel/out/summary.json.

Medians with bootstrap 95% CIs over sandboxes (2,000 resamples, seed 0), same
method as analysis/analyze.py. Every failure is counted, nothing is dropped.

The other providers' numbers are recomputed here from their own result files
(results/runs_full, runs_instabox, runs_instabox_lifecycle_rerun, results/burst,
results/sleepwake); nothing is copied by hand. If those files are missing, the
comparison cells are left blank.
"""

import collections
import glob
import itertools
import json
import math
import os
import random
import statistics as st
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


V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(V)
sys.path.insert(0, f"{ROOT}/harness")
import providers as P


def _need_results():
    pats = (
        f"{V}/results/runs_vercel/*.json",
        f"{V}/results/burst/*.json",
        f"{V}/results/sleepwake/*.json",
        f"{V}/results/runs_pilot/*.json",
    )
    if any(glob.glob(p) for p in pats):
        return
    sys.exit(
        "No Vercel benchmark JSON under vercel/results/. This repository stores code only; "
        "run output is not committed.\n"
        "Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n"
        "Reproduce with the Vercel commands in README.md / vercel/VERCEL.md, then re-run this script."
    )


_need_results()


def ci(xs, f=st.median, B=2000):
    xs = sorted(x for x in xs if x is not None)
    random.seed(0)
    if not xs:
        return None
    bs = sorted(f(random.choices(xs, k=len(xs))) for _ in range(B))
    return (
        round(f(xs), 3),
        round(bs[int(0.025 * B)], 3),
        round(bs[int(0.975 * B)], 3),
        len(xs),
    )


def fmt(c):
    return "" if not c else f"{c[0]} [{c[1]}–{c[2]}] (n={c[3]})"


def med(c):
    return "" if not c else f"{c[0]}"


def L(pat):
    return [_load_json(f) for f in glob.glob(pat)]


def g(r, *ks):
    for k in ks:
        r = r.get(k) if isinstance(r, dict) else None
    return r


RUNS = {
    "agent37": L(f"{ROOT}/results/runs_full/agent37__default__*.json"),
    "daytona": L(f"{ROOT}/results/runs_full/daytona__*.json"),
    "instabox": L(f"{ROOT}/results/runs_instabox/*.json"),
    "vercel": L(f"{V}/results/runs_vercel/*.json"),
}
IBR = L(f"{ROOT}/results/runs_instabox_lifecycle_rerun/*.json")
FAIL429 = L(f"{V}/results/runs_vercel_failed_first_attempt/*.json")
PROV = [
    ("agent37", "Agent37 default"),
    ("daytona", "Daytona"),
    ("instabox", "InstaBox"),
    ("vercel", "Vercel Sandbox"),
]


def cellruns(p, sh, kind=None):
    return [
        r for r in RUNS[p] if r["job"]["shape"] == sh and (kind is None or r["job"]["kind"] == kind)
    ]


def life(p, sh):
    src = IBR if p == "instabox" and IBR else RUNS[p]
    return [r for r in src if r["job"]["shape"] == sh and r["job"]["kind"] == "lifecycle"]


def clone(p, sh, m):
    o = [g(r, "clone", "out") for r in cellruns(p, sh, "clone") if r["job"]["mode"] == m]
    return [x["seconds"] for x in o if x and x["rc"] == 0]


def cpuratio(p, sh):
    return [
        g(r, "cpu", "out", "min") / g(r, "cpu", "out", "max")
        for r in life(p, sh)
        if g(r, "cpu", "out", "max")
    ]


def jobcost(p, r, sh):
    if p == "vercel":
        return P.vc_cost(r["life_s"], sh, r.get("vc_cpu_busy_s") or 0)
    rate = P.rate_per_s(p, sh, "default")
    life = r["life_s"]
    return (math.ceil(life / 60) * 60 if p == "agent37" else life) * rate


T = [
    "# Vercel Sandbox: generated tables\n",
    (
        "Recomputed from local result files (same probes and job kinds as the other providers). "
        "See `vercel/VERCEL.md` for method and caveats. Comparison cells are blank when the other "
        "providers' result files are not present.\n"
    ),
]
S = {}

T.append("## Matched comparison (Medium 2 vCPU / 4 GiB and Large 4 vCPU / 8 GiB; medians)\n")
for sh, lab in (("medium", "Medium 2 vCPU / 4 GiB"), ("large", "Large 4 vCPU / 8 GiB")):
    T.append(
        f"### {lab}\n\n| | Agent37 default | Daytona | InstaBox (Pro, agent-browser) | **Vercel Sandbox (Pro)** |\n|---|---|---|---|---|"
    )
    rows = []

    def row(name, fn, rows=rows):
        rows.append("| " + name + " | " + " | ".join(fn(p) for p, _ in PROV) + " |")

    row(
        "create → API returns, s (InstaBox: clean rerun)",
        lambda p, sh=sh: med(ci([r.get("create_s") for r in life(p, sh) if r.get("create_s")])),
    )
    row(
        "first command, s",
        lambda p, sh=sh: med(
            ci([r.get("first_cmd_s") for r in life(p, sh) if r.get("first_cmd_s")])
        ),
    )
    row(
        "exec round trip, s",
        lambda p, sh=sh: med(
            ci([st.median(r["exec_rtt_s"]) for r in life(p, sh) if r.get("exec_rtt_s")])
        ),
    )
    row(
        "CPU: slowest / fastest 5 s window over 180 s",
        lambda p, sh=sh: med(ci(cpuratio(p, sh))),
    )
    row("git clone full, s (3 repos pooled)", lambda p, sh=sh: med(ci(clone(p, sh, "full"))))
    row(
        "git clone shallow, s (3 repos pooled)",
        lambda p, sh=sh: med(ci(clone(p, sh, "shallow"))),
    )

    def memtxt(p, sh=sh):
        rs = cellruns(p, sh, "mem")
        if not rs:
            return ""
        alive = sum(1 for r in rs if g(r, "mem_after", "alive"))
        rc137 = sum(
            1 for r in rs if g(r, "mem", "rc") == 137 or "Killed" in str(g(r, "mem", "tail") or "")
        )
        return f"{len(rs)} runs, OOM-kill 137: {rc137}, sandbox answered after: {alive}/{len(rs)}"

    row("memory limit probe (up to 2x RAM)", memtxt)
    row(
        "disk written until ENOSPC, GB (home / data volume)",
        lambda p, sh=sh: med(
            ci(
                [
                    (g(r, "disk_home", "out", "written_b") or 0) / 1e9
                    for r in cellruns(p, sh, "disk")
                    if g(r, "disk_home", "out")
                ]
            )
        ),
    )
    row(
        "grid jobs failed / run",
        lambda p, sh=sh: (
            f"{sum(1 for r in cellruns(p, sh) if 'error' in r or r.get('create_error'))}/{len(cellruns(p, sh))}"
            if cellruns(p, sh)
            else ""
        ),
    )
    row(
        "modeled $ of this grid cell (48 sandboxes)",
        lambda p, sh=sh: (
            f"{sum(jobcost(p, r, sh) for r in cellruns(p, sh) if r.get('id')):.3f}"
            if cellruns(p, sh)
            else ""
        ),
    )

    def price(p, sh=sh):
        if p == "vercel":
            busy = P.SHAPES[sh][1] * P.VC_GB_H + P.SHAPES[sh][0] * P.VC_CPU_H
            idle = P.SHAPES[sh][1] * P.VC_GB_H + P.SHAPES[sh][0] * P.VC_CPU_H * 0.01
            return f"{busy:.4f} all vCPUs busy; {idle:.4f} at 1% CPU"
        if p == "instabox":
            return (
                f"{P.SHAPES[sh][0] * 0.004 + P.SHAPES[sh][1] * 0.00225:.4f} compute "
                "(+ fixed 20 GiB /data beyond the 200 GiB Pro includes)"
            )
        return f"{P.rate_per_s(p, sh, 'default') * 3600:.4f}"

    row("published list $ per sandbox-hour", price)
    T += rows
    T.append("")
    S[sh] = {
        p: {
            "create": med(ci([r.get("create_s") for r in life(p, sh) if r.get("create_s")])),
            "first": med(ci([r.get("first_cmd_s") for r in life(p, sh) if r.get("first_cmd_s")])),
            "cpu": med(ci(cpuratio(p, sh))),
            "full": med(ci(clone(p, sh, "full"))),
            "shallow": med(ci(clone(p, sh, "shallow"))),
        }
        for p, _ in PROV
    }

T.append(
    "## Modeled cost per task (USD per sandbox job, medians; the sandbox lives for the whole job)\n\n"
    "Job = create, the probes of that kind, delete (`life_s`). Agent37 rounded up to whole minutes, "
    "Vercel with its 60 s memory minimum and Active CPU from the guest busy time (`/proc/stat`, all vCPUs), "
    "everyone else life x list rate.\n\n"
    "| Shape | Job | Agent37 default | Daytona | InstaBox | **Vercel** |\n|---|---|---|---|---|---|"
)
for sh in ("medium", "large"):
    for kind, modes in (("lifecycle", [None]), ("clone", ["shallow", "full"])):
        for m in modes:

            def c_(p, sh=sh, kind=kind, m=m):
                xs = [
                    jobcost(p, r, sh)
                    for r in cellruns(p, sh, kind)
                    if r.get("id") and (m is None or r["job"]["mode"] == m)
                ]
                return f"{st.median(xs):.5f}" if xs else ""

            T.append(
                f"| {sh} | {kind + (' ' + m if m else '')} | "
                + " | ".join(c_(p) for p, _ in PROV)
                + " |"
            )

VR = RUNS["vercel"]
T.append(
    "\n## Vercel lifecycle detail (seconds, median [95% CI])\n\n"
    "| Shape | create → API returns | create incl. SDK retry waits | first command | exec round trip | delete call | create errors | jobs with an SDK/harness 429 wait |\n"
    "|---|---|---|---|---|---|---|---|"
)
for sh in ("medium", "large"):
    rs = [r for r in VR if r["job"]["shape"] == sh]
    lc = [r for r in rs if r["job"]["kind"] == "lifecycle"]
    T.append(
        f"| {sh} lifecycle (n={len(lc)}) | {fmt(ci([r.get('create_s') for r in lc]))} | "
        f"{fmt(ci([r.get('create_raw_s') for r in lc]))} | {fmt(ci([r.get('first_cmd_s') for r in lc]))} | "
        f"{fmt(ci([st.median(r['exec_rtt_s']) for r in lc if r.get('exec_rtt_s')]))} | "
        f"{fmt(ci([r.get('delete_s') for r in lc]))} | {sum(1 for r in lc if r.get('create_error'))}/{len(lc)} | "
        f"{sum(1 for r in lc if (r.get('create_sdk_retry_wait_s') or 0) > 0)}/{len(lc)} |"
    )
    T.append(
        f"| {sh} all {len(rs)} grid jobs | {fmt(ci([r.get('create_s') for r in rs]))} | "
        f"{fmt(ci([r.get('create_raw_s') for r in rs]))} | {fmt(ci([r.get('first_cmd_s') for r in rs]))} | "
        f"{fmt(ci([st.median(r['exec_rtt_s']) for r in rs if r.get('exec_rtt_s')]))} | "
        f"{fmt(ci([r.get('delete_s') for r in rs]))} | {sum(1 for r in rs if r.get('create_error'))}/{len(rs)} | "
        f"{sum(1 for r in rs if (r.get('create_sdk_retry_wait_s') or 0) > 0)}/{len(rs)} |"
    )

T.append(
    "\n## Vercel CPU under 180 s sustained all-core load (sha256 rounds per 5 s window, all cores)\n\n"
    "| Shape | first window | last window | min/max ratio |\n|---|---|---|---|"
)
for sh in ("medium", "large"):
    xs = [g(r, "cpu", "out") for r in cellruns("vercel", sh, "lifecycle")]
    xs = [x for x in xs if x]
    T.append(
        f"| {sh} | {fmt(ci([x['first'] for x in xs]))} | {fmt(ci([x['last'] for x in xs]))} | "
        f"{fmt(ci([x['min'] / x['max'] for x in xs if x['max']]))} |"
    )

T.append(
    "\n## Vercel git clone (wall seconds; Mbit/s received)\n\n"
    "| Shape | Repo | Mode | seconds | Mbit/s | failures |\n|---|---|---|---|---|---|"
)
for sh in ("medium", "large"):
    for repo in ("next.js", "pytorch", "kubernetes"):
        for m in ("full", "shallow"):
            rs = [
                r
                for r in cellruns("vercel", sh, "clone")
                if r["job"]["repo"].endswith(repo) and r["job"]["mode"] == m
            ]
            if not rs:
                continue
            ok = [g(r, "clone", "out") for r in rs]
            ok = [x for x in ok if x and x["rc"] == 0]
            T.append(
                f"| {sh} | {repo} | {m} | {fmt(ci([x['seconds'] for x in ok]))} | "
                f"{fmt(ci([x['mbit_s'] for x in ok]))} | {len(rs) - len(ok)}/{len(rs)} |"
            )

T.append(
    "\n## Vercel memory (128 MB steps up to 2x RAM)\n\n"
    "| Shape | RAM GiB | GiB reached (progress file) | how it stopped | sandbox answered 5 s later |\n"
    "|---|---|---|---|---|"
)
for sh in ("medium", "large"):
    rs = cellruns("vercel", sh, "mem")
    reach = []
    for r in rs:
        t = (g(r, "mem_after", "out") or "").strip().splitlines()
        try:
            reach.append(int(t[0].split()[0]) / 1024)
        except Exception:  # noqa: BLE001
            o = g(r, "mem", "out")
            reach.append(o["allocated_mb"] / 1024 if o else None)
    how = collections.Counter(
        (
            "process OOM-killed (137)"
            if g(r, "mem", "rc") == 137 or "Killed" in str(g(r, "mem", "tail") or "")
            else str(g(r, "mem", "rc"))
        )
        for r in rs
    )
    T.append(
        f"| {sh} | {P.SHAPES[sh][1]} | {fmt(ci(reach))} | {dict(how)} | "
        f"{sum(1 for r in rs if g(r, 'mem_after', 'alive'))}/{len(rs) if rs else 0} |"
    )

T.append(
    "\n## Vercel disk (write until ENOSPC; GB, MB/s). The 64 GB NVMe is one filesystem: "
    "the home probe and the `/var/tmp` probe share it\n\n"
    "| Shape | home GB | home MB/s | /var/tmp probe GB (stops at 12) |\n|---|---|---|---|"
)
for sh in ("medium", "large"):
    rs = cellruns("vercel", sh, "disk")
    T.append(
        f"| {sh} | {fmt(ci([(g(r, 'disk_home', 'out', 'written_b') or 0) / 1e9 for r in rs if g(r, 'disk_home', 'out')]))} | "
        f"{fmt(ci([g(r, 'disk_home', 'out', 'mb_per_s') for r in rs]))} | "
        f"{fmt(ci([(g(r, 'disk_root', 'out', 'written_b') or 0) / 1e9 for r in rs if g(r, 'disk_root', 'out')]))} |"
    )

T.append("\n## Vercel failures and retried answers (kept)\n")
T.append(
    f"- grid jobs: {len(VR)} result files, {sum(1 for r in VR if 'error' in r)} with an error, "
    f"{sum(1 for r in VR if r.get('create_error'))} create errors."
)
if FAIL429:
    kinds = collections.Counter(
        (
            "httpx ConnectTimeout after a successful create"
            if "ConnectTimeout" in r.get("first_attempt_failure", "")
            else "429 vCPU allocation limit, SDK retries exhausted"
        )
        for r in FAIL429
    )
    T.append(
        "- first-attempt grid jobs that failed (kept in `vercel/results/runs_vercel_failed_first_attempt/`, "
        f"then re-run): {len(FAIL429)} = " + ", ".join(f"{k}: {v}" for k, v in kinds.items())
    )
mx = collections.Counter()
for r in VR:
    for k, v in (r.get("retries_so_far") or {}).items():
        mx[k] = max(mx[k], v)
T.append(
    "- SDK/harness retry counters (cumulative per process, max seen at a create; lower bound): "
    + (", ".join(f"{k}: {v}" for k, v in sorted(mx.items())) or "none")
)

B = [_load_json(f) for f in glob.glob(f"{V}/results/burst/*.json")]
OB = [_load_json(f) for f in glob.glob(f"{ROOT}/results/burst/*.json")]


def burst_rows(Bs):
    out = []
    for b in sorted(Bs, key=lambda x: (x["provider"], x["N"], x["wave"])):
        ok = [r for r in b["runs"] if "error" not in r]
        cs = sorted(r["create_s"] for r in ok)
        out.append(
            f"| {b['provider']} | {b['N']} | {b['wave']}{' (retry on)' if b.get('retry') else ''} | "
            f"{len(ok)}/{b['N']} | "
            f"{dict(collections.Counter(str(r['error'].get('code') or str(r['error'].get('exc', ''))[:40]) for r in b['runs'] if 'error' in r))} | "
            f"{fmt(ci(cs))} | {cs[int(0.95 * (len(cs) - 1))] if cs else ''} | {b['wall_s']} | {b.get('retries') or ''} |"
        )
    return out


T.append(
    "\n## Vercel burst creation (N creates fired at once, Medium, no retry unless marked)\n\n"
    "Waves a/b are 20 s apart, c/d 75 s apart (as for InstaBox), e is 100 at once with no retry, "
    "r is 100 with the SDK and harness retries on. Vercel Pro starts at a 150 vCPU/min allocation "
    "rate (75 Medium sandboxes) and ramps; see `vercel/VERCEL.md`.\n\n"
    "| Provider | N | wave | succeeded | errors | create s median [CI] | p95 | wall s | retries |\n"
    "|---|---|---|---|---|---|---|---|---|"
)
T += burst_rows(B)
T.append(
    "\n### Burst success at N = 10 / 25 / 45 (clean waves only: Agent37, Daytona a+b; InstaBox c+d; Vercel a+b and c+d)\n\n"
    "| Provider | N=10 | N=25 | N=45 |\n|---|---|---|---|"
)


def succ(prov, waves, n, pool):
    bs = [b for b in pool if b["provider"] == prov and b["N"] == n and b["wave"] in waves]
    return (
        f"{sum(sum(1 for r in b['runs'] if 'error' not in r) for b in bs)}/{sum(b['N'] for b in bs)}"
        if bs
        else ""
    )


for p, w, pool in (
    ("agent37", ("a", "b"), OB),
    ("daytona", ("a", "b"), OB),
    ("instabox", ("c", "d"), OB),
    ("vercel", ("a", "b", "c", "d"), B),
):
    T.append(f"| {p} | " + " | ".join(succ(p, w, n, pool) for n in (10, 25, 45)) + " |")

SW = [_load_json(f) for f in sorted(glob.glob(f"{V}/results/sleepwake/sleepwake__vercel__*.json"))]
T.append(
    "\n## Vercel stop / resume (5 cycles per instance: stop, 120 s idle, wake, first command)\n\n"
    "`stop()` snapshots the filesystem automatically (persistent sandbox) and ends the session; "
    'memory and processes are not kept. "resume" = explicit `resume_sandbox` call then a command; '
    '"auto" = no resume call, the first command resumes it. Process kept = a background counter '
    "advanced between one wake and the next sleep.\n\n"
    "| Mode | instances | cycles | stop call s | resume call s | wake → first command s (median [CI]) | file kept | process kept | errors |\n"
    "|---|---|---|---|---|---|---|---|---|"
)
for mode in ("resume", "auto"):
    ss = [s for s in SW if s.get("wake_mode") == mode]
    cy = [c for s in ss for c in s["cycles"]]
    if not ss:
        continue
    kept = tot = 0
    for s in ss:
        cyc = s["cycles"]
        for a, b in itertools.pairwise(cyc):
            tot += 1
            try:
                kept += int(b["counter_before"]) > int(a["after"][1])
            except Exception:  # noqa: BLE001, S110
                pass
    T.append(
        f"| {mode} | {len(ss)} | {len(cy)} | {fmt(ci([c['sleep_call_s'] for c in cy]))} | "
        f"{fmt(ci([c.get('resume_call_s') for c in cy]))} | "
        f"{fmt(ci([c['wake_to_first_cmd_s'] for c in cy]))} | "
        f"{sum(1 for c in cy if 'persisted' in c['after'])}/{len(cy)} | {kept}/{tot} | "
        f"{sum(1 for c in cy if c.get('last_err'))}+{sum(1 for s in ss if 'error' in s)} |"
    )

SN = [_load_json(f) for f in sorted(glob.glob(f"{V}/results/sleepwake/snapshot_resume__*.json"))]
if SN:
    cy = [c for s in SN for c in s["cycles"]]
    T.append(
        "\n## Vercel snapshot-based resume (snapshot the sandbox, 120 s idle, create a NEW sandbox from the snapshot; the restored one becomes the next producer)\n\n"
        "| chains | cycles | snapshot call s | restore create s | restore → first command s (create + first command) | first command alone s | file kept | process kept | snapshot size GB | errors |\n"
        "|---|---|---|---|---|---|---|---|---|---|"
    )
    T.append(
        f"| {len(SN)} | {len(cy)} | {fmt(ci([c['snapshot_call_s'] for c in cy]))} | "
        f"{fmt(ci([c['restore_create_s'] for c in cy]))} | "
        f"{fmt(ci([c['restore_to_first_cmd_s'] for c in cy]))} | "
        f"{fmt(ci([c['first_cmd_s'] for c in cy]))} | "
        f"{sum(1 for c in cy if c['file_kept'])}/{len(cy)} | "
        f"{sum(1 for c in cy if c['process_kept'])}/{len(cy)} | "
        f"{fmt(ci([(c.get('snapshot_size_b') or 0) / 1e9 for c in cy]))} | "
        f"{sum(1 for c in cy if c.get('last_err'))}+{sum(1 for s in SN if 'error' in s)} |"
    )

TO = [_load_json(f) for f in sorted(glob.glob(f"{V}/results/sleepwake/timeout_resume__*.json"))]
if TO:
    cy = [c for s in TO for c in s["cycles"]]
    T.append(
        "\n## Vercel session-timeout auto-stop and auto-resume (session limit 60 s; Vercel stops the session itself, the next plain command resumes it)\n\n"
        "| instances | cycles | stopped by Vercel after (s from session start) | wake → first command s (median [CI]) | file kept | errors |\n"
        "|---|---|---|---|---|---|"
    )
    T.append(
        f"| {len(TO)} | {len(cy)} | {fmt(ci([c['stopped_after_session_start_s'] for c in cy]))} | "
        f"{fmt(ci([c['wake_to_first_cmd_s'] for c in cy]))} | "
        f"{sum(1 for c in cy if c['file_kept'])}/{len(cy)} | "
        f"{sum(1 for c in cy if c.get('last_err'))}+{sum(1 for s in TO if 'error' in s)} |"
    )

os.makedirs(f"{V}/out", exist_ok=True)
_write_open(f"{V}/out/tables.md", "w", "\n".join(T) + "\n")
_dump_json(f"{V}/out/summary.json", "w", S, indent=1)
print("\n".join(T))
