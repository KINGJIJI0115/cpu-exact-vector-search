"""Single-core diagnostic; sampled phase estimates are not production timings."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import argparse,ctypes as ct,csv,datetime,hashlib,json,platform,random,subprocess,time
from pathlib import Path
import numpy as np
from build_profile import ROOT,FIELDS,build

def vectors(p,integer=False):
    a=np.fromfile(p,dtype='<i4');d=int(a[0]);a=a.reshape(-1,d+1);assert np.all(a[:,0]==d)
    return np.ascontiguousarray(a[:,1:] if integer else a[:,1:].view('<f4'))
class Native:
    def __init__(self,path,x,diagnostic=False):
        self.lib=ct.CDLL(str(path));fp=np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS');ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
        self.lib.packed_create.argtypes=[fp,ct.c_int,ct.c_int];self.lib.packed_create.restype=ct.c_void_p
        self.lib.packed_tuned.argtypes=[ct.c_void_p,fp,ct.c_int,ct.c_int,ct.c_int,ct.c_int,fp,ip]
        self.lib.packed_destroy.argtypes=[ct.c_void_p]
        self.h=self.lib.packed_create(x,len(x),x.shape[1]);assert self.h
        self.diagnostic=diagnostic
        if diagnostic:
            self.lib.v2_reset.argtypes=[ct.c_uint64,ct.c_uint64];self.lib.v2_read.argtypes=[ct.POINTER(ct.c_uint64)]
    def search(self,q,k,mode,block=256,period=128,seed=1):
        if self.diagnostic:self.lib.v2_reset(period,seed)
        ds=np.empty((len(q),k),'float32');ids=np.empty((len(q),k),'int32')
        start=time.perf_counter_ns();code=self.lib.packed_tuned(self.h,q,len(q),k,mode,block,ds,ids);ns=time.perf_counter_ns()-start
        assert code==0
        stats={}
        if self.diagnostic:
            a=(ct.c_uint64*len(FIELDS))();self.lib.v2_read(a);stats=dict(zip(FIELDS,a))
        return ds,ids,ns/1e6,stats
    def close(self):
        if self.h:self.lib.packed_destroy(self.h);self.h=None

def oracle(x,q,k):
    delta=x.astype('float64')-q.astype('float64');dist=np.einsum('ij,ij->i',delta,delta);ids=np.lexsort((np.arange(len(x)),dist))[:k]
    return dist[ids],ids

def correctness(folder):
    rng=np.random.default_rng(271127);cases=0
    for n,d in [(7,3),(17,128),(137,128),(41,25),(19,258)]:
        x=rng.integers(0,256,(n,d)).astype('float32');x[1]=x[0]
        for floating in [False,True]:
            q=rng.integers(0,256,(5,d)).astype('float32');q[0]=x[0]
            if floating:q+=np.float32(.25)
            a=Native(folder/'control.so',x);b=Native(folder/'diagnostic.so',x,True)
            try:
                for k in sorted(set([1,min(10,n),n])):
                    for mode in [7,102]:
                        da,ia,_,_=a.search(q,k,mode);db,ib,_,_=b.search(q,k,mode,period=2)
                        np.testing.assert_array_equal(da,db);np.testing.assert_array_equal(ia,ib)
                        for i in range(len(q)):
                            od,oi=oracle(x,q[i],k);np.testing.assert_array_equal(ia[i],oi);np.testing.assert_allclose(da[i],od,rtol=1e-5 if floating else 0,atol=1e-4 if floating else 0)
                        cases+=1
            finally:a.close();b.close()
    return {'cases':cases,'passed':True,'scope':'Independent float64 exhaustive oracle on small integer/tie/tail/K=N and noninteger query inputs; profile/control equivalence.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cpu',type=int,default=0);ap.add_argument('--repeats',type=int,default=5);ap.add_argument('--periods',default='32,128,512');ap.add_argument('--build-only',action='store_true');a=ap.parse_args()
    assert a.cpu in os.sched_getaffinity(0);os.sched_setaffinity(0,{a.cpu});os.nice(10)
    a.out.mkdir(parents=True,exist_ok=False);folder=a.out/'build';record=build(folder)
    check=correctness(folder);(a.out/'correctness.json').write_text(json.dumps(check,indent=2));print('CORRECTNESS',check,flush=True)
    if a.build_only:return
    periods=[int(x) for x in a.periods.split(',')];assert all(p>0 and p&(p-1)==0 for p in periods)
    x=vectors(a.data/'sift1m/sift_base.fvecs');queries=vectors(a.data/'sift1m/sift_query.fvecs');gt=vectors(a.data/'sift1m/sift_groundtruth.ivecs',True)
    assert x.shape==(1000000,128)
    env=dict(date=datetime.datetime.now(datetime.timezone.utc).isoformat(),platform=platform.platform(),numpy=np.__version__,cpu=a.cpu,threads=1,lscpu=subprocess.check_output(['lscpu'],text=True),build=record,dataset_sha256=hashlib.sha256(memoryview(x).cast('B')).hexdigest(),query_sha256=hashlib.sha256(memoryview(queries).cast('B')).hexdigest(),scope='Development diagnostics using historical batch-0 query indices; not new held-out Faiss results.')
    try:
        perf=subprocess.run(['perf','stat','-e','cycles,instructions','--','true'],capture_output=True,text=True,timeout=10)
        env['perf_probe']={'exit':perf.returncode,'stderr':perf.stderr}
    except Exception as exc:env['perf_probe']={'error':str(exc)}
    (a.out/'environment.json').write_text(json.dumps(env,indent=2))
    control=Native(folder/'control.so',x);diag=Native(folder/'diagnostic.so',x,True)
    rows=[];checks=[];rng=random.Random(20261127)
    cases=[(128,1,7),(128,100,7),(256,10,7),(256,100,7),(4,10,7),(4,10,102)]
    try:
      for nq,k,mode in cases:
        label=f'sift1m_q{nq}_k{k}_mode{mode}'
        ref=json.loads((ROOT/f'evidence/faiss78/sift1m_q{nq}_k{k}_b0.json').read_text());indices=ref['validation']['query_indices'];q=np.ascontiguousarray(queries[indices]);assert len(q)==nq
        d0,i0,_,_=control.search(q,k,mode)
        truth=x[gt[indices,:k]].astype('float64')-q[:,None,:].astype('float64');td=np.einsum('qkd,qkd->qk',truth,truth)
        np.testing.assert_array_equal(d0,np.sort(td,axis=1));assert all(len(set(v))==k for v in i0)
        checks.append({'label':label,'official_groundtruth_distances_exact':True,'query_indices':indices})
        for period in periods:
            d1,i1,_,_=diag.search(q,k,mode,period=period);np.testing.assert_array_equal(d0,d1);np.testing.assert_array_equal(i0,i1)
        for rep in range(a.repeats):
            methods=[0]+periods;rng.shuffle(methods)
            for period in methods:
                start=time.perf_counter_ns();prepared=np.ascontiguousarray(q,dtype=np.float32)
                assert np.isfinite(prepared).all();kind=bool(np.all((prepared>=0)&(prepared<=255)&(prepared==np.floor(prepared))))
                prepare_ms=(time.perf_counter_ns()-start)/1e6
                d1,i1,native_ms,stats=(control if period==0 else diag).search(prepared,k,mode,period=period or 128,seed=10000+rep*991)
                api_ms=(time.perf_counter_ns()-start)/1e6
                np.testing.assert_array_equal(d1,d0);np.testing.assert_array_equal(i1,i0)
                rows.append(dict(label=label,q=nq,k=k,mode=mode,repeat=rep,sample_period=period,native_ms=native_ms,wrapper_ms=api_ms,python_prepare_ms=prepare_ms,**stats))
        print('CASE',label,'complete',flush=True)
        (a.out/'raw.json').write_text(json.dumps(rows,indent=2));(a.out/'validation.json').write_text(json.dumps(checks,indent=2))
    finally:control.close();diag.close()
    import statistics
    summary=[]
    for nq,k,mode in cases:
      label=f'sift1m_q{nq}_k{k}_mode{mode}';base=[r for r in rows if r['label']==label and r['sample_period']==0];base_ms=statistics.median(r['native_ms'] for r in base)
      for period in periods:
        rr=[r for r in rows if r['label']==label and r['sample_period']==period];dist=sum(r['distance_ns'] for r in rr);sel=sum(r['selection_ns'] for r in rr)
        summary.append(dict(label=label,period=period,control_native_ms=base_ms,control_wrapper_ms=statistics.median(r['wrapper_ms'] for r in base),diagnostic_native_ms=statistics.median(r['native_ms'] for r in rr),diagnostic_overhead_ratio=statistics.median(r['native_ms'] for r in rr)/base_ms,distance_sample_share=dist/(dist+sel),selection_sample_share=sel/(dist+sel),prepare_ms=statistics.median(r['prepare_ns']/1e6 for r in rr),finalize_ms=statistics.median(r['finalize_ns']/1e6 for r in rr),sampled_tiles=sum(r['sampled_tiles'] for r in rr)))
    with (a.out/'summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    (a.out/'SUCCESS.json').write_text(json.dumps({'status':'passed','cases':len(cases),'repeats':a.repeats,'periods':periods,'interpretation':'Phase shares estimated from sampled instrumented tiles; compare periods and diagnostic overhead. Distance phase excludes accumulator reduction; selection includes reduction, mask and heap. Wrapper is a diagnostic harness, not the full AdaptiveIndex API. Not a Faiss comparison.'},indent=2))
    print(a.out,flush=True)
if __name__=='__main__':main()
