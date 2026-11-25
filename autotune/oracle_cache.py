"""Content-addressed, untimed float64 oracle cache; never caches search results.

Keys include every database/query byte, the algorithm source and NumPy version.
Files are disposable: a missing/invalid cache is recomputed by exhaustive L2.
"""
import hashlib,json,zipfile,zlib
from pathlib import Path
import numpy as np

def exact_oracles(x,queries,k,ground_truth,root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    database_hash=hashlib.sha256(memoryview(x).cast('B')).hexdigest()
    algorithm_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    cap=min(len(x),max(1000,k));ds=[];ids=[];hits=0
    for qi,query in enumerate(queries):
        identity=dict(database=database_hash,shape=list(x.shape),dtype=x.dtype.str,query=hashlib.sha256(query.tobytes()).hexdigest(),cap=cap,algorithm=algorithm_hash,numpy=np.__version__)
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();file=root/(key+'.npz');cached=False
        if file.exists():
            try:
                with np.load(file,allow_pickle=False) as z:
                    values=z['distances'];order=z['ids'];stored=str(z['checksum']);saved=json.loads(str(z['identity']))
                checksum=hashlib.sha256(values.tobytes()+order.tobytes()).hexdigest()
                cached=(saved==identity and checksum==stored and values.shape==(cap,) and order.shape==(cap,) and values.dtype==np.float64 and order.dtype==np.int64 and np.all(order>=0) and np.all(order<len(x)) and np.all(values[:-1]<=values[1:]))
            except (ValueError,OSError,KeyError,EOFError,zipfile.BadZipFile,zlib.error):cached=False
        if not cached:
            dist=np.empty(len(x),np.float64)
            for begin in range(0,len(x),8192):
                delta=x[begin:begin+8192].astype(np.float64)-query.astype(np.float64)
                dist[begin:begin+8192]=np.einsum('ij,ij->i',delta,delta)
            order=np.lexsort((np.arange(len(x)),dist))[:cap].astype(np.int64);values=dist[order]
            checksum=hashlib.sha256(values.tobytes()+order.tobytes()).hexdigest()
            np.savez(file,distances=values,ids=order,checksum=checksum,identity=json.dumps(identity,sort_keys=True))
        else:hits+=1
        if ground_truth is not None:
            external_k=min(k,ground_truth.shape[1]);external=x[ground_truth[qi,:external_k]].astype(np.float64)-query.astype(np.float64)
            external_distance=np.einsum('ij,ij->i',external,external)
            np.testing.assert_array_equal(np.sort(external_distance),values[:external_k])
        ds.append(values[:k]);ids.append(order[:k])
    return np.array(ds),np.array(ids),dict(cache_hits=hits,queries=len(queries),database_sha256=database_hash,algorithm_sha256=algorithm_hash,scope='Untimed independent exhaustive float64 reference; data/content-addressed. Search methods always execute.')
