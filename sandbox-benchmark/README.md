# Agent37, Daytona, InstaBox, and Vercel sandboxes

**Warning: running this costs real money.** Each provider bills running sandboxes (and, for Vercel, snapshot storage). Set the spend caps below, watch the provider usage pages, and run cleanup when you are done. The harness only enforces modeled caps on new grid jobs; it cannot read or stop on the billed amount.

Infrastructure benchmark of [Agent37](https://agent37.com), [Daytona](https://www.daytona.io), [InstaBox](https://instabox.sh), and [Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) on matched shapes (2 vCPU / 4 GiB and 4 vCPU / 8 GiB). No LLM is called.

**Results** are in the blog post: [Agent37 vs Daytona: sandboxes for coding agents](https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/). This folder is the code that produced them. `results/`, `logs/`, and `out/` are created by a run and are gitignored.

## What it measures

| Metric                   | How                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------- |
| Create → API returns     | Wall time of the create call                                                            |
| Time to first command    | First `true` after create, plus 10 exec round trips                                     |
| CPU under sustained load | One sha256 loop per vCPU for 180 s                                                      |
| git clone throughput     | Full and shallow clones of `vercel/next.js`, `pytorch/pytorch`, `kubernetes/kubernetes` |
| Memory limit behaviour   | Allocate and touch 128 MB steps up to 2× the shape's RAM                                |
| Disk limits              | Write until ENOSPC on the home volume and the OS layer                                  |
| Burst creation           | 10 / 25 / 45 creates fired at once (plus an Agent37 over-limit probe at 55)             |
| Billed vs modeled        | Provider usage API against lifetime × published rate                                    |
| Sleep/wake persistence   | File and background process across 5 sleep cycles                                       |
| 24 h soak                | One Medium instance per provider, woken every 30 min                                    |

Design, sample sizes, and the cost model: [`DESIGN.md`](./DESIGN.md).

## Prerequisites

- Python 3.11+
- An [Agent37](https://agent37.com) API key, a [Daytona](https://www.daytona.io) API key, an [InstaBox](https://instabox.sh) API key, and a Vercel token plus team and project ids for the cells you run
- Network access to create sandboxes and to clone the three public GitHub repos above

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

| Variable            | Required for            | Notes                                                                      |
| ------------------- | ----------------------- | -------------------------------------------------------------------------- |
| `AGENT37_API_KEY`   | Agent37 cells, billing  | Never printed or written by the harness                                    |
| `DAYTONA_API_KEY`   | Daytona cells           | Read by the Daytona SDK; never printed                                     |
| `INSTABOX_API_KEY`  | InstaBox cells, billing | Sent as `X-API-Key`; never printed or written                              |
| `INSTABOX_TEMPLATE` | optional                | Default `agent-browser`                                                    |
| `SPEND_CAP_A37`     | optional                | Default `$5`. Runner stops starting Agent37 jobs at the cap.               |
| `SPEND_CAP_DT`      | optional                | Default `$10`.                                                             |
| `SPEND_CAP_IB`      | optional                | Default `$10`.                                                             |
| `SOAK=1`            | optional                | Starts the Agent37 and Daytona 24 h soaks in the background from `run.sh`. |
| `PY`                | optional                | Python interpreter. Defaults to `python3`.                                 |
| `VERCEL_TOKEN`      | Vercel cells            | Official `vercel-sandbox` SDK; never printed or written                    |
| `VERCEL_TEAM_ID`    | Vercel cells            | Team id; never printed                                                     |
| `VERCEL_PROJECT_ID` | Vercel cells            | Project id; never printed                                                  |
| `SPEND_CAP_VC`      | optional                | Default `$15`. Runner stops starting Vercel *grid* jobs at the cap.        |
| `SPEND_CAP_TOTAL_VC`| optional                | Default `$25`. Compared to modeled total Vercel spend in `spend_vercel.py`.|
| `VC_WAKE`           | optional                | `resume` or `auto`. Vercel sleep/wake mode. See [`vercel/VERCEL.md`](./vercel/VERCEL.md). |

## Reproduce Agent37 and Daytona

Published numbers are only in the blog post. A fresh checkout has no result files. To regenerate the Agent37 and Daytona grid:

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

If `results/` has no run output, the analysis scripts print where the published numbers are and how to reproduce them, then exit.

The cost estimate and the default caps are in [`DESIGN.md`](./DESIGN.md). The Agent37/Daytona grid and bursts take on the order of 45 minutes; the soak reports the next day.

## InstaBox

InstaBox uses the same probes and job kinds. It does not re-run the Agent37 or Daytona cells. `harness/providers.py` talks to `https://api.instabox.sh`: create, delete, suspend, and resume return an operation followed with `GET /v1/operations/{id}?wait=25s`. Lifecycle calls send `Idempotency-Key`. Deletes send `X-Confirm-Delete`. Exec is `POST /v1/machines/{id}/exec`. Upload is `PUT /v1/machines/{id}/files`. Retryable `429` and `503` answers are retried after `Retry-After` and counted. `create_s` does not include that wait.

**Key.** Export `INSTABOX_API_KEY`. The harness reads it into the `X-API-Key` header and never prints or stores it.

**Template.** `agent-browser`, set with `INSTABOX_TEMPLATE` (the default). It is InstaBox's default image: Debian 13, a Firecracker microVM, and a pre-booted pool. Exec runs as the unprivileged user `user`. Home is `/data/home`. The follow-up script also runs a Large lifecycle check with `INSTABOX_TEMPLATE=universal`, which has no pre-booted pool.

**Plan.** Pro. The benchmark uses the 2 vCPU / 4 GiB and 4 vCPU / 8 GiB shapes. Pro limits starts to 30 a minute across create, start, resume, and wake. A faster burst is a retryable `429 rate_limited`. Bursts record that error unless `harness/burst.py` is given `retry`, which waits for `Retry-After`.

**Disk.** 20 GiB, fixed, on `/data`. It is not settable at create. The disk probe writes that volume until ENOSPC, then writes `/var/tmp` on the root disk.

**Idle pause.** The grid, sleep/wake, and the manual soak leave the default 1800 s idle pause alone and suspend or delete explicitly. The soak has two variants: `manual` (explicit suspend, 30 minutes idle, resume, then `cat` the marker) and `auto` (no explicit sleep, idle pause 300 s, a plain exec every 30 minutes has to wake the machine). The harness records the machine state just before an automatic wake.

```bash
export INSTABOX_API_KEY=...
python3 harness/make_jobs_instabox.py
python3 harness/bench.py results/jobs_instabox_pilot.json results/runs_instabox_pilot --ib-workers 2
python3 harness/bench.py results/jobs_instabox.json results/runs_instabox --ib-workers 50
./harness/run_instabox_bursts.sh          # 10 / 25 / 45, then one wave that retries
./harness/run_instabox_followups.sh       # lifecycle inside the start limit, clean burst gaps, universal template
for r in 0 1 2; do python3 harness/sleepwake.py instabox medium 5 120 results/sleepwake $r; done
python3 harness/soak.py instabox 24 30 results/soak manual
python3 harness/soak.py instabox 24 30 results/soak auto
```

Then, from the local files:

```bash
python3 analysis/analyze.py
python3 analysis/spend.py
python3 analysis/billing_instabox.py      # INSTABOX_API_KEY; GET /v1/usage lags up to an hour
python3 analysis/charts_instabox.py       # out/*.png
python3 analysis/soak_summary.py          # prints the soak summary
```

List price and the `$10` cap are in [`DESIGN.md`](./DESIGN.md).


## Vercel Sandbox

Vercel uses the same probes and job kinds. It does not re-run the Agent37, Daytona, or InstaBox cells. `harness/providers.py` talks to the official Python SDK `vercel-sandbox` (sync API). Setup, sizes, the cost model, and the full command list: [`vercel/VERCEL.md`](./vercel/VERCEL.md).

**This costs real money.** Export `VERCEL_TOKEN`, `VERCEL_TEAM_ID`, and `VERCEL_PROJECT_ID`. The harness and the SDK read them and never print or store them. The grid cap is `SPEND_CAP_VC` (default `$15`, modeled). Bursts and persistence tests are not auto-capped; plan a total budget (`SPEND_CAP_TOTAL_VC`, default `$25`) and confirm billed spend on the Vercel Usage page.

**Shapes.** Medium 2 vCPU / 4 GiB and Large 4 vCPU / 8 GiB (2 GiB per vCPU is fixed). Disk is a fixed 64 GB ephemeral NVMe. Default image `vercel/sandbox/universal`. Exec runs as `ubuntu`. Home is `/home/ubuntu`.

**Persistence.** `stop()` snapshots the filesystem and drops memory and processes. Grid and burst jobs destroy a still-running sandbox (no snapshot). Cleanup must also delete leftover snapshots.

```bash
export VERCEL_TOKEN=... VERCEL_TEAM_ID=... VERCEL_PROJECT_ID=...
SMOKE_OUT=vercel/results/smoke python3 harness/smoke.py vercel medium
python3 harness/make_jobs_vercel.py
python3 harness/bench.py vercel/results/jobs_vercel_pilot.json vercel/results/runs_pilot --vc-workers 2
./vercel/run_vercel.sh
```

Then, from the local files:

```bash
python3 vercel/analysis/analyze_vercel.py
python3 vercel/analysis/spend_vercel.py
python3 vercel/analysis/charts_vercel.py
```

## Layout

```
harness/          provider clients, probes, bench / burst / sleepwake / soak / Vercel runners
analysis/         tables, spend, billing, InstaBox charts and soak summary
vercel/           Vercel run script, analysis, and VERCEL.md (results under vercel/results/)
DESIGN.md         pre-registered design, including the InstaBox and Vercel amendments
run.sh            Agent37 and Daytona orchestrated run
requirements.txt
results/          local run output (gitignored; not in this repo)
logs/             local runner stdout (gitignored)
out/              local tables, spend, billing, and charts (gitignored)
```

## Caveats

- **Base images differ.** Agent37 `agent37-base` is Debian 12 with git 2.39; Daytona's default image has its own git; InstaBox `agent-browser` is Debian 13 on Firecracker with git 2.47. Clone times include that difference. InstaBox exec is unprivileged; Agent37 exec in this harness runs as root.
- **Agent37 default overcommits.** The `default` type shares host CPU and memory by design. The `performance` and `vm` types are the like-for-like comparison with dedicated resources.
- **Disk is not the same size.** Agent37 and Daytona use 8 GiB on Medium and 10 GiB on Large. InstaBox is a fixed 20 GiB `/data`. Vercel is a fixed 64 GB NVMe.
- **InstaBox starts are rate limited** at 30 a minute on Pro. The harness counts the retries. It does not hide them.
- **Published list prices only**, before credits and plan fees. Vercel bills CPU only while it is busy and memory the whole time; the others bill allocation.
- **Vercel was added after the other three.** A Vercel run on a different day is not a same-day comparison. The official SDK retries 429/5xx silently unless a no-retry burst turns that off.
