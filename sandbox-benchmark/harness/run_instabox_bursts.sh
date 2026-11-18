#!/usr/bin/env bash
# InstaBox bursts, same N and waves as the others (10, 25, 45 at once, two waves each, no retry: errors are recorded), then one extra wave of 45 that honours Retry-After.
cd "$(dirname "$0")/.." || exit
PY=${PY:-python3}
for w in a b; do for n in 10 25 45; do
  $PY harness/burst.py instabox $n $w results/burst
  sleep 20
done; done
$PY harness/burst.py instabox 45 r results/burst retry
