#!/usr/bin/env bash
# Follow-ups after the InstaBox grid. Fifty workers can exceed Pro's 30 starts a minute, so some create_s values include Retry-After waits:
# 1) lifecycle jobs re-run at 20 workers (inside the start limit) with the wait excluded from create_s; 2) clean burst waves c/d with 75 s between waves
# (waves a/b had 20 s gaps and the rolling 30-per-minute window carried over); 3) template check: 5 Large lifecycle runs on `universal` (no pre-booted pool) vs the default `agent-browser`.
cd "$(dirname "$0")/.."; PY=${PY:-python3}; export SPEND_CAP_IB=${SPEND_CAP_IB:-10}
$PY harness/make_jobs_instabox.py
mkdir -p results/runs_instabox_lifecycle_rerun results/runs_instabox_universal logs
$PY harness/bench.py results/jobs_instabox_lifecycle_rerun.json results/runs_instabox_lifecycle_rerun --ib-workers 20 > logs/instabox_lifecycle_rerun.log 2>&1
sleep 75
for w in c d; do for n in 10 25 45; do $PY harness/burst.py instabox $n $w results/burst; sleep 75; done; done > logs/instabox_burst_clean.log 2>&1
INSTABOX_TEMPLATE=universal $PY harness/bench.py results/jobs_instabox_universal.json results/runs_instabox_universal --ib-workers 5 > logs/instabox_universal.log 2>&1
echo FOLLOWUPS_DONE >> logs/instabox_events.log
