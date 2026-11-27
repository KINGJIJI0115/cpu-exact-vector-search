"""Extract allowlisted fvecs/ivecs and record source/hash. Local archive is retained."""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request
import shutil
root=Path(__file__).resolve().parent/'data/sift1m';root.mkdir(parents=True,exist_ok=True)
revision='8956d7e088e0b79b6901c234632e801fa37d731d'
url=f'https://huggingface.co/datasets/zjd2000/ANN_SIFT/resolve/{revision}/sift.tar.gz'
archive=root/'sift.tar.gz.part'
if not archive.exists():
    raise FileNotFoundError('完整提交包缺少SIFT1M原始归档，请检查解压内容。')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
expected='92f1270c5e3a0cb46b89983e72b0511e4df065c31a9fa0276d8c9b1fca5bc81a'
if sha(archive)!=expected: raise ValueError('SIFT1M archive checksum mismatch')
with tarfile.open(archive) as tar:
    for name in ['sift_base.fvecs','sift_query.fvecs','sift_groundtruth.ivecs']:
        with tar.extractfile('sift/'+name) as source,(root/name).open('wb') as dest:
            shutil.copyfileobj(source,dest)
manifest={'source':url,'original_source':'ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz',
          'license':'Bundled course workload; provenance and rights notes: DATA_SOURCES.md',
          'sha256':{p.name:sha(p) for p in root.iterdir() if p.suffix in ['.part','.fvecs','.ivecs']}}
(root/'prepared_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
