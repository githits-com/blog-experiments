#!/usr/bin/env bash
# Vercel Sandbox run. Needs VERCEL_TOKEN, VERCEL_TEAM_ID, and VERCEL_PROJECT_ID
# in the environment (never printed). THIS COSTS REAL MONEY. The runner stops
# starting new grid jobs at SPEND_CAP_VC (default $15, modeled); bursts and
# persistence tests are not auto-capped. Confirm billed spend on the Vercel
# Usage page. Stages: grid + sleep/wake + snapshot-restore + timeout-resume
# (parallel) -> 10 min idle (vCPU allocation rate resets) -> bursts -> cleanup
# -> tables. Run a smoke and a pilot first (see vercel/VERCEL.md).
set -uo pipefail
cd "$(dirname "$0")/.." || exit
PY=${PY:-python3}
mkdir -p vercel/logs vercel/results
export SPEND_CAP_VC=${SPEND_CAP_VC:-15}
$PY harness/make_jobs_vercel.py
$PY harness/bench.py vercel/results/jobs_vercel.json vercel/results/runs_vercel --vc-workers "${VC_W:-50}" >vercel/logs/grid.log 2>&1 &
for r in 0 1 2; do
  VC_WAKE=resume $PY harness/sleepwake.py vercel medium 5 120 vercel/results/sleepwake $r >vercel/logs/sleepwake_resume_$r.log 2>&1 &
  VC_WAKE=auto $PY harness/sleepwake.py vercel medium 5 120 vercel/results/sleepwake a$r >vercel/logs/sleepwake_auto_$r.log 2>&1 &
  $PY harness/snapshot_resume_vercel.py medium 5 120 vercel/results/sleepwake $r >vercel/logs/snapshot_resume_$r.log 2>&1 &
  $PY harness/timeout_resume_vercel.py medium 5 60 vercel/results/sleepwake $r >vercel/logs/timeout_resume_$r.log 2>&1 &
done
wait
echo "grid and persistence tests done $(date)" | tee -a vercel/logs/events.log
sleep 600 # quota resets to the starting rate after 10 min without creates
for w in a b; do
  for n in 10 25 45; do
    $PY harness/burst.py vercel $n $w vercel/results/burst
    sleep 20
  done
done | tee vercel/logs/burst_ab.log
sleep 75
for w in c d; do
  for n in 10 25 45; do
    $PY harness/burst.py vercel $n $w vercel/results/burst
    sleep 75
  done
done | tee vercel/logs/burst_cd.log
$PY harness/burst.py vercel 100 e vercel/results/burst | tee vercel/logs/burst_100.log
sleep 75
$PY harness/burst.py vercel 100 r vercel/results/burst retry | tee -a vercel/logs/burst_100.log
$PY harness/cleanup.py vercel --all | tee vercel/logs/cleanup.log
$PY vercel/analysis/analyze_vercel.py >/dev/null && echo "tables: vercel/out/tables.md"
$PY vercel/analysis/spend_vercel.py >/dev/null && echo "spend: vercel/out/spend.md"
$PY vercel/analysis/charts_vercel.py && echo "charts: vercel/out/*.png"
echo "ALL DONE $(date)" | tee -a vercel/logs/events.log
