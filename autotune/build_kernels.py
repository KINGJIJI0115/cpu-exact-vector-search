"""Generate a separate candidate library; the preserved production source is immutable."""
from pathlib import Path
import hashlib, json, subprocess
ROOT=Path(__file__).resolve().parent
FLAGS=['-std=c++17','-O3','-mavx2','-mfma','-ffp-contract=off','-shared','-fPIC']
def build():
    original=(ROOT/'src/original_packed.cpp').read_text()
    assert hashlib.sha256((ROOT/'src/original_packed.cpp').read_bytes()).hexdigest()=='e058d712dae1f944859299ec957c56411f0f761453918341e9bab7e10296dda4'
    extra=''
    for mode,fn,r,s in [(100,'byte_search',1,4),(101,'byte_search',2,4),(102,'byte_search',4,2),(103,'byte_search',8,1),(110,'byte128_search',1,4),(111,'byte128_search',2,4),(112,'byte128_search',4,2),(113,'byte128_search',8,1),(120,'fixed25_search',1,4),(121,'fixed25_search',8,1)]:
        extra+=f'        if(mode=={mode})return {fn}<{r},{s}>(p,q,nq,k,block,ds,ids);\n'
    needle='        if(mode==7){';assert original.count(needle)==1
    generated=original.replace(needle,extra+needle)
    source=ROOT/'src/autotune_kernels.cpp';source.write_text(generated)
    folder=ROOT/'build';folder.mkdir(exist_ok=True)
    library=folder/'libautotune.so';tmp=folder/'libautotune.tmp.so'
    subprocess.run(['g++',*FLAGS,str(source),'-o',str(tmp)],check=True)
    tmp.replace(library)
    symbols=subprocess.check_output(['nm','-D',str(library)],text=True)
    assert not any(word in symbols.lower() for word in ['sgemm','cblas','faiss'])
    record=dict(flags=FLAGS,compiler=subprocess.check_output(['g++','--version'],text=True),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),library_sha256=hashlib.sha256(library.read_bytes()).hexdigest())
    (folder/'build.json').write_text(json.dumps(record,indent=2));return record
if __name__=='__main__':build()
