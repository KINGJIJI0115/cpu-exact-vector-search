"""One command calibrates the configured grid, freezes choices, then validates unseen queries."""
import argparse,csv,datetime,fcntl,hashlib,json,math,os,random,statistics,time
from pathlib import Path
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import numpy as np
from adaptive import ROOT,AdaptiveIndex,candidates,digest,host_facts,identity,read_profile,save_profile
from build_kernels import build
from oracle_cache import exact_oracles
def verify(index,q,k,result,oracle):
    ds,ids=result;od,oi=oracle
    assert ds.shape==ids.shape==(len(q),k) and np.all((ids>=0)&(ids<index.n))
    assert all(len(set(row))==k for row in ids)
    true=np.sum((index.x[ids].astype('float64')-q[:,None,:].astype('float64'))**2,axis=2)
    exact=index.database_kind=='byte' and np.all((q>=0)&(q<=255)&(q==np.floor(q)))
    if exact:
        np.testing.assert_array_equal(ids,oi);np.testing.assert_array_equal(ds,od)
    else:
        np.testing.assert_allclose(ds,true,rtol=1e-5,atol=1e-4);np.testing.assert_allclose(true,od,rtol=1e-5,atol=1e-6)
    return dict(correct=True,exact=bool(exact),max_distance_error=float(np.max(abs(ds-true))),id_recall=float(np.mean([len(set(a)&set(b))/k for a,b in zip(ids,oi)])))
def time_methods(index,q,k,methods,repeats,seed,oracle):
    checked={str(mode):verify(index,q,k,call(),oracle) for mode,call in methods.items()}
    raw=[];rng=random.Random(seed)
    for rep in range(repeats):
        order=list(methods);rng.shuffle(order)
        for mode in order:
            start=time.perf_counter_ns();result=methods[mode]();elapsed=(time.perf_counter_ns()-start)/1e6
            assert np.isfinite(result[0]).all()
            raw.append(dict(repeat=rep,method=mode,ms=elapsed))
    med={str(mode):statistics.median(x['ms'] for x in raw if x['method']==mode) for mode in methods}
    return dict(raw=raw,medians=med,validation=checked)
def load_vectors(path):
    a=np.fromfile(path,dtype='<i4');d=int(a[0]);a=a.reshape(-1,d+1);assert np.all(a[:,0]==d)
    return np.ascontiguousarray(a[:,1:].view('<f4'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--profile',type=Path,default=ROOT/'profiles/host.json');ap.add_argument('--cpu',type=int);ap.add_argument('--force',action='store_true');ap.add_argument('--quick',action='store_true',help='Two configurations only; not full calibration');ap.add_argument('--repeats',type=int,default=5);a=ap.parse_args()
    if a.repeats<3:ap.error('At least three repeats required')
    cpu=a.cpu if a.cpu is not None else min(os.sched_getaffinity(0))
    if cpu not in os.sched_getaffinity(0):ap.error('CPU outside allowed affinity')
    os.sched_setaffinity(0,{cpu});host_facts()
    lock=(ROOT/'calibration.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    start=time.perf_counter();build();facts=identity()
    configs=json.loads((ROOT/'goal_scope.json').read_text())['configs']
    if a.quick:configs=[['sift1m',1,100],['glove25',8,10]]
    # Exclude prior training, confirmation, and the previous single-query experiment.
    scope=json.loads((ROOT/'goal_scope.json').read_text());oldtrain=set(random.Random(scope['baseline_seed']).sample(range(128,10000),256))
    oldtest=set(random.Random(scope['confirmation_seed']).sample([i for i in range(128,10000) if i not in oldtrain],768))
    forbidden=oldtrain|oldtest|{4324,779,4529,5547,8423}
    ids=random.Random(2026122501).sample([i for i in range(128,10000) if i not in forbidden],1024)
    splits={'train':[ids[:256],ids[256:512]],'validation':[ids[512:768],ids[768:]]}
    assert not set(sum(splits['train'],[])) & set(sum(splits['validation'],[]))
    policy=dict(configs=configs,repeats=a.repeats,threshold=1.03,splits=splits,driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    cached,reason=read_profile(a.profile,facts)
    if a.force or cached and cached.get('policy_hash')!=digest(policy):cached=None
    profile=cached or dict(schema=1,identity=facts,policy_hash=digest(policy),entries={},complete=False)
    profile['complete']=False
    out=ROOT/'results'/('calibration_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(parents=True)
    (out/'policy.json').write_text(json.dumps(policy,indent=2));(out/'identity.json').write_text(json.dumps(facts,indent=2))
    report=[];trained=0;reused=0
    for dataset in dict.fromkeys(x[0] for x in configs):
        prefix='sift' if dataset=='sift1m' else 'glove'
        x=load_vectors(a.data/dataset/f'{prefix}_base.fvecs');queries=load_vectors(a.data/dataset/f'{prefix}_query.fvecs')
        query_file_hash=hashlib.sha256(memoryview(queries).cast('B')).hexdigest()
        setup=time.perf_counter()
        with AdaptiveIndex(x) as index:
            setup_seconds=time.perf_counter()-setup;del x
            for _,nq,k in [v for v in configs if v[0]==dataset]:
                kind=index.prepare(queries[:nq],k)[1];key=index.key(nq,k,kind);label=f'{dataset}_q{nq}_k{k}'
                if key in profile['entries'] and profile['entries'][key].get('validated') and profile['entries'][key].get('query_file_sha256')==query_file_hash:
                    reused+=1;report.append(dict(profile['entries'][key],status='reused'));print('REUSE',label,flush=True);continue
                modes=candidates(kind,index.d,nq);records=[]
                print('CALIBRATE',label,'candidates',modes,flush=True)
                for b,indices in enumerate(splits['train']):
                    q=np.ascontiguousarray(queries[indices[:nq]])
                    od,oi,meta=exact_oracles(index.x,q,k,None,ROOT/'.oracle_cache')
                    record=time_methods(index,q,k,{m:lambda m=m:index.forced(q,k,m) for m in modes},a.repeats,202600+b,(od,oi))
                    record.update(query_indices=indices[:nq],oracle=meta);records.append(record)
                eligible=[m for m in modes if m!=7 and all(v['medians']['7']/v['medians'][str(m)]>=1.03 for v in records)]
                chosen=min(eligible,key=lambda m:sum(math.log(v['medians'][str(m)]) for v in records)) if eligible else 7
                # Freeze selection before examining validation query measurements.
                entry=dict(mode=chosen,block=256,n=index.n,d=index.d,nq=nq,k=k,kind=kind,validated=False,label=label,query_file_sha256=query_file_hash)
                (out/(label+'_training.json')).write_text(json.dumps(dict(selected=entry,batches=records),indent=2))
                index.profile={'entries':{key:entry}}
                validation=[]
                for b,indices in enumerate(splits['validation']):
                    q=np.ascontiguousarray(queries[indices[:nq]]);od,oi,meta=exact_oracles(index.x,q,k,None,ROOT/'.oracle_cache')
                    record=time_methods(index,q,k,{'selected':lambda:index.search(q,k),'original':lambda:index.forced(q,k,7)},a.repeats,202700+b,(od,oi))
                    record.update(query_indices=indices[:nq],oracle=meta,gain=record['medians']['original']/record['medians']['selected']);validation.append(record)
                entry.update(validated=True,validation_gains=[v['gain'] for v in validation],training_medians=[v['medians'] for v in records],evidence=str(out.relative_to(ROOT)/(label+'_validation.json')))
                (out/(label+'_validation.json')).write_text(json.dumps(validation,indent=2))
                profile['entries'][key]=entry;save_profile(a.profile,profile);trained+=1
                report.append(dict(label=label,status='calibrated',mode=chosen,validation_gains=entry['validation_gains'],index_setup_seconds=setup_seconds))
                print('SELECTED',label,chosen,'heldout gains',entry['validation_gains'],flush=True)
    profile['complete']=True;profile['coverage']=configs;save_profile(a.profile,profile)
    final=dict(status='completed',full_scope=not a.quick,configs=len(configs),newly_calibrated=trained,reused=reused,seconds=time.perf_counter()-start,profile=str(a.profile),results=report,scope='Candidate selection and independent comparison to original dispatcher, not a new Faiss performance claim. Calibration cost excluded from search, recorded separately.')
    (out/'SUCCESS.json').write_text(json.dumps(final,indent=2));print(json.dumps(final),flush=True)
if __name__=='__main__':main()
