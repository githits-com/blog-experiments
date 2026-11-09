"""Provider abstraction: the same job spec runs on Daytona and Agent37.
Keys come from the environment (DAYTONA_API_KEY, AGENT37_API_KEY) and are never printed or written.
Every create/delete is appended to ../results/sandboxes.jsonl (provider, id, tag, event, time) so spend can be audited."""
import os,json,time,threading,fcntl,base64
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(H); TRACK=f'{ROOT}/results/sandboxes.jsonl'; _L=threading.Lock()
LABEL='sandbox-a37-vs-dt'
def track(rec):
    rec=dict(rec,t=time.time()); os.makedirs(os.path.dirname(TRACK),exist_ok=True)
    with _L, open(TRACK,'a') as f: fcntl.flock(f,fcntl.LOCK_EX); f.write(json.dumps(rec)+'\n')

# Shapes. Agent37 has no 1 vCPU / 1 GiB shape, so our earlier "Small" has no counterpart.
SHAPES={'medium':(2,4,8),'large':(4,8,10)}            # vCPU, GiB RAM, GiB disk (same on both providers)
A37_TYPES={'default':1.0,'vm':2.5,'performance':4.0}  # compute-rate multiplier; disk unchanged
def rate_per_s(provider,shape,typ='default'):
    c,m,d=SHAPES[shape]
    if provider=='daytona': return (c*0.0504+m*0.0162+max(0,d-5)*0.000108)/3600
    return ((c*0.80+m*0.70)*A37_TYPES[typ]+d*0.09)/730/3600

class Box:
    def __init__(s,provider,id,home,raw=None,shape=None,typ=None): s.provider,s.id,s.home,s.raw,s.shape,s.typ=provider,id,home,raw,shape,typ

class ProviderError(Exception):
    def __init__(s,code,msg,http=None): super().__init__(f'{http} {code}: {msg}'); s.code,s.http=code,http

class Daytona:
    name='daytona'
    def __init__(s):
        from daytona import Daytona as D; s.c=D()
    def create(s,shape,typ='default',tag='',image=None):
        from daytona import CreateSandboxFromSnapshotParams as P
        t=time.time()
        sb=s.c.create(P(snapshot=image or f'daytona-{shape}',labels={'exp':LABEL,'tag':tag[:60]},auto_stop_interval=0 if 'keep' in tag else 30,auto_delete_interval=-1 if 'keep' in tag else 0,ttl_minutes=None if 'keep' in tag else 90),timeout=900)
        b=Box('daytona',sb.id,'/home/daytona',sb,shape,typ); track({'provider':'daytona','id':sb.id,'tag':tag,'event':'created','shape':shape,'type':typ}); return b,time.time()-t
    def exec(s,b,cmd,timeout=900,root=False):
        if root: cmd=f"sudo -n sh -c {json.dumps(cmd)}"
        r=b.raw.process.exec(cmd,timeout=timeout); return r.exit_code,(r.result or '')
    def upload(s,b,data,path): b.raw.fs.upload_file(data,path)
    def delete(s,b,tag=''):
        for i in range(4):
            try: s.c.delete(b.raw); track({'provider':'daytona','id':b.id,'tag':tag,'event':'deleted'}); return True
            except Exception as e: err=e; time.sleep(3)
        track({'provider':'daytona','id':b.id,'tag':tag,'event':'delete_failed','err':str(err)[:200]}); return False
    def sleep(s,b): b.raw.stop()          # Daytona has no checkpointed sleep: stop keeps the disk, drops memory
    def wake(s,b): b.raw.start(timeout=900)
    def list_ours(s,keep=True):
        from daytona import ListSandboxesQuery as Q
        return [x.id for x in s.c.list(Q(labels={'exp':LABEL})) if keep or 'soak' not in ((x.labels or {}).get('tag',''))]
    def delete_id(s,i): s.c.delete(s.c.get(i)); track({'provider':'daytona','id':i,'event':'deleted_by_cleanup'})

class Agent37:
    name='agent37'; API='https://api.agent37.com/v1'; SBX='https://sandbox.agent37.app/v1'
    def __init__(s):
        import requests; s.r=requests.Session(); s.k=os.environ['AGENT37_API_KEY']
    def _api(s,method,path,body=None,timeout=900,params=None):
        resp=s.r.request(method,s.API+path,headers={'Authorization':'Bearer '+s.k},json=body,timeout=timeout,params=params)
        if resp.status_code>=400:
            try: e=resp.json().get('error'); code,msg=(e.get('code'),e.get('message')) if isinstance(e,dict) else (e,'')
            except Exception: code,msg='http',resp.text[:200]
            raise ProviderError(code,(msg or '')[:300],resp.status_code)
        return resp.json() if resp.content else {}
    def get(s,path,**kw): return s._api('GET',path,**kw)
    def create(s,shape,typ='default',tag='',image=None):
        c,m,d=SHAPES[shape]; t=time.time()
        body={'template':image or ('agent37-ubuntu' if typ=='vm' else 'agent37-base'),'resources':{'cpu':c,'memory':m,'disk':d},'type':typ,'region':'us',
              'name':tag[:60] or LABEL,'metadata':{'exp':LABEL,'tag':tag[:60]},'network':'allow-all'}
        j=s._api('POST','/instances',body,timeout=900)
        b=Box('agent37',j['id'],'/home/node',j,shape,typ)
        track({'provider':'agent37','id':j['id'],'tag':tag,'event':'created','shape':shape,'type':typ,'status':j.get('status'),'resources':j.get('resources')}); return b,time.time()-t
    def exec(s,b,cmd,timeout=840,root=True):
        resp=s.r.post(f'{s.SBX}/instances/{b.id}/exec',headers={'X-Agent37-Key':s.k},json={'command':cmd,**({'user':'root'} if root else {})},timeout=min(timeout,900)+30)
        if resp.status_code>=400:
            try: e=resp.json().get('error'); code=e.get('code') if isinstance(e,dict) else e
            except Exception: code='http'
            raise ProviderError(code,resp.text[:200],resp.status_code)
        j=resp.json(); return j['exit_code'],(j.get('stdout') or '')+(j.get('stderr') or '')
    def upload(s,b,data,path):
        b64=base64.b64encode(data).decode(); CH=48000
        s.exec(b,f'mkdir -p $(dirname {path}) && : > {path}.b64')
        for i in range(0,len(b64),CH): s.exec(b,f"printf %s '{b64[i:i+CH]}' >> {path}.b64")
        rc,out=s.exec(b,f'base64 -d {path}.b64 > {path} && rm {path}.b64'); assert rc==0,out
    def delete(s,b,tag=''):
        for i in range(4):
            try: s._api('DELETE',f'/instances/{b.id}'); track({'provider':'agent37','id':b.id,'tag':tag,'event':'deleted'}); return True
            except ProviderError as e:
                if e.http==404: track({'provider':'agent37','id':b.id,'tag':tag,'event':'deleted','note':'404'}); return True
                err=e; time.sleep(3)
            except Exception as e: err=e; time.sleep(3)
        track({'provider':'agent37','id':b.id,'tag':tag,'event':'delete_failed','err':str(err)[:200]}); return False
    def sleep(s,b): s._api('POST',f'/instances/{b.id}/sleep')
    def wake(s,b): s.exec(b,'true')        # exec wakes a sleeping instance; we time it
    def metrics(s,b,hours=1): return s.get(f'/instances/{b.id}/metrics',params={'hours':hours})
    def list_ours(s,keep=True): return [x['id'] for x in s.get('/instances').get('data',[]) if (x.get('metadata') or {}).get('exp')==LABEL and (keep or 'soak' not in (x.get('metadata') or {}).get('tag',''))]
    def delete_id(s,i): s._api('DELETE',f'/instances/{i}'); track({'provider':'agent37','id':i,'event':'deleted_by_cleanup'})

def provider(name): return {'daytona':Daytona,'agent37':Agent37}[name]()
