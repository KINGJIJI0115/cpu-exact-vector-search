"""PYTHONPATH=.deps taskset -c 0 python3 compare.py
Both libraries run inside the same process, in random order, single threaded.
"""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[name]='1'
import ctypes as ct
import csv
import datetime
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import time
import argparse
import platform
import sys
import numpy as np
import faiss
from threadpoolctl import threadpool_limits, threadpool_info

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--synthetic',type=int,default=0,help='Use this many reproducible synthetic integer-valued vectors')
parser.add_argument('--repeats',type=int,default=21)
parser.add_argument('--dataset',choices=['siftsmall','sift1m','glove25'],default='siftsmall')
parser.add_argument('--limit',type=int,default=0)
parser.add_argument('--queries',type=int,default=0)
parser.add_argument('--k',type=int,default=10)
parser.add_argument('--methods',default='',help='Comma separated method names; empty means all')
parser.add_argument('--query-indices',type=Path,help='JSON list of distinct zero-based real query indices')
parser.add_argument('--hybrid-block',type=int,default=8192)
args=parser.parse_args()
if args.synthetic and args.synthetic<10: parser.error('synthetic size must be >=10')
if args.repeats<1: parser.error('repeats must be positive')
if args.hybrid_block<1: parser.error('hybrid block must be positive')
OUT=ROOT/'results'/('comparison_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
OUT.mkdir(parents=True)
build=ROOT/'build'; build.mkdir(exist_ok=True)
cmd=['g++','-std=c++17','-O3','-mavx2','-ffp-contract=off','-shared','-fPIC',str(ROOT/'src/library.cpp'),'-o',str(build/'libsearch.so')]
subprocess.run(cmd,check=True)
lib=ct.CDLL(str(build/'libsearch.so'))
fp=np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS')
ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
lib.vs_create.argtypes=[fp,ct.c_int,ct.c_int]; lib.vs_create.restype=ct.c_void_p
lib.vs_destroy.argtypes=[ct.c_void_p]; lib.vs_destroy.restype=None
lib.vs_search.argtypes=[ct.c_void_p,fp,ct.c_int,ct.c_int,ct.c_int,ct.c_int,fp,ip]
lib.vs_search.restype=ct.c_int
data_dir=ROOT/'data' if args.dataset=='siftsmall' else ROOT/'data'/args.dataset
def vectors(name,integer=False):
    a=np.fromfile(data_dir/name,dtype='<i4')
    d=int(a[0]); a=a.reshape(-1,d+1)
    assert np.all(a[:,0]==d)
    return np.ascontiguousarray(a[:,1:] if integer else a[:,1:].view('<f4'))
prefix='glove' if args.dataset=='glove25' else ('siftsmall' if args.dataset=='siftsmall' else 'sift')
x=vectors(prefix+'_base.fvecs'); q=vectors(prefix+'_query.fvecs')
gt=None if args.dataset=='glove25' else vectors(prefix+'_groundtruth.ivecs',True)
query_indices=None
if args.query_indices:
    if args.synthetic: parser.error('query indices require real data')
    query_indices=json.loads(args.query_indices.read_text())
    if not isinstance(query_indices,list) or not query_indices or any(type(i)!=int or i<0 or i>=len(q) for i in query_indices) or len(set(query_indices))!=len(query_indices):
        parser.error('invalid query indices')
    q=np.ascontiguousarray(q[query_indices]);gt=np.ascontiguousarray(gt[query_indices]) if gt is not None else None
assert x.shape[1]==q.shape[1]
if args.limit:
    x=x[:args.limit].copy();gt=None
if args.synthetic:
    generator=np.random.default_rng(20261109)
    x=generator.integers(0,256,(args.synthetic,128)).astype(np.float32)
    q=generator.integers(0,256,(32,128)).astype(np.float32)
    gt=None
batches=[1,32] if args.synthetic or args.dataset=='sift1m' else [1,32,100]
if args.queries: batches=[args.queries]
if min(batches)<1 or max(batches)>len(q): parser.error('invalid query count')
q=q[:max(batches)]
k=args.k
if k<1 or k>len(x): parser.error('K out of range')
# External ground truth and independent float64 oracle; equal-distance IDs may differ.
from oracle_cache import exact_oracles
oracle_d,oracle_i,oracle_metadata=exact_oracles(x,q,k,gt,ROOT/'.oracle_cache')
faiss.omp_set_num_threads(1)
start=time.perf_counter(); index=faiss.IndexFlatL2(x.shape[1]); index.add(x)
faiss_setup_ms=(time.perf_counter()-start)*1000
start=time.perf_counter(); handle=lib.vs_create(x,*x.shape)
custom_setup_ms=(time.perf_counter()-start)*1000
assert handle
hybrid=None;hybrid_setup_ms=None;hybrid_phases=[]
if 'hybrid_' in args.methods:
    from hybrid import Hybrid
    start=time.perf_counter();hybrid=Hybrid(x,lib)
    hybrid_setup_ms=(time.perf_counter()-start)*1000
sq8=None;sq8_setup_ms=None
if 'faiss_sq8_direct' in args.methods:
    assert np.all(x>=0) and np.all(x<=255) and np.all(x==np.floor(x))
    assert np.all(q>=0) and np.all(q<=255) and np.all(q==np.floor(q))
    start=time.perf_counter();sq8=faiss.IndexScalarQuantizer(x.shape[1],faiss.ScalarQuantizer.QT_8bit_direct,faiss.METRIC_L2);sq8.train(x);sq8.add(x)
    sq8_setup_ms=(time.perf_counter()-start)*1000
rows=[]; checks=[]; rng=random.Random(20261109)
packed_handle=None;packed_setup_ms=None
if 'direct_packed' in args.methods or 'direct_auto' in args.methods:
    packed_cmd=cmd.copy();packed_cmd[-3]=str(ROOT/'src/direct_packed.cpp');packed_cmd[-1]=str(build/'libpacked.so')
    packed_cmd.insert(1,'-mfma')
    subprocess.run(packed_cmd,check=True)
    packed_lib=ct.CDLL(str(build/'libpacked.so'))
    packed_lib.packed_create.argtypes=[fp,ct.c_int,ct.c_int];packed_lib.packed_create.restype=ct.c_void_p
    packed_lib.packed_search.argtypes=[ct.c_void_p,fp,ct.c_int,ct.c_int,fp,ip]
    packed_lib.packed_tuned.argtypes=[ct.c_void_p,fp,ct.c_int,ct.c_int,ct.c_int,ct.c_int,fp,ip]
    packed_lib.packed_destroy.argtypes=[ct.c_void_p]
    packed_lib.packed_query_route.argtypes=[ct.c_void_p,fp,ct.c_int,ct.c_int]
    packed_lib.packed_storage_bytes.argtypes=[ct.c_void_p];packed_lib.packed_storage_bytes.restype=ct.c_size_t
    packed_lib.packed_byte_storage_bytes.argtypes=[ct.c_void_p];packed_lib.packed_byte_storage_bytes.restype=ct.c_size_t
    start=time.perf_counter();packed_handle=packed_lib.packed_create(x,*x.shape)
    packed_setup_ms=(time.perf_counter()-start)*1000;assert packed_handle
try:
    with threadpool_limits(limits=1):
        pools=threadpool_info()
        for nq in batches:
            queries=q[:nq].copy()
            def custom(mask):
                ds=np.empty((nq,k),np.float32); ids=np.empty((nq,k),np.int32)
                assert lib.vs_search(handle,queries,nq,k,mask,256,ds,ids)==0
                return ds,ids
            def faiss_path(threshold):
                previous=faiss.cvar.distance_compute_blas_threshold
                try:
                    faiss.cvar.distance_compute_blas_threshold=threshold
                    return index.search(queries,k)
                finally:
                    faiss.cvar.distance_compute_blas_threshold=previous
            methods={'custom_topk':lambda:custom(1),'custom_topk_simd':lambda:custom(5),
                     'custom_all':lambda:custom(7),'stream_scalar':lambda:custom(8),
                     'stream_simd':lambda:custom(12),'stream_all':lambda:custom(14),
                     'faiss_flat':lambda:index.search(queries,k),
                     'faiss_direct':lambda:faiss_path(1000000000),
                     'faiss_blas':lambda:faiss_path(0)}
            if sq8 is not None:methods['faiss_sq8_direct']=lambda:sq8.search(queries,k)
            if hybrid is not None:
                methods.update(hybrid_heap=lambda:hybrid.search(queries,k,args.hybrid_block,0),
                               hybrid_select=lambda:hybrid.search(queries,k,args.hybrid_block,1),
                               hybrid_faissblas=lambda:hybrid.search(queries,k,args.hybrid_block,0,backend='faiss'),
                               hybrid_scalarfilter=lambda:hybrid.search(queries,k,args.hybrid_block,2,backend='faiss'))
            if packed_handle:
                def packed():
                    ds=np.empty((nq,k),np.float32);ids=np.empty((nq,k),np.int32)
                    assert packed_lib.packed_search(packed_handle,queries,nq,k,ds,ids)==0
                    return ds,ids
                methods['direct_packed']=packed
                def tuned(mode,block):
                    ds=np.empty((nq,k),np.float32);ids=np.empty((nq,k),np.int32)
                    assert packed_lib.packed_tuned(packed_handle,queries,nq,k,mode,block,ds,ids)==0
                    return ds,ids
                for mode in range(16):
                    methods[f'direct_packed_m{mode}']=lambda mode=mode:tuned(mode,256)
                methods['direct_auto']=lambda:tuned(7,256)
                for block in [64,128,512,1024]:
                    methods[f'direct_packed_b{block}']=lambda block=block:tuned(6,block)
            if args.methods:
                selected=args.methods.split(',')
                if not set(selected)<=set(methods): parser.error('unknown method')
                methods={name:methods[name] for name in selected}
            for name,method in methods.items():
                ds,ids=method()
                assert np.all(ids>=0) and np.all(ids<len(x))
                assert all(len(set(row))==k for row in ids)
                true=np.sum((x[ids].astype(np.float64)-queries[:,None,:])**2,axis=2)
                np.testing.assert_allclose(ds,true,rtol=1e-5,atol=1e-4)
                np.testing.assert_allclose(true,oracle_d[:nq],rtol=1e-5 if args.dataset=='glove25' else 0,atol=1e-6 if args.dataset=='glove25' else 0)
                checks.append({'nq':nq,'method':name,'correct':True,
                               'strict_id_matches':int(np.sum(ids==oracle_i[:nq])),
                               'total_ids':nq*k,'max_absolute_distance_error':float(np.max(np.abs(ds-true))),
                               'max_rank_distance_gap':float(np.max(np.abs(true-oracle_d[:nq]))),
                               'exact_distance_multiset_match':bool(np.array_equal(np.sort(true,axis=1),oracle_d[:nq])),
                               'oracle_id_recall':float(np.mean([len(set(a)&set(b))/k for a,b in zip(ids,oracle_i[:nq])])),
                               'validation_policy':'float tolerance 1e-5 relative + 1e-6 absolute; exact metrics separately recorded' if args.dataset=='glove25' else 'exact double-distance ranking'})
            if hybrid is not None:
                for mode in [0,1]:
                    phases={'nq':nq,'mode':mode}
                    hybrid.search(queries,k,args.hybrid_block,mode,phases)
                    hybrid_phases.append(phases)
            for rep in range(args.repeats):
                names=list(methods); rng.shuffle(names)
                for name in names:
                    start=time.perf_counter_ns(); result=methods[name]()
                    ms=(time.perf_counter_ns()-start)/1e6
                    rows.append({'nq':nq,'repeat':rep,'method':name,'ms':ms})
finally:
    packed_facts={'route':packed_lib.packed_query_route(packed_handle,q,len(q),k),'storage_bytes':packed_lib.packed_storage_bytes(packed_handle),'byte_storage_bytes':packed_lib.packed_byte_storage_bytes(packed_handle)} if packed_handle else None
    lib.vs_destroy(handle)
    if packed_handle:packed_lib.packed_destroy(packed_handle)
with (OUT/'raw.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
summary=[]
for nq in batches:
    for name in methods:
        values=[r['ms'] for r in rows if r['nq']==nq and r['method']==name]
        summary.append({'nq':nq,'method':name,'median_ms':statistics.median(values),
                        'min_ms':min(values),'max_ms':max(values)})
with (OUT/'summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
metadata={'faiss_sq8_direct':{'setup_ms':sq8_setup_ms,'scope':'Exact-byte control only for checked integral 0..255 database and query coordinates; same double oracle.'},'oracle_cache':oracle_metadata,'numpy':np.__version__,'faiss':faiss.__version__,'faiss_compile_options':faiss.get_compile_options(),
          'direct_packed':{'production_method':'direct_auto (mode7)', 'route':'checked lossless byte 1/4/8-query kernels; otherwise fixed25 float kernels or prior float dispatcher', 'selected_route':packed_facts['route'] if packed_facts else None,'storage':packed_facts, 'setup_ms':packed_setup_ms,'compile_command':packed_cmd if packed_handle else None,'note':'Index checks/layout conversion excluded from query timing and separately recorded. Integral coordinates 0..255 and d<=258 use lossless byte SIMD; otherwise direct float squared differences. Query eligibility/encoding included. Both layouts retained for fallback; no BLAS/Faiss search calls.','source_sha256':hashlib.sha256((ROOT/'src/direct_packed.cpp').read_bytes()).hexdigest() if packed_handle else None},
          'openblas_coretype_environment':os.environ.get('OPENBLAS_CORETYPE'),
          'hybrid':{'block':args.hybrid_block,'setup_ms':hybrid_setup_ms,'profile_outside_timing':hybrid_phases,'note':'NumPy BLAS backend may differ from Faiss; library identities recorded in threadpools. Norm preprocessing outside search timing.'},
          'query_indices':query_indices,
          'python':sys.version,'platform':platform.platform(),
          'faiss_default_blas_threshold':faiss.cvar.distance_compute_blas_threshold,
          'dataset':{'kind':'synthetic_integer' if args.synthetic else args.dataset,'n':len(x),'d':x.shape[1],'queries':len(q),'k':k,'seed':20261109,'repeats':args.repeats,'external_gt_checked':gt is not None},
          'threadpools':pools,'affinity':sorted(os.sched_getaffinity(0)),'compile_command':cmd,
          'setup_ms':{'faiss':faiss_setup_ms,'custom':custom_setup_ms},
          'validation':checks,'data_manifest':json.loads((data_dir/'manifest.json').read_text()),
          'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                    [ROOT/'src/benchmark.cpp',ROOT/'src/library.cpp',ROOT/'compare.py',ROOT/'hybrid.py',ROOT/'oracle_cache.py']},
          'timing':'Python calls, output allocation, C++ query copy, search; excludes database construction and input loading',
          'notes':'Different Python bindings add small asymmetric overhead; Faiss ISA dispatch recorded. Both resident databases.'}
(OUT/'environment.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(summary,indent=2)); print('Results:',OUT)
