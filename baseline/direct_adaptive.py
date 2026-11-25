"""Train block choice on first128; freeze before independent query validation."""
import csv,datetime,json,os,random,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'results'/('direct_adaptive_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(parents=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
env=os.environ.copy();env['PYTHONPATH']=str(root/'.deps');env['OPENBLAS_CORETYPE']='Haswell'
rows=[];runs=[]
def run(label,q,methods,indices=None):
    print(label,flush=True)
    cmd=[sys.executable,str(root/'compare.py'),'--dataset','sift1m','--queries',str(q),'--repeats','5','--methods',methods]
    if indices is not None:
        p=out/(label+'_indices.json');p.write_text(json.dumps(indices));cmd+=['--query-indices',str(p)]
    p=subprocess.run(cmd,env=env,text=True,capture_output=True)
    (out/(label+'.log')).write_text(p.stdout+p.stderr);p.check_returncode()
    folder=Path(p.stdout.strip().split('Results: ')[-1]);runs.append({'label':label,'folder':folder.relative_to(root).as_posix()})
    rr=list(csv.DictReader((folder/'summary.csv').open()));rows.extend({'label':label,**r} for r in rr)
    with (out/'partial.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/'runs.json').write_text(json.dumps(runs,indent=2))
    return rr
for q in [1,2,4,8]:run(f'train_q{q}',q,'direct_packed_m1,direct_packed_m3,direct_packed_m4,direct_packed_m5,direct_packed_m6,faiss_direct,faiss_blas')
rr=run('train_q128',128,'direct_packed_m6,direct_packed_b64,direct_packed_b128,direct_packed_b512,direct_packed_b1024,faiss_blas')
best=min((r for r in rr if r['method'].startswith('direct_')),key=lambda r:float(r['median_ms']))['method']
(out/'selection.json').write_text(json.dumps({'small_batch':'m6 fixed shape-based rule, not tuned by observed output','q128_method':best,'training_queries':'first128','heldout_excludes':'indices0..127'},indent=2))
rng=random.Random(20261122);indices=rng.sample(range(128,10000),128)
for q in [1,2,4,8,32,128]:
    methods=list(dict.fromkeys(['stream_all','direct_packed_m1','direct_packed_m6',best if q==128 else 'direct_packed_m6','faiss_flat','faiss_direct','faiss_blas']))
    run(f'heldout_q{q}',q,','.join(methods),indices[:q])
for i in [1,2]:run(f'heldout_q1_repeat{i}',1,'direct_packed_m1,direct_packed_m6,faiss_flat,faiss_direct,faiss_blas',rng.sample(range(128,10000),1))
(out/'summary.csv').write_bytes((out/'partial.csv').read_bytes())
print(out)
