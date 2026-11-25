"""Prepare normalized float32 L2 vectors; original angular ground truth is not reused."""
import hashlib,json
from pathlib import Path
import h5py,numpy as np
root=Path(__file__).resolve().parent;d=root/'data/glove25';source=d/'glove-25-angular.hdf5'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
manifest=d/'manifest.json'
if manifest.exists():assert json.loads(manifest.read_text())['source_sha256']==digest
info={}
with h5py.File(source,'r') as f:
    for key,name in [('train','base'),('test','query')]:
        x=f[key][:].astype(np.float64);norm=np.linalg.norm(x,axis=1)
        assert np.all(norm>0) and np.isfinite(x).all()
        x=np.ascontiguousarray(x/norm[:,None],dtype=np.float32)
        a=np.empty((len(x),x.shape[1]+1),dtype='<i4');a[:,0]=x.shape[1];a[:,1:]=x.view('<i4')
        path=d/f'glove_{name}.fvecs';a.tofile(path)
        info[name]={'shape':list(x.shape),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
manifest.write_text(json.dumps({'source':'https://ann-benchmarks.com/glove-25-angular.hdf5','source_sha256':digest,'description':'GloVe25 word embeddings; ANN-Benchmarks train/test split. Float64 L2 normalization then float32 storage. Evaluate exact squared L2 on stored floats, not original angular scores; independent double reference recomputed.','h5py':h5py.__version__,'files':info},indent=2))
print(manifest)
