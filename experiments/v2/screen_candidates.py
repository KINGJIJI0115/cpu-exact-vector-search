"""Development screening then frozen independent confirmation, no Faiss claim."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import argparse,csv,ctypes as ct,datetime,json,random,statistics,time,hashlib
from pathlib import Path
import numpy as np
from profile_bottlenecks import Native,vectors,oracle,ROOT
from build_candidates import build

def tests(control,variant):
 rng=np.random.default_rng(271128);cases=0
 for n,d in [(7,128),(17,128),(139,128),(33,25),(17,258)]:
  for value in ['random','max','float_database']:
   x=rng.integers(0,256,(n,d)).astype('float32') if value!='max' else np.full((n,d),255,'float32')
   if value=='float_database':x+=np.float32(.25)
   x[1]=x[0];a=Native(control,x);b=Native(variant,x)
   try:
    for nq in [1,4,9]:
     q=rng.integers(0,256,(nq,d)).astype('float32');q[0]=x[0]
     if value=='max':q[0]=0
     if value=='float_database':q+=np.float32(.5)
     for k in sorted(set([1,min(n,10),n])):
      for mode in [200,201]:
       dc,ic,_,_=a.search(q,k,7);dv,iv,_,_=b.search(q,k,mode,block=64)
       np.testing.assert_array_equal(dc,dv);np.testing.assert_array_equal(ic,iv)
       for i in range(nq):
        od,oi=oracle(x,q[i],k);np.testing.assert_array_equal(iv[i],oi);np.testing.assert_allclose(dv[i],od,rtol=1e-5 if value=='float_database' else 0,atol=1e-4 if value=='float_database' else 0)
       cases+=1
    if d==128 and value=='random':
     q=rng.integers(0,256,(9,d)).astype('float32')+.25
     for mode in [200,201]:
      dc,ic,_,_=a.search(q,7,7);dv,iv,_,_=b.search(q,7,mode);np.testing.assert_array_equal(dc,dv);np.testing.assert_array_equal(ic,iv);cases+=1
   finally:a.close();b.close()
 return dict(passed=True,cases=cases,scope='Float64 exhaustive oracle, exact byte distances/IDs, tails/ties/K=N/0/255; release equivalence including float/non128 fallbacks.')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--control',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cpu',type=int,default=0);ap.add_argument('--repeats',type=int,default=5);ap.add_argument('--confirm-repeats',type=int,default=5);ap.add_argument('--fast-screen',action='store_true');a=ap.parse_args()
 os.sched_setaffinity(0,{a.cpu});os.nice(10);a.out.mkdir(parents=True,exist_ok=False);build(a.out/'build')
 ck=tests(a.control,a.out/'build/candidate.so');(a.out/'correctness.json').write_text(json.dumps(ck,indent=2));print('CORRECTNESS',ck,flush=True)
 x=vectors(a.data/'sift1m/sift_base.fvecs');qq=vectors(a.data/'sift1m/sift_query.fvecs');gt=vectors(a.data/'sift1m/sift_groundtruth.ivecs',True)
 t=time.perf_counter();control=Native(a.control,x);setup_control=time.perf_counter()-t
 t=time.perf_counter();variant=Native(a.out/'build/candidate.so',x);setup_variant=time.perf_counter()-t
 variant.lib.v2_norm_storage.argtypes=[ct.c_void_p];variant.lib.v2_norm_storage.restype=ct.c_size_t
 extra=variant.lib.v2_norm_storage(variant.h)
 scope=json.loads((ROOT/'autotune/goal_scope.json').read_text());oldtrain=set(random.Random(scope['baseline_seed']).sample(range(128,10000),256));oldtest=set(random.Random(scope['confirmation_seed']).sample([i for i in range(128,10000) if i not in oldtrain],768));forbidden=oldtrain|oldtest|{4324,779,4529,5547,8423};oldcal=set(random.Random(2026122501).sample([i for i in range(128,10000) if i not in forbidden],1024));unused=[i for i in range(128,10000) if i not in forbidden|oldcal]
 newids=random.Random(2026112701).sample(unused,768);assert not set(newids)&(forbidden|oldcal)
 policy={'screening':'historical batch-0','new_confirmation_indices':newids,'excluded_old_training_and_confirmation':True,'selection':'one minimum median candidate with at least 3% screening gain, otherwise baseline; selection frozen before confirmation','repeats':a.repeats,'confirmation_repeats':a.confirm_repeats,'fast_screen':a.fast_screen,'cpu':a.cpu,'norm_bytes':int(extra),'setup_seconds_single_observation':{'control':setup_control,'variant':setup_variant}}
 (a.out/'policy.json').write_text(json.dumps(policy,indent=2));raw=[];selected=[];rng=random.Random(2026112702)
 candidates={'base':(control,7,256)}
 for b in ([64,128,512] if a.fast_screen else [64,128,192,512,1024]):candidates[f'block{b}']=(control,7,b)
 for mode in [200,201]:
  for b in ([256] if a.fast_screen and mode==201 else [128,256,512]):candidates[f'dot{mode}_block{b}']=(variant,mode,b)
 def run(q,k,label,methods,phase,batch):
  d0,i0,_,_=control.search(q,k,7);local=[]
  for key,(obj,m,b) in methods.items():
   d,i,_,_=obj.search(q,k,m,b);np.testing.assert_array_equal(d,d0);np.testing.assert_array_equal(i,i0)
  for rep in range(a.repeats if phase=='screening' else a.confirm_repeats):
   keys=list(methods);rng.shuffle(keys)
   for key in keys:
    obj,m,b=methods[key];t=time.perf_counter_ns();d,i,nms,_=obj.search(q,k,m,b);ms=(time.perf_counter_ns()-t)/1e6
    np.testing.assert_array_equal(d,d0);np.testing.assert_array_equal(i,i0)
    row=dict(phase=phase,batch=batch,label=label,method=key,repeat=rep,ms=ms,native_ms=nms);local.append(row);raw.append(row)
  return {key:statistics.median(r['ms'] for r in local if r['method']==key) for key in methods}
 try:
  cases=[(128,1),(128,100),(256,10),(256,100)]
  for nq,k in cases:
   label=f'sift1m_q{nq}_k{k}';indices=json.loads((ROOT/f'evidence/faiss78/{label}_b0.json').read_text())['validation']['query_indices'];q=np.ascontiguousarray(qq[indices]);med=run(q,k,label,candidates,'screening',0);best=min(med,key=med.get);choice=best if med['base']/med[best]>=1.03 else 'base';selected.append(dict(label=label,q=nq,k=k,selected=choice,screening_gain=med['base']/med[choice],medians=med));print('SCREEN',selected[-1],flush=True)
   (a.out/'raw.json').write_text(json.dumps(raw,indent=2))
  (a.out/'frozen_selection.json').write_text(json.dumps(selected,indent=2));frozen_hash=hashlib.sha256((a.out/'frozen_selection.json').read_bytes()).hexdigest();confirmation=[]
  for entry in selected:
   nq,k,choice=entry['q'],entry['k'],entry['selected']
   for batch in range(3):
    ids=newids[batch*256:batch*256+nq];q=np.ascontiguousarray(qq[ids]);d0,i0,_,_=control.search(q,k,7);delta=x[gt[ids,:k]].astype('float64')-q[:,None,:].astype('float64');np.testing.assert_array_equal(d0,np.sort(np.einsum('qkd,qkd->qk',delta,delta),axis=1))
    methods={'base':candidates['base']};methods[choice]=candidates[choice];med=run(q,k,entry['label'],methods,'confirmation',batch);confirmation.append(dict(label=entry['label'],batch=batch,selected=choice,base_ms=med['base'],selected_ms=med[choice],gain=med['base']/med[choice],official_groundtruth_distances_exact=True));print('CONFIRM',confirmation[-1],flush=True)
    (a.out/'raw.json').write_text(json.dumps(raw,indent=2));(a.out/'confirmation.json').write_text(json.dumps(confirmation,indent=2))
  assert hashlib.sha256((a.out/'frozen_selection.json').read_bytes()).hexdigest()==frozen_hash
  (a.out/'SUCCESS.json').write_text(json.dumps(dict(status='passed',scope='Local development 4 configurations, not 78-case Faiss comparison; selected before fresh confirmation queries',frozen_selection_sha256=frozen_hash,cases=len(confirmation),norm_bytes=int(extra)),indent=2))
 finally:control.close();variant.close()
 print(a.out,flush=True)
if __name__=='__main__':main()
