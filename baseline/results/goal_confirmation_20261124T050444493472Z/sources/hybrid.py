"""Experimental blocked NumPy BLAS + C++ candidate merge. No Faiss search calls."""
import ctypes as ct
import time
import numpy as np
from threadpoolctl import threadpool_info

class Hybrid:
    def __init__(self,x,lib):
        self.x=x
        self.norms=np.einsum('ij,ij->i',x,x)
        self.lib=lib
        fp=np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS')
        ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
        lib.vs_merge_tile.argtypes=[fp,fp,fp,ct.c_int,ct.c_int,ct.c_int,ct.c_int,ct.c_int,fp,ip]
        lib.vs_merge_tile.restype=ct.c_int
        self.faiss_blas=None
        for pool in threadpool_info():
            if pool['user_api']=='blas' and 'faiss_cpu.libs' in pool['filepath']:
                self.faiss_blas=ct.CDLL(pool['filepath']).cblas_sgemm
                self.faiss_blas.argtypes=[ct.c_int]*6+[ct.c_float,fp,ct.c_int,fp,ct.c_int,ct.c_float,fp,ct.c_int]
                self.faiss_blas.restype=None

    def search(self,q,k,block=8192,mode=0,profile=None,backend='numpy'):
        start=time.perf_counter()
        nq=len(q)
        ds=np.full((nq,k),np.inf,dtype=np.float32)
        ids=np.full((nq,k),np.iinfo(np.int32).max,dtype=np.int32)
        qn=np.einsum('ij,ij->i',q,q)
        setup=time.perf_counter()-start
        gemm=merge=0.0
        for a in range(0,len(self.x),block):
            t=time.perf_counter() if profile is not None else 0
            xb=self.x[a:a+block]
            if backend=='numpy':dots=q @ xb.T
            else:
                if self.faiss_blas is None:raise RuntimeError('Faiss BLAS symbol unavailable')
                dots=np.empty((nq,len(xb)),dtype=np.float32)
                self.faiss_blas(101,111,112,nq,len(xb),q.shape[1],1.0,q,q.shape[1],xb,q.shape[1],0.0,dots,len(xb))
            if profile is not None:gemm+=time.perf_counter()-t;t=time.perf_counter()
            assert self.lib.vs_merge_tile(dots,self.norms[a:a+block],qn,nq,dots.shape[1],a,k,mode,ds,ids)==0
            if profile is not None:merge+=time.perf_counter()-t
        if profile is not None:profile.update(setup_ms=setup*1000,gemm_ms=gemm*1000,merge_ms=merge*1000)
        return ds,ids
