# Agent37, Daytona, and InstaBox: an infrastructure benchmark for agent sandboxes

The question: for short, bursty agent sandboxes and for long-running agents, what do you actually get from Agent37 (gVisor containers on shared hosts, $0.80/vCPU-month), Daytona ($0.0504/vCPU-hour), and InstaBox (Firecracker microVMs, $0.004/vCPU-hour)? We measure only things a sandbox user feels: how fast a sandbox is usable, how fast it clones big repositories, what happens at the memory and disk limits, whether CPU holds up under load, whether a burst of creates succeeds, what you are billed, and whether a long-running agent survives sleep.

This is an infrastructure benchmark. No LLM is called: an agent loop adds model latency and variance that would hide the provider differences, and the earlier sandbox experiments already measured agent outcomes.

## Arms (cells)

| Provider | Type | Shapes (vCPU / GiB RAM / GiB disk) | Notes |
|---|---|---|---|
| Daytona | default (`daytona-medium`, `daytona-large`) | 2/4/8, 4/8/10 | per-second billing, first 5 GiB disk free |
| Agent37 | `default` (`agent37-base`) | 2/4/8, 4/8/10 | gVisor container on shared hosts |
| Agent37 | `vm` (`agent37-ubuntu`) | 2/4/8, 4/8/10 | own kernel, compute 2.5x the default rate |
| Agent37 | `performance` (`agent37-base`) | 2/4/8, 4/8/10 | cores held for the instance, compute 4x |
| InstaBox | `agent-browser` (override with `INSTABOX_TEMPLATE`) | 2/4 and 4/8, disk fixed at 20 GiB | Pro workspace. See amendment A1 |

Shapes are matched on CPU and RAM: Agent37 2/4 against Daytona Medium and InstaBox Medium, Agent37 4/8 against Daytona Large and InstaBox Large. Agent37 and Daytona use the same disk; InstaBox disk is the fixed 20 GiB `/data`. Agent37's smallest shape is 2 vCPU / 4 GB, so there is no counterpart to the 1 vCPU / 1 GiB Daytona Small used in earlier experiments; Small is left out. Region: Agent37 `us` (the only region with the default type); Daytona's default region.

## Measurements

Every job is one fresh sandbox: create, probes, delete. The same job spec runs on each provider through `harness/providers.py`, a small provider interface (create, exec, upload, delete, sleep, wake). In-sandbox measurement is `harness/probe.py`, Python standard library only.

| # | Metric | How |
|---|---|---|
| M1 | Create → API returns | wall time of the create call (both APIs return when the sandbox is running) |
| M2 | Time to first command | first `true` after create; plus 10 more round trips for exec latency |
| M3 | CPU under sustained load | one sha256 loop per vCPU for 180 s; work per 5 s window. Throttling shows as later windows falling below the first; compared across types |
| M4 | git clone throughput | full and shallow (`--depth 1`) clones of vercel/next.js, pytorch/pytorch, kubernetes/kubernetes; wall time, bytes received (/proc/net/dev), Mbit/s, disk used |
| M5 | Memory limit behaviour | allocate and touch 128 MB steps up to 2x the shape's RAM; record where it stops, how (MemoryError, process killed, exec error, sandbox restarted) and whether the sandbox still answers 5 s later |
| M6 | Disk limits | write 256 MB files until ENOSPC, up to 2x the disk, on the home volume, then up to 12 GB on the OS layer (`/var/tmp`): GB written and MB/s. Agent37 bills the home volume and has a separate 10 GB OS layer |
| M7 | Burst creation | N creates fired at the same instant (N = 10, 25, 45; two waves each), Medium, default type: successes, every API error code, create latency median and p95 |
| M8 | Billed vs modeled | Agent37: per-instance compute from `GET /v1/usage` against lifetime x published rate, exact and rounded up to whole minutes. Daytona: billed total from the dashboard against the same model |
| M9 | Sleep/wake and persistence | one instance per run writes a file and starts a background process, then 5 cycles of sleep → 120 s idle → first command. Wake latency, file kept, process kept. Agent37 uses its checkpointed sleep; Daytona has no checkpointed sleep, so stop/start |
| M10 | Long-running soak (optional, runs beside the grid) | one auto-sleep instance per provider for 24 h, woken every 30 min with one command: wake latency distribution, failures, cost |

Out of scope: GPU, Docker-in-Docker (only the Agent37 `vm` type can run it), regions outside the US.

## Task list and runs per cell

| Job kind | Runs per cell | Cells | Sandboxes |
|---|---|---|---|
| lifecycle + CPU (M1–M3) | 10 | 8 | 80 |
| clone (M4): 3 repos x full/shallow | 5 each = 30 | 8 | 240 |
| memory (M5) | 5 | 8 | 40 |
| disk (M6) | 3 | 8 | 24 |
| **grid total** | 48 | 8 | **384** (288 Agent37, 96 Daytona) |
| burst (M7) | 2 waves x (10+25+45) | 2 providers | 320 (160 each) |
| sleep/wake (M9) | 3 instances x 5 cycles | 2 providers | 6 |

Statistics: medians with bootstrap 95% CIs over sandboxes (2,000 resamples, seed 0). Every failed create and every failed probe is kept as a result file and counted.

## Concurrency

- Agent37: the account is tier 2, so 50 instances (counting every instance not yet deleted). Grid at 40 workers, leaving room for the sleep/wake instances. Bursts run alone afterwards at up to 45.
- Daytona: 50 workers. The peak is 50 x 4 vCPU = 200 vCPU, inside the 250-vCPU org cap.
- InstaBox: Pro plan, 50 workers on a 96-sandbox grid. Pro allows 30 starts a minute across create, start, resume, and wake. A faster burst is a retryable `429 rate_limited`; the harness waits for `Retry-After` and counts it. See amendment A1.

## Cost estimate and cap

The model is sandbox lifetime x published rate. Agent37 bills whole minutes. Estimated sandbox-minutes per grid cell: lifecycle 10 x 4 + full clones 15 x 4 + shallow clones 15 x 1 + memory 5 x 2 + disk 3 x 5 = 140 minutes (2.33 h).

| Item | Agent37 | Daytona |
|---|---|---|
| $/h, Medium / Large | default 0.0070 / 0.0133; vm 0.0161 / 0.0314; performance 0.0251 / 0.0495 | 0.1659 / 0.3317 |
| grid (2.33 h per cell) | 0.142 $/h summed over 6 cells x 2.33 h = $0.33 | 0.497 $/h x 2.33 h = $1.16 |
| bursts (160 sandboxes, about 1–1.5 min each) | $0.02 | about $0.70 |
| sleep/wake + 24 h soak | about $0.20 | about $0.25 |
| **estimate** | **about $0.55** | **about $2.10** |
| **hard cap** | **$5** (`SPEND_CAP_A37`) | **$10** (`SPEND_CAP_DT`) |

InstaBox is priced separately: vCPU $0.004/h + GiB $0.00225/h + the fixed 20 GiB `/data` at $0.00011/GiB-h (an upper bound; Pro includes 200 GiB across machines). Runtime is billed only while the machine is `running`. Its hard cap is **$10** (`SPEND_CAP_IB`). `analysis/billing_instabox.py` reads `GET /v1/usage`.

LLM: $0. The runner stops starting new jobs on a provider when its modeled spend reaches that provider's cap. Agent37 and Daytona together are capped at $15. InstaBox has its own $10 cap and does not draw on theirs.

## Wall-clock ETA (heavy parallelism)

- Pilot, one sandbox per cell: about 5 min.
- Grid: Agent37 has 288 sandboxes and about 840 sandbox-minutes over 40 workers, so about 21 min of work plus a tail for the longest jobs (about 5 min). Daytona runs at the same time (about 280 sandbox-minutes over 50 workers, about 10 min). Sleep/wake runs alongside. **About 25–30 min.**
- Bursts: 6 waves per provider, the two providers in parallel. **About 10 min.**
- Cleanup and tables: about 5 min.
- **Total: about 45 min from go to tables.** Billed-vs-modeled is re-read after Agent37's hourly settlement, about 1 h after the last job. The 24 h soak reports the next day and blocks nothing.

## Reproduce

```
./run.sh                      # Agent37 and Daytona: pilot, grid, sleep/wake, bursts, cleanup, tables
python3 analysis/billing.py   # >1 h later: Agent37 billed vs modeled
```

InstaBox is a separate run. Commands are in the folder `README.md` (`INSTABOX_API_KEY`, `harness/make_jobs_instabox.py`, `harness/run_instabox_bursts.sh`, `harness/run_instabox_followups.sh`, and the two soak variants).

A run writes local output only (gitignored; not in this repository): `results/`, `logs/`, and `out/`. Published numbers are in the blog post: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/

## Fairness notes

- Same probe code and the same job order on each provider; jobs are interleaved across cells so time-of-day effects spread evenly.
- Base images differ (Agent37 `agent37-base` is Debian 12 with git 2.39; Daytona's default image has its own git; InstaBox `agent-browser` is Debian 13, Firecracker, git 2.47). Clone times include that difference.
- Agent37's default type shares and overcommits host CPU and memory by design. M3 and M5 measure what that means in practice; the `performance` and `vm` types are the like-for-like comparison with dedicated resources.
- Published list prices only, before credits and plan fees.
- InstaBox was added after the Agent37/Daytona grid. It uses the same probes and job kinds. Details: amendment A1.

## Amendment A1: InstaBox

Same probes, repos, modes, and reps per cell as `harness/make_jobs.py`. Two cells: Medium (2 vCPU / 4 GiB) and Large (4 vCPU / 8 GiB), 48 jobs per cell, 96 sandboxes, 50 workers. Bursts at 10, 25, and 45. Sleep/wake is 3 instances × 5 cycles. The 24 h soak has two variants.

- **Plan.** Pro. The free tier is not part of this benchmark. Pro is what allows the 2/4 and 4/8 shapes. It also limits starts to 30 a minute across create, start, resume, and wake. That limit is reported, not worked around: retries honour `Retry-After`, and `create_s` excludes the wait. Bursts record errors unless `burst.py` is passed `retry`.
- **Template.** `agent-browser`, InstaBox's default (a pre-booted pool). Override with `INSTABOX_TEMPLATE` (the follow-up script checks `universal`, which has no pre-booted pool). Exec runs as the unprivileged user `user`. Home is `/data/home`.
- **Disk.** Fixed 20 GiB `/data`, not settable at create. The disk probe writes until ENOSPC on that volume, then up to 12 GB on `/var/tmp`.
- **Idle pause.** Grid, sleep/wake, and the manual soak leave the default 1800 s idle pause in place and suspend or delete explicitly, so that timer is not what ends the sandbox. The soak's `auto` variant sets idle pause to 300 s and does not call suspend; a plain exec every 30 minutes has to wake the machine. The harness records the machine state just before that wake.
- **API.** REST at `https://api.instabox.sh`. `INSTABOX_API_KEY` is sent as `X-API-Key` and is never printed or written. Create, delete, suspend, and resume return an operation that is followed with `GET /v1/operations/{id}?wait=25s`. Lifecycle calls send `Idempotency-Key`. Deletes send `X-Confirm-Delete`. Exec is `POST /v1/machines/{id}/exec`. Upload is `PUT /v1/machines/{id}/files`.
- **Sleep.** `POST /v1/machines/{id}/suspend` keeps memory and processes. `POST /v1/machines/{id}/resume` wakes a manual pause; exec alone does not.
