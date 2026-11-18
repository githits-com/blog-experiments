"""Prints the InstaBox 24 h soak summary. If REPORT.md or INSTABOX.md is present and contains <!--SOAK--> markers, updates that section. Status stays 'in progress' until both soak files carry 'deleted'."""

import collections
import itertools
import json
import os
import statistics as st
import sys
import time


def _load_json(path):
    with open(path) as handle:
        return json.load(handle)


def _read_open(*args):
    with open(*args) as handle:
        return handle.read()


def _write_open(path, mode, text):
    with open(path, mode) as handle:
        handle.write(text)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not (
    os.path.isfile(f"{ROOT}/results/soak/soak__instabox.json")
    or os.path.isfile(f"{ROOT}/results/soak/soak__instabox-auto.json")
):
    sys.exit(
        "No InstaBox soak JSON under results/soak/. This repository stores code only; run output is not committed.\n"
        "Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n"
        "Start a soak with harness/soak.py, then re-run this script."
    )


def pt(t):
    return time.strftime("%b %d %I:%M %p PT", time.localtime(t))  # box clock is America/Los_Angeles


L = []
done = True
for mode, f, desc in (
    (
        "manual",
        "soak__instabox.json",
        "explicit suspend, 30 min idle, resume, then `cat marker` (idle-pause setting 1800 s, never reached)",
    ),
    (
        "auto",
        "soak__instabox-auto.json",
        "no explicit sleep, idle pause 300 s, a plain exec every 30 min wakes it by itself",
    ),
):
    p = f"{ROOT}/results/soak/{f}"
    if not os.path.exists(p):
        L.append(f"- {mode}: no result file yet")
        done = False
        continue
    r = _load_json(p)
    c = r["checks"]
    w = [x for x in c if "wake_s" in x]
    err = [x for x in c if "err" in x]
    ts = [r["start"]] + [x["t"] for x in c]
    fin = "deleted" in r
    done &= fin
    ws = [x["wake_s"] for x in w]
    sb = collections.Counter(x.get("state_before") for x in w if x.get("state_before"))
    L.append(
        f"- **{mode}** ({desc}): {len(w)} wakes OK, {len(err)} failed wake attempts, {sum(1 for x in c if 'sleep_err' in x)} suspend errors; marker file present {sum(1 for x in w if x['ok'])}/{len(w)}; wake to first command median {round(st.median(ws), 2) if ws else '-'} s (min {min(ws) if ws else '-'}, max {max(ws) if ws else '-'}); longest gap between checks {round(max(b - a for a, b in itertools.pairwise(ts)) / 3600, 2)} h; "
        + (f"state just before the wake: {dict(sb)}; " if sb else "")
        + (
            f"instance deleted: {r.get('deleted')}; ended {pt(r['start'] + r['life_s'])}; retries {r.get('retries')}"
            if fin
            else f"still running, last check {pt(ts[-1])}"
        )
    )
    errs = [x["err"][:140] for x in err][:3]
    if errs:
        L.append(f"  - first errors: {errs}")
txt = (
    (
        "**24 h soak finished.**"
        if done
        else "**24 h soak: in progress** (as of " + pt(time.time()) + ")."
    )
    + "\n\n"
    + "\n".join(L)
    + "\n"
)
print(txt)
for fn in ("REPORT.md", "INSTABOX.md"):
    p = f"{ROOT}/{fn}"
    if not os.path.isfile(p):
        continue
    s = _read_open(p)
    if "<!--SOAK-->" not in s or "<!--/SOAK-->" not in s:
        continue
    a = s.index("<!--SOAK-->") + len("<!--SOAK-->")
    b = s.index("<!--/SOAK-->")
    _write_open(p, "w", s[:a] + "\n" + txt + s[b:])
