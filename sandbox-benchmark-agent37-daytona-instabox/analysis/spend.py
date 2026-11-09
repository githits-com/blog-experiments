"""Spend from results/sandboxes.jsonl: every create -> delete interval x published rate (Agent37 also rounded up to whole minutes per sandbox).
Sandboxes still alive (the 24 h soak) are charged up to now. Writes out/spend.json."""
import json,os,sys,time,math,collections
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0,f'{ROOT}/harness'); import providers as P
path=f'{ROOT}/results/sandboxes.jsonl'
if not os.path.isfile(path):
    sys.exit('No results/sandboxes.jsonl. This repository stores code only; run output is not committed.\n'
             'Published numbers: https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/\n'
             'Reproduce with ./run.sh, or the InstaBox commands in README.md, then re-run this script.')
ev={}
for l in open(path):
    r=json.loads(l); ev.setdefault((r['provider'],r['id']),{})[r['event']]=r
out=collections.defaultdict(lambda:dict(sandboxes=0,hours=0.0,usd=0.0,usd_whole_minutes=0.0,alive=0,delete_failed=0))
for (p,i),e in ev.items():
    c=e.get('created')
    if not c: continue
    d=e.get('deleted') or e.get('deleted_by_cleanup'); end=d['t'] if d else time.time(); s=end-c['t']; rt=P.rate_per_s(p,c.get('shape') or 'medium',c.get('type') or 'default')
    o=out[p]; o['sandboxes']+=1; o['hours']+=s/3600; o['usd']+=s*rt; o['usd_whole_minutes']+=math.ceil(s/60)*60*rt; o['alive']+=0 if d else 1; o['delete_failed']+=1 if 'delete_failed' in e and not d else 0
res={p:{k:round(v,4) for k,v in o.items()} for p,o in out.items()}
os.makedirs(f'{ROOT}/out',exist_ok=True); json.dump(res,open(f'{ROOT}/out/spend.json','w'),indent=1); print(res)
