"""M10 long-running soak: one instance per provider for HOURS, put to sleep (Agent37 sleep / Daytona stop) and woken every EVERY_MIN minutes with one command.
Records wake latency, failures, file persistence. Usage: soak.py <provider> <hours> <every_min> <outdir>"""
import sys,os,json,time,traceback
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,H); import providers as P
prov,hours,every,outdir=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]; os.makedirs(outdir,exist_ok=True)
pv=P.provider(prov); R=dict(provider=prov,checks=[],start=time.time()); path=f'{outdir}/soak__{prov}.json'; b=None
try:
    b,cs=pv.create('medium','default','soak-keep'); R.update(id=b.id,create_s=round(cs,2)); pv.exec(b,f'echo persisted > {b.home}/marker')
    end=time.time()+hours*3600
    while time.time()<end:
        try: pv.sleep(b)
        except Exception as e: R['checks'].append({'t':time.time(),'sleep_err':str(e)[:200]})
        time.sleep(every*60); t=time.time()
        try:
            if prov=='daytona': pv.wake(b)
            rc,out=pv.exec(b,f'cat {b.home}/marker'); R['checks'].append({'t':t,'wake_s':round(time.time()-t,2),'ok':'persisted' in out})
        except Exception as e: R['checks'].append({'t':t,'err':str(e)[:200]})
        json.dump(R,open(path,'w'))
except Exception: R['error']=traceback.format_exc()[-1500:]
finally:
    if b: R['deleted']=pv.delete(b,'soak')
    R['life_s']=round(time.time()-R['start'],2); json.dump(R,open(path,'w'))
