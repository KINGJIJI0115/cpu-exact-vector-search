"""Fresh-process index construction and RSS costs; no oracle allocation in workers."""
import argparse,csv,datetime,hashlib,json,os,statistics,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--worker',choices=['direct_auto','faiss_blas','faiss_sq8_direct']);ap.add_argument('--dataset',choices=['sift1m','glove25'],default='sift1m');a=ap.parse_args()
os.environ['OPENBLAS_CORETYPE']='Haswell';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
if a.worker:
 import ctypes as ct,resource,time
 import numpy as np,faiss
 from threadpoolctl import threadpool_limits,threadpool_info
 d,n,prefix=(128,1000000,'sift') if a.dataset=='sift1m' else (25,1183514,'glove');nq,k=128,(100 if d==128 else 10)
 def load(name,count):
  result=np.empty((count,d),'float32')
  with (r/'data'/a.dataset/name).open('rb') as f:
   for begin in range(0,count,4096):
    size=min(4096,count-begin);chunk=np.fromfile(f,dtype='<i4',count=size*(d+1)).reshape(size,d+1);assert np.all(chunk[:,0]==d);result[begin:begin+size]=chunk[:,1:].view('<f4')
  return result
 def rss():return next(int(line.split()[1]) for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmRSS:'))
 x=load(prefix+'_base.fvecs',n);q=load(prefix+'_query.fvecs',nq);faiss.omp_set_num_threads(1);before=rss();storage=None
 with threadpool_limits(limits=1):
  start=time.perf_counter()
  if a.worker=='direct_auto':
   lib=ct.CDLL(str(r/'build/libpacked.so'));fp=np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS');ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
   lib.packed_create.argtypes=[fp,ct.c_int,ct.c_int];lib.packed_create.restype=ct.c_void_p;lib.packed_destroy.argtypes=[ct.c_void_p]
   lib.packed_tuned.argtypes=[ct.c_void_p,fp,ct.c_int,ct.c_int,ct.c_int,ct.c_int,fp,ip]
   lib.packed_storage_bytes.argtypes=[ct.c_void_p];lib.packed_storage_bytes.restype=ct.c_size_t
   ptr=lib.packed_create(x,n,d);assert ptr;storage=lib.packed_storage_bytes(ptr)
   def search():
    ds=np.empty((nq,k),'float32');ids=np.empty((nq,k),'int32');assert lib.packed_tuned(ptr,q,nq,k,7,256,ds,ids)==0;return ds,ids
  else:
   if a.worker=='faiss_blas':index=faiss.IndexFlatL2(d);faiss.cvar.distance_compute_blas_threshold=0
   else:assert d==128;index=faiss.IndexScalarQuantizer(d,faiss.ScalarQuantizer.QT_8bit_direct,faiss.METRIC_L2);index.train(x)
   index.add(x);storage=int(index.code_size)*n;search=lambda:index.search(q,k)
  setup_ms=(time.perf_counter()-start)*1000;after_setup=rss()
  for _ in range(3):ds,ids=search();assert ds.shape==(nq,k) and np.all(ids>=0) and np.all(ids<n)
  record=dict(dataset=a.dataset,method=a.worker,q=nq,k=k,input_bytes=x.nbytes,input_rss_kib=before,setup_rss_kib=after_setup,after_search_rss_kib=rss(),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,index_payload_bytes=storage,setup_ms=setup_ms,threadpools=threadpool_info(),scope='Fresh process; same original input array retained; no exhaustive oracle allocated. RSS includes runtime/libraries. Payload excludes allocator/object overhead. Correctness validated separately.')
  if a.worker=='direct_auto':lib.packed_destroy(ptr)
 print(json.dumps(record))
else:
 out=r/'results'/('goal_memory_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir();rows=[];env=os.environ.copy();env['PYTHONPATH']=str(r/'.deps')
 compile_cmd=['g++','-std=c++17','-O3','-mavx2','-mfma','-ffp-contract=off','-shared','-fPIC','src/direct_packed.cpp','-o','build/libpacked.so'];subprocess.run(compile_cmd,cwd=r,check=True)
 for repeat in range(3):
  for dataset,methods in [('sift1m',['direct_auto','faiss_blas','faiss_sq8_direct']),('glove25',['direct_auto','faiss_blas'])]:
   for method in methods:
    proc=subprocess.run([sys.executable,__file__,'--worker',method,'--dataset',dataset],env=env,text=True,capture_output=True);(out/f'{dataset}_{method}_{repeat}.log').write_text(proc.stdout+proc.stderr);proc.check_returncode()
    record=json.loads(proc.stdout);record['repeat']=repeat;rows.append(record);print(dataset,method,repeat,record['peak_rss_kib'],flush=True)
 (out/'raw.json').write_text(json.dumps(rows,indent=2));summary=[]
 for dataset,method in dict.fromkeys((v['dataset'],v['method']) for v in rows):
  selected=[v for v in rows if (v['dataset'],v['method'])==(dataset,method)]
  summary.append(dict(dataset=dataset,method=method,**{key:statistics.median(v[key] for v in selected) for key in ['setup_ms','peak_rss_kib','setup_rss_kib','index_payload_bytes']}))
 with (out/'summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 (out/'manifest.json').write_text(json.dumps(dict(status='passed',source_sha256=hashlib.sha256((r/'src/direct_packed.cpp').read_bytes()).hexdigest(),compile_command=compile_cmd,processes=len(rows)),indent=2));print(out)
