"""M10 long-running soak: one instance per provider for HOURS, put to sleep (Agent37 sleep / Daytona stop) and woken every EVERY_MIN minutes with one command.
Records wake latency, failures, file persistence. Usage: soak.py <provider> <hours> <every_min> <outdir> [manual|auto]"""
import sys,os,json,time,traceback
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,H); import providers as P
prov,hours,every,outdir=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]; os.makedirs(outdir,exist_ok=True)
mode=sys.argv[5] if len(sys.argv)>5 else 'manual'   # InstaBox only: 'manual' = explicit suspend/resume each cycle (mirrors the others); 'auto' = no explicit sleep, idle pause after 5 min, exec wakes it
pv=P.provider(prov); R=dict(provider=prov,mode=mode,checks=[],start=time.time()); path=f'{outdir}/soak__{prov}'+('' if mode=='manual' else '-'+mode)+'.json'; b=None
try:
    b,cs=pv.create('medium','default','soak-keep'+('' if mode=='manual' else '-'+mode),**({'auto_suspend':300} if mode=='auto' else {})); R.update(id=b.id,create_s=round(cs,2),auto_suspend_s=300 if mode=='auto' else (1800 if prov=='instabox' else None)); pv.exec(b,f'echo persisted > {b.home}/marker')
    end=time.time()+hours*3600
    while time.time()<end:
        try:
            if mode!='auto': pv.sleep(b)
        except Exception as e: R['checks'].append({'t':time.time(),'sleep_err':str(e)[:200]})
        time.sleep(every*60); t=time.time()
        try:
            if prov in ('daytona','instabox') and mode!='auto': pv.wake(b)
            sb=None
            if prov=='instabox' and mode=='auto':
                try: sb=pv.get(f'/v1/machines/{b.id}').get('state')   # reading never wakes it
                except Exception as e: sb='err'
            rs=getattr(b,'last_wake_s',None); rc,out=pv.exec(b,f'cat {b.home}/marker'); R['checks'].append({'t':t,'wake_s':round(time.time()-t,2),'ok':'persisted' in out,**({'resume_call_s':rs} if rs is not None else {}),**({'state_before':sb} if sb else {})})
        except Exception as e: R['checks'].append({'t':t,'err':str(e)[:200]})
        json.dump(R,open(path,'w'))
except Exception: R['error']=traceback.format_exc()[-1500:]
finally:
    if b: R['deleted']=pv.delete(b,'soak')
    if prov=='instabox': R['retries']=dict(pv.retries)
    R['life_s']=round(time.time()-R['start'],2); json.dump(R,open(path,'w'))
