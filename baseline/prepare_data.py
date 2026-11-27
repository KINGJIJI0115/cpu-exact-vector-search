"""Fetch original SIFT small archive; extract only three explicitly named files."""
import hashlib
import json
import pathlib
import tarfile
import urllib.request
ROOT=pathlib.Path(__file__).resolve().parent/'data'
ROOT.mkdir(exist_ok=True)
url='https://huggingface.co/datasets/vecdata/siftsmall/resolve/3106e1b83049c44713b1ce06942d0ab474bbdfb6/siftsmall.tar.gz'
archive=ROOT/'mirror.tar.gz'
if not archive.exists():
    raise FileNotFoundError('完整提交包缺少SIFTsmall原始归档，请检查解压内容。')
expected='987b526d24e749082ba27ee8068003836eb17a61b34f09b4db865750f8a43487'
if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
    raise ValueError('Archive checksum mismatch; do not extract')
with tarfile.open(archive) as tar:
    for name in ['siftsmall_base.fvecs','siftsmall_query.fvecs','siftsmall_groundtruth.ivecs']:
        member=tar.getmember('siftsmall/'+name)
        (ROOT/name).write_bytes(tar.extractfile(member).read())
manifest={'source':url,'original_source':'ftp://ftp.irisa.fr/local/texmex/corpus/siftsmall.tar.gz', 'description':'SIFT small: image descriptors; 10000 base, 100 query, 128 dimensions',
          'license':'Bundled course workload; provenance and rights notes: DATA_SOURCES.md',
          'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.iterdir() if p.is_file() and p.name!='manifest.json'}}
(ROOT/'prepared_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
