"""InstaBox billed vs modeled. Reads GET /v1/usage (cost for the month so far, rated hourly, so it lags up to an hour) and the sandboxes the harness created
(results/sandboxes.jsonl). Pro includes monthly credits and 200 GiB of disk across machines, so billed cost shows up as credit use.
Writes out/billing_instabox.md and out/billing_instabox.json. Needs INSTABOX_API_KEY (never printed)."""
import os,json,sys,time,collections
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path=f'{ROOT}/results/sandboxes.jsonl'
if not os.path.isfile(path):
    sys.exit('No results/sandboxes.jsonl. This repository stores code only; run output is not committed.\n'
             'Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n'
             'Reproduce with the InstaBox commands in README.md, then re-run this script.')
import requests
u=requests.get('https://api.instabox.sh/v1/usage',headers={'X-API-Key':os.environ['INSTABOX_API_KEY']},timeout=30).json()
c=u['cost']; ev=[json.loads(l) for l in open(path) if '"instabox"' in l]
life=collections.defaultdict(dict)
for e in ev: life[e['id']][e['event']]=e['t']
import sys; sys.path.insert(0,f'{ROOT}/harness'); import providers as P
mod=0.0; hrs=0.0; n=0
for i,d in life.items():
    if 'created' in d and 'deleted' in d: n+=1; hrs+=(d['deleted']-d['created'])/3600
out=dict(read_at=time.time(),cost=c,limits=u.get('limits'),machines_now=u.get('machines'),sandboxes_created_and_deleted=n,wall_sandbox_hours_created_to_deleted=round(hrs,3))
os.makedirs(f'{ROOT}/out',exist_ok=True); json.dump(out,open(f'{ROOT}/out/billing_instabox.json','w'),indent=1)
T=['# InstaBox: billed (GET /v1/usage) vs sandbox lifetime\n',f"Read {time.strftime('%Y-%m-%d %H:%M %Z')}; the ledger is rated hourly, so figures lag by up to an hour (`ratedUntil` {c.get('ratedUntil')}).\n",
 '| field | value |\n|---|---|']+[f'| {k} | {c.get(k)} |' for k in ('vcpuHours','memGiBHours','storageGiBHours','egressGiB','vcpuUSD','memUSD','storageUSD','egressUSD','costUSD','allowanceUSD','creditRemainingUSD','overageUSD','creditsUSD','creditsUsedUSD','billableDiskGiB','includedDiskGiB')]
T.append(f"\nSandboxes created and deleted by the harness (all, including pilot/smoke/soak): {n}; created-to-deleted wall time {round(hrs,2)} h. Note `vcpuHours` counts only the time a machine is `running` (not paused, not starting).")
open(f'{ROOT}/out/billing_instabox.md','w').write('\n'.join(T)+'\n'); print('\n'.join(T))
