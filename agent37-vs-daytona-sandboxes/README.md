# Agent37 vs Daytona sandboxes

Infrastructure benchmark of [Agent37](https://agent37.com) and [Daytona](https://www.daytona.io) sandboxes on matched shapes (2 vCPU / 4 GiB and 4 vCPU / 8 GiB). No LLM is called.

**Results** are in the blog post: [Agent37 vs Daytona: sandboxes for coding agents](https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/). This folder is the code that produced them. `results/`, `logs/`, and `out/` are created by a run and are gitignored.

## What it measures

| Metric | How |
|---|---|
| Create → API returns | Wall time of the create call |
| Time to first command | First `true` after create, plus 10 exec round trips |
| CPU under sustained load | One sha256 loop per vCPU for 180 s |
| git clone throughput | Full and shallow clones of `vercel/next.js`, `pytorch/pytorch`, `kubernetes/kubernetes` |
| Memory limit behaviour | Allocate and touch 128 MB steps up to 2× the shape's RAM |
| Disk limits | Write until ENOSPC on the home volume and the OS layer |
| Burst creation | 10 / 25 / 45 creates fired at once (plus an Agent37 over-limit probe at 55) |
| Billed vs modeled | Agent37 `GET /v1/usage` against lifetime × published rate |
| Sleep/wake persistence | File and background process across 5 sleep cycles |
| 24 h soak | One Medium instance per provider, woken every 30 min |

Design, sample sizes, and the cost model: [`DESIGN.md`](./DESIGN.md).

## Prerequisites

- Python 3.11+
- An [Agent37](https://agent37.com) API key and a [Daytona](https://www.daytona.io) API key
- Network access to create sandboxes and to clone the three public GitHub repos above

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

| Variable | Required for | Notes |
|---|---|---|
| `AGENT37_API_KEY` | Agent37 cells, billing | Never printed or written by the harness |
| `DAYTONA_API_KEY` | Daytona cells | Read by the Daytona SDK; never printed |
| `SPEND_CAP_A37` | optional | Default `$5`. Runner stops starting Agent37 jobs at the cap. |
| `SPEND_CAP_DT` | optional | Default `$10`. |
| `SOAK=1` | optional | Starts the 24 h soak in the background from `run.sh`. |
| `PY` | optional | Python interpreter. Defaults to `python3`. |

## Reproduce

Published numbers are only in the blog post. A fresh checkout has no result files. To regenerate them:

```bash
export AGENT37_API_KEY=... DAYTONA_API_KEY=...
./run.sh                 # pilot → grid + sleep/wake → bursts → cleanup → tables
SOAK=1 ./run.sh          # same, and start the 24 h soak alongside
```

`./run.sh` writes one JSON per sandbox under `results/`, appends every create and delete to `results/sandboxes.jsonl`, and writes runner stdout under `logs/`. It then runs `analysis/analyze.py`, which writes `out/tables.md`.

After the run:

```bash
python3 analysis/analyze.py    # out/tables.md from local results/
python3 analysis/spend.py      # out/spend.json from results/sandboxes.jsonl
```

`analysis/billing.py` needs `AGENT37_API_KEY` and should be run more than an hour after the last Agent37 job so hourly settlement has landed. It writes `out/billing.json` and `out/billing.md`.

If `results/` has no run output, those scripts print where the published numbers are and how to reproduce them, then exit.

The cost estimate and the default caps are in [`DESIGN.md`](./DESIGN.md). The grid and bursts take on the order of 45 minutes; the soak reports the next day.

## Layout

```
harness/          provider clients, probes, bench / burst / sleepwake / soak runners
analysis/         analyze.py (tables), spend.py, billing.py
DESIGN.md         pre-registered design
run.sh            full orchestrated run
requirements.txt
results/          local run output (gitignored; not in this repo)
logs/             local runner stdout (gitignored)
out/              local tables, spend, and billing files (gitignored)
```

## Caveats

- **Base images differ.** Agent37 `agent37-base` is Debian 12 with git 2.39; Daytona's default image has its own git. Clone times include that difference.
- **Agent37 default overcommits.** The `default` type shares host CPU and memory by design. The `performance` and `vm` types are the like-for-like comparison with dedicated resources.
- **Published list prices only**, before credits and plan fees.
