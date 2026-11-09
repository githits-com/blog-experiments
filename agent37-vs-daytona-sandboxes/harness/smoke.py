"""Smoke check: one create -> first command -> probe upload -> sysinfo + 10 s CPU -> delete, on one provider. Writes ../results/smoke/<provider>.json"""
import sys,os,json,time,traceback
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,H); import providers as P, bench
prov=sys.argv[1]; shape=sys.argv[2] if len(sys.argv)>2 else 'medium'; typ=sys.argv[3] if len(sys.argv)>3 else 'default'
out=f'{P.ROOT}/results/smoke'; os.makedirs(out,exist_ok=True); pv=P.provider(prov); R={'provider':prov,'shape':shape,'type':typ}; b=None; t0=time.time()
try:
    b,cs=pv.create(shape,typ,'smoke'); R.update(id=b.id,create_s=round(cs,2),create_resp={k:b.raw.get(k) for k in ('status','resources','type','region','template')} if isinstance(b.raw,dict) else None)
    t=time.time(); pv.exec(b,'true'); R['first_cmd_s']=round(time.time()-t,3)
    rtt=[]
    for _ in range(5): t=time.time(); pv.exec(b,'true'); rtt.append(round(time.time()-t,3))
    R['exec_rtt_s']=rtt; t=time.time(); pv.upload(b,bench.PROBE,f'{b.home}/probe.py'); R['upload_s']=round(time.time()-t,2)
    R['sysinfo']=bench.run_probe(pv,b,'sysinfo'); R['cpu10']=bench.run_probe(pv,b,f'cpu 10 {P.SHAPES[shape][0]}')
    rc,o=pv.exec(b,'id; df -h / /home/node /tmp 2>/dev/null; cat /etc/os-release | head -2'); R['env']=o[-1500:]
except Exception: R['error']=traceback.format_exc()[-1500:]
finally:
    if b: t=time.time(); R['deleted']=pv.delete(b,'smoke'); R['delete_s']=round(time.time()-t,2)
    R['life_s']=round(time.time()-t0,2); json.dump(R,open(f'{out}/{prov}__{typ}__{shape}.json','w'),indent=1)
print(json.dumps({k:v for k,v in R.items() if k not in ('env',)},indent=1)[:3000]); print(R.get('env',''))
