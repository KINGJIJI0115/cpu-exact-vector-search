"""Frozen-profile, same-query, single-thread confirmation; never tunes kernels."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_CORETYPE='Haswell')
import csv,datetime,hashlib,json,math,random,statistics,sys,time,traceback,shutil
from pathlib import Path
import numpy as np
import faiss
from threadpoolctl import threadpool_limits,threadpool_info
from adaptive import AdaptiveIndex,ROOT,identity,digest
from oracle_cache import exact_oracles

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):Path(path).write_text(json.dumps(obj,indent=2))
def vectors(path,integer=False):
    a=np.fromfile(path,dtype='<i4');d=int(a[0]);a=a.reshape(-1,d+1);assert np.all(a[:,0]==d)
    return np.ascontiguousarray(a[:,1:] if integer else a[:,1:].view('<f4'))
def verify(x,q,k,result,od,oi,dataset):
    ds,ids=result
    assert ds.shape==ids.shape==(len(q),k) and np.all((ids>=0)&(ids<len(x)))
    assert all(len(set(row))==k for row in ids)
    true=np.sum((x[ids].astype('float64')-q[:,None,:].astype('float64'))**2,axis=2)
    np.testing.assert_allclose(ds,true,rtol=1e-5,atol=1e-4)
    np.testing.assert_allclose(true,od,rtol=1e-5 if dataset=='glove25' else 0,atol=1e-6 if dataset=='glove25' else 0)
    return dict(correct=True,max_distance_error=float(np.max(abs(ds-true))),max_rank_gap=float(np.max(abs(true-od))),id_recall=float(np.mean([len(set(a)&set(b))/k for a,b in zip(ids,oi)])))

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cpu',type=int,default=19);ap.add_argument('--profile',type=Path,default=ROOT/'profiles/local.json');a=ap.parse_args()
    os.sched_setaffinity(0,{a.cpu});faiss.omp_set_num_threads(1)
    out=a.out;out.mkdir(parents=True,exist_ok=False)
    profile=a.profile;scope=json.loads((ROOT/'goal_scope.json').read_text())
    frozen={str(p):sha(p) for p in [profile,ROOT/'adaptive.py',ROOT/'src/autotune_kernels.cpp',ROOT/'build/libautotune.so',ROOT/'build/build.json',ROOT/'goal_scope.json',Path(__file__)]}
    for p in frozen:
        dst=out/'frozen'/Path(p).name;dst.parent.mkdir(exist_ok=True);dst.write_bytes(Path(p).read_bytes())
    train=set(random.Random(scope['baseline_seed']).sample(range(128,10000),256))
    ids=random.Random(scope['confirmation_seed']).sample([i for i in range(128,10000) if i not in train],768)
    payload=json.loads(profile.read_text())['payload']
    policies=[json.loads(p.read_text()) for p in (ROOT/'results').glob('calibration_*/policy.json')]
    matching=[p for p in policies if digest(p)==payload['policy_hash']]
    assert matching,'No policy matching current profile; run full calibration first'
    policy=matching[-1]
    reference=ROOT.parent/'evidence/faiss78'
    assert ids==json.loads((reference/'manifest.json').read_text())['query_indices']
    assert not set(ids)&set(sum(policy['splits']['train'],[]))
    assert not set(ids)&set(sum(policy['splits']['validation'],[]))
    oldratios={r['label']:r for r in json.loads((reference/'previous_ratios.json').read_text())}
    manifest=dict(status='running',started=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity=identity(),frozen_sha256=frozen,scope=scope,query_indices=ids,training_disjoint=True,faiss=faiss.__version__,faiss_compile_options=faiss.get_compile_options(),openblas_coretype='Haswell',timing='Python public search calls and output allocations; index building/calibration/oracle excluded. Seven randomized interleaved repeats; first call validates and warms up.',profile_frozen=True)
    write(out/'manifest.json',manifest)
    cache=out/'.oracle_cache';cache.mkdir()
    for p in (a.base/'.oracle_cache').glob('*.npz'):
        try:os.link(p,cache/p.name)
        except OSError:shutil.copy2(p,cache/p.name)
    start=time.perf_counter();rows=[];raw=[];checks=[];setup={}
    with threadpool_limits(limits=1):
      manifest['threadpools']=threadpool_info();assert faiss.omp_get_max_threads()==1
      assert all(p['num_threads']==1 for p in manifest['threadpools'])
      for dataset in dict.fromkeys(v[0] for v in scope['configs']):
        prefix='sift' if dataset=='sift1m' else 'glove';data=a.base/'data'/dataset
        x=vectors(data/(prefix+'_base.fvecs'));queries=vectors(data/(prefix+'_query.fvecs'))
        gt=vectors(data/(prefix+'_groundtruth.ivecs'),True) if dataset=='sift1m' else None
        assert list(x.shape)==[scope['datasets'][dataset]['n'],scope['datasets'][dataset]['d']]
        t=time.perf_counter();index=AdaptiveIndex(x,profile);assert index.profile_status=='matched';assert index.profile['complete']
        setup[dataset]={'adaptive_seconds':time.perf_counter()-t,'database_sha256':index.database_hash,'queries_sha256':hashlib.sha256(memoryview(queries).cast('B')).hexdigest()}
        t=time.perf_counter();flat=faiss.IndexFlatL2(x.shape[1]);flat.add(x);setup[dataset]['faiss_flat_seconds']=time.perf_counter()-t
        sq8=None
        if dataset=='sift1m':
            assert np.all((x>=0)&(x<=255)&(x==np.floor(x)))
            t=time.perf_counter();sq8=faiss.IndexScalarQuantizer(x.shape[1],faiss.ScalarQuantizer.QT_8bit_direct,faiss.METRIC_L2);sq8.train(x);sq8.add(x);setup[dataset]['faiss_sq8_seconds']=time.perf_counter()-t
        for _,nq,k in [v for v in scope['configs'] if v[0]==dataset]:
          for batch in range(3):
            assert all(sha(p)==h for p,h in frozen.items()),'Frozen source/profile changed'
            label=f'{dataset}_q{nq}_k{k}_b{batch}';indices=ids[batch*256:batch*256+nq]
            assert indices==json.loads((reference/(label+'.json')).read_text())['validation']['query_indices']
            q=np.ascontiguousarray(queries[indices]);kind=index.prepare(q,k)[1];entry=index.profile['entries'][index.key(nq,k,kind)]
            print(f'{len(rows)+1}/78 {label} mode={entry["mode"]}',flush=True)
            od,oi,oracle=exact_oracles(x,q,k,gt[indices] if gt is not None else None,cache)
            def path(threshold):
                previous=faiss.cvar.distance_compute_blas_threshold
                try:faiss.cvar.distance_compute_blas_threshold=threshold;return flat.search(q,k)
                finally:faiss.cvar.distance_compute_blas_threshold=previous
            methods={'adaptive':lambda:index.search(q,k),'original':lambda:index.forced(q,k,7),'faiss_flat':lambda:flat.search(q,k),'faiss_direct':lambda:path(10**9),'faiss_blas':lambda:path(0)}
            if sq8 is not None:methods['faiss_sq8_direct']=lambda:sq8.search(q,k)
            validation={name:verify(x,q,k,call(),od,oi,dataset) for name,call in methods.items()}
            assert index.last_mode==entry['mode']
            local=[];rng=random.Random(2026112400+len(rows))
            for rep in range(scope['repeats']):
                order=list(methods);rng.shuffle(order)
                for name in order:
                    t=time.perf_counter_ns();result=methods[name]();ms=(time.perf_counter_ns()-t)/1e6
                    local.append(dict(label=label,repeat=rep,method=name,ms=ms))
            med={name:statistics.median(r['ms'] for r in local if r['method']==name) for name in methods}
            best=min(scope['faiss_methods'][dataset],key=med.get);previous=oldratios[label]
            row=dict(label=label,dataset=dataset,q=nq,k=k,batch=batch,mode=entry['mode'],custom_ms=med['adaptive'],original_ms=med['original'],best_faiss_method=best,best_faiss_ms=med[best],gain=med[best]/med['adaptive'],gain_over_original=med['original']/med['adaptive'],passed=med['adaptive']<=med[best],previous_gain=1/previous['ratio'],previous_passed=previous['pass'])
            rows.append(row);raw.extend(local);checks.append(dict(label=label,query_indices=indices,oracle=oracle,methods=validation))
            write(out/(label+'.json'),dict(summary=row,medians=med,raw=local,validation=checks[-1]))
            write(out/'partial.json',rows)
            print(f'  gain/Faiss={row["gain"]:.4f}; gain/original={row["gain_over_original"]:.4f}; best={best}',flush=True)
        index.close();del index,flat,sq8,x,queries,gt
    assert len(rows)==78 and all(sha(p)==h for p,h in frozen.items())
    for name,data in [('summary.csv',rows),('raw.csv',raw)]:
        with (out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    write(out/'validation.json',checks);write(out/'setup.json',setup)
    manifest.update(status='completed',cases=len(rows),passed=sum(r['passed'] for r in rows),correct_cases=len(checks),gain_geomean=math.exp(statistics.mean(math.log(r['gain']) for r in rows)),gain_min=min(r['gain'] for r in rows),gain_max=max(r['gain'] for r in rows),seconds=time.perf_counter()-start,completed=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(out/'manifest.json',manifest);print(json.dumps(manifest),flush=True)
if __name__=='__main__':
    try:main()
    except Exception:traceback.print_exc();sys.exit(1)
