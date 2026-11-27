"""Full SIFTsmall functional regression for the new public wrapper (no timing claim)."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
import argparse,json
from pathlib import Path
import numpy as np
from adaptive import AdaptiveIndex,DOT_MODES,candidates
from calibrate import load_vectors,verify

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cpu',type=int,default=0);a=p.parse_args();os.sched_setaffinity(0,{a.cpu})
    x=load_vectors(a.data/'siftsmall_base.fvecs');q=load_vectors(a.data/'siftsmall_query.fvecs');rows=[]
    with AdaptiveIndex(x) as index:
        dist=np.array([np.sum((x.astype('float64')-v.astype('float64'))**2,axis=1) for v in q])
        order=np.array([np.lexsort((np.arange(len(x)),row))[:100] for row in dist]);ds=np.take_along_axis(dist,order,axis=1)
        for nq in [1,8,32,len(q)]:
            for k in [1,10,100]:
                for mode in [7]+[m for m in DOT_MODES if m in candidates('byte',index.d,nq)]:
                    check=verify(index,q[:nq],k,index.forced(q[:nq],k,mode),(ds[:nq,:k],order[:nq,:k]));rows.append(dict(q=nq,k=k,mode=mode,**check))
    result=dict(status='passed',dataset='siftsmall',n=len(x),d=x.shape[1],queries=len(q),cases=len(rows),checks=rows)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()
