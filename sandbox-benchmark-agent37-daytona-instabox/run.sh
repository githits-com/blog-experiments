#!/usr/bin/env bash
# Full run, everything in parallel. Needs AGENT37_API_KEY and DAYTONA_API_KEY in the environment (never printed).
# Stages: pilot (1 sandbox per cell) -> grid + sleep/wake (parallel) -> bursts (alone, so they get every Agent37 slot) -> cleanup -> tables.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python3}
mkdir -p logs
export SPEND_CAP_A37=${SPEND_CAP_A37:-5} SPEND_CAP_DT=${SPEND_CAP_DT:-10}
$PY harness/make_jobs.py
$PY harness/bench.py results/jobs_pilot.json results/runs_pilot --a37-workers 6 --dt-workers 2 | tee logs/pilot.log
$PY harness/bench.py results/jobs_full.json results/runs_full --a37-workers ${A37_W:-40} --dt-workers ${DT_W:-50} >logs/full.log 2>&1 &
for p in agent37 daytona; do for r in 0 1 2; do $PY harness/sleepwake.py $p medium 5 120 results/sleepwake $r >logs/sleepwake_${p}_$r.log 2>&1 & done done
wait
# optional 24 h soak (M10): SOAK=1 starts it in the background; it reports the next day
if [ "${SOAK:-0}" = 1 ]; then for p in agent37 daytona; do nohup $PY harness/soak.py $p 24 30 results/soak >logs/soak_$p.log 2>&1 & done fi
for w in a b; do for n in 10 25 ${BURST_MAX:-45}; do
  $PY harness/burst.py agent37 $n $w results/burst &
  $PY harness/burst.py daytona $n $w results/burst &
  wait
done; done | tee logs/burst.log
$PY harness/cleanup.py agent37 daytona | tee logs/cleanup.log
$PY analysis/analyze.py >/dev/null && echo "tables: out/tables.md"
echo "run analysis/billing.py once more after the next hourly settlement for billed vs modeled"
