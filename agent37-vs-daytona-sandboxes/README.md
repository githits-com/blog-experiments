# Agent37 vs Daytona sandboxes

Infrastructure benchmark of [Agent37](https://agent37.com) and [Daytona](https://www.daytona.io) sandboxes on matched shapes (2 vCPU / 4 GiB and 4 vCPU / 8 GiB). No LLM is called.

**Blog post:** [Agent37 vs Daytona: sandboxes for coding agents](https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/)

## What was measured

| Metric | Summary |
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

Full design: [`DESIGN.md`](./DESIGN.md). Results write-up: [`REPORT.md`](./REPORT.md). Generated tables: [`out/tables.md`](./out/tables.md).

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

## Reproduce the tables (free)

Committed result JSONs are enough. No API keys needed:

```bash
python3 analysis/analyze.py    # writes out/tables.md
python3 analysis/spend.py      # writes out/spend.json from sandboxes.jsonl
```

`analysis/billing.py` needs `AGENT37_API_KEY` and should be run more than an hour after the last Agent37 job so hourly settlement has landed.

## Re-run the paid grid

```bash
export AGENT37_API_KEY=... DAYTONA_API_KEY=...
./run.sh                 # pilot → grid + sleep/wake → bursts → cleanup → tables
SOAK=1 ./run.sh          # same, and start the 24 h soak alongside
```

Expected cost at published list prices: about **$0.55 Agent37 + $2.10 Daytona** (hard caps $5 / $10). Wall clock for the grid and bursts is about 45 minutes; the soak reports the next day.

## Layout

```
harness/          provider clients, probes, bench / burst / sleepwake / soak runners
analysis/         analyze.py (tables), spend.py, billing.py
results/          one JSON per sandbox, plus burst/, sleepwake/, soak/, sandboxes.jsonl
out/              tables.md, spend.json, billing.md / billing.json
logs/             runner stdout from the original Nov 3–4, 2026 run
DESIGN.md         pre-registered design
REPORT.md         results write-up
run.sh            full orchestrated run
```

## Caveats

- **Full-clone gap.** Full clones ran 40–50 at a time against GitHub from each provider's shared outbound addresses. Agent37 default and Performance finished in a median 90–175 s; Daytona and Agent37 VM took 510–680 s. Shallow clones were the same everywhere (23–35 s). The full-clone gap likely reflects how GitHub treats each provider's outbound addresses at that concurrency, not raw sandbox speed; earlier one-at-a-time Daytona clones took 116–184 s.
- **Overnight soak gaps.** The harness host was paused overnight, so wakes were skipped for about 11.6–12.5 h and then 3.5–4.5 h. The instances stayed parked through those gaps; marker files were intact on every successful wake.
- **Base images differ.** Agent37 `agent37-base` is Debian 12 with git 2.39; Daytona's default image has its own git. Clone times include that difference.
- **Agent37 default overcommits.** The `default` type shares host CPU and memory by design. The `performance` and `vm` types are the like-for-like comparison with dedicated resources.
- **Published list prices only**, before credits and plan fees.
