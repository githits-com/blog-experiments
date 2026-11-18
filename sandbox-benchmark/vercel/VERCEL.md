# Vercel Sandbox

Adds [Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) as a fourth provider next to Agent37, Daytona, and InstaBox. Same probes, job kinds, repos, and reps per cell. AWS is out of scope.

**This costs real money.** Every create, every running sandbox (provisioned memory the whole time, Active CPU while the vCPU is busy), and leftover snapshot storage is billed by Vercel. Set a cap, watch the [Vercel Usage](https://vercel.com/dashboard) page, and delete sandboxes and snapshots when you are done. The harness only enforces a *modeled* grid cap (`SPEND_CAP_VC`); it cannot read or stop on the billed amount.

## Environment variables

Export these before any command. The harness and the official `vercel-sandbox` SDK read them and never print or write them.

| Variable             | Required | Notes                                                                 |
| -------------------- | -------- | --------------------------------------------------------------------- |
| `VERCEL_TOKEN`       | yes      | Vercel access token with access to the team and project               |
| `VERCEL_TEAM_ID`     | yes      | Team id                                                               |
| `VERCEL_PROJECT_ID`  | yes      | Project id (an empty project is enough)                               |
| `SPEND_CAP_VC`       | optional | Default `$15`. Runner stops starting new *grid* jobs at this modeled cap. |
| `SPEND_CAP_TOTAL_VC` | optional | Default `$25`. Used only by `spend_vercel.py` when it compares modeled total spend to a cap. Grid + bursts + persistence tests should fit this. |
| `VC_W`               | optional | Grid workers. Default `50`.                                           |
| `VC_WAKE`            | optional | `resume` (explicit `resume_sandbox`) or `auto` (first command resumes). Used by `sleepwake.py`. |
| `PY`                 | optional | Python interpreter. Defaults to `python3`.                            |
| `SMOKE_OUT`          | optional | Directory for `harness/smoke.py` output.                              |

## Sizes tested

- **Medium:** 2 vCPU / 4 GiB
- **Large:** 4 vCPU / 8 GiB
- Disk is a fixed 64 GB ephemeral NVMe on every size (not settable).
- Default image: `vercel/sandbox/universal`. Exec runs as `ubuntu` (sudo available). Home is `/home/ubuntu`.
- Region: the SDK default (`iad1`).
- Grid jobs set `execution_time_limit` to 1 hour (the SDK default is 5 minutes). The timeout-resume test uses a 60 s limit.

## How to run

From the experiment folder, after `pip install -r requirements.txt`:

```bash
export VERCEL_TOKEN=... VERCEL_TEAM_ID=... VERCEL_PROJECT_ID=...

# smoke, then a 2-job pilot
SMOKE_OUT=vercel/results/smoke python3 harness/smoke.py vercel medium
python3 harness/make_jobs_vercel.py
python3 harness/bench.py vercel/results/jobs_vercel_pilot.json vercel/results/runs_pilot --vc-workers 2

# full run: grid + persistence tests, 10 min idle, bursts, cleanup, tables
./vercel/run_vercel.sh
```

Or the analysis only, from local `vercel/results/` (and, for the comparison tables, the other providers' `results/` if you have them):

```bash
python3 vercel/analysis/analyze_vercel.py   # vercel/out/tables.md
python3 vercel/analysis/spend_vercel.py     # vercel/out/spend.md
python3 vercel/analysis/charts_vercel.py    # vercel/out/*.png
```

`vercel/results/`, `vercel/logs/`, and `vercel/out/` are gitignored. If they are missing, the analysis scripts print a short message and exit.

## What the harness does

- `harness/make_jobs_vercel.py` — 96 grid jobs (lifecycle × 10, clones of the three repos full and shallow × 5, memory × 5, disk × 3) for Medium and Large, plus a 2-job pilot file.
- `harness/bench.py --vc-workers` — one fresh sandbox per job: create, probes, delete. Records SDK retry waits separately; `create_s` excludes them. After the probes it reads `/proc/stat` so modeled Active CPU can use the guest's busy time.
- `harness/sleepwake.py` — stop, 120 s idle, wake. `VC_WAKE=resume` calls `resume_sandbox` first; `VC_WAKE=auto` lets the first command resume the session. Use a distinct `rep` (for example `a0`) so result files do not collide.
- `harness/snapshot_resume_vercel.py` — snapshot the sandbox, idle, create a *new* sandbox from that snapshot.
- `harness/timeout_resume_vercel.py` — short session limit; Vercel stops the session; the next command auto-resumes it.
- `harness/burst.py` — N creates at once (10, 25, 45, and 100). Without the `retry` argument the SDK's own retries are switched off so errors are recorded; with `retry` they stay on and the harness also retries 429s.
- `harness/cleanup.py vercel --all` — deletes this experiment's sandboxes *and* remaining snapshots.

The official Python SDK (`vercel-sandbox`) retries 429/5xx twice with short backoff. The provider client counts those retries by hooking `vercel.sandbox._internal.retry` (not a public API) and can disable them for no-retry burst waves. A further harness retry covers leftover vCPU-allocation 429s. Vercel Pro starts at 150 vCPU/min and ramps; `run_vercel.sh` waits 10 minutes before the bursts so the starting rate can reset.

Create, delete, and cleanup events are appended to `results/sandboxes.jsonl` at the experiment root (same tracker as the other providers).

## Persistence and snapshots

`stop()` snapshots the filesystem and drops memory and processes. Grid and burst jobs `destroy()` a still-running sandbox, so they should not leave a snapshot. Stop/resume and snapshot-restore tests do leave snapshots until cleanup deletes them. Leftover snapshots still cost storage; always run cleanup.

## 24-hour soak

Not orchestrated by `run_vercel.sh`. A parked Vercel sandbox is snapshot storage only, so a soak would be cheap, but it is not part of this scripted Vercel addition.

## Cost model

List prices (Pro, iad1), used by `providers.vc_cost` and `spend_vercel.py`:

- Active CPU: $0.128 per vCPU-hour, only while the vCPU is busy
- Provisioned memory: $0.0212 per GB-hour, 1 minute minimum
- Creations: $0.60 per million
- Snapshot storage: $0.08 per GB-month

Modeled spend is not billed spend. Confirm the bill on the Vercel Usage page.
