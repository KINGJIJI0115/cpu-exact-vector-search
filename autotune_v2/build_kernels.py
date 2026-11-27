"""Build v2 from preserved v1 sources plus the tested integer-dot transformation."""
from pathlib import Path
import sys,shutil,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'experiments/v2'))
from build_candidates import build as build_candidate

def build():
    folder=ROOT/'build';folder.mkdir(exist_ok=True)
    record=build_candidate(folder/'generated')
    shutil.copy2(folder/'generated/candidate.cpp',ROOT/'src/autotune_kernels.cpp')
    shutil.copy2(folder/'generated/candidate.so',folder/'libautotune.so')
    record.update(compiler=subprocess.check_output(['g++','--version'],text=True),library_sha256=hashlib.sha256((folder/'libautotune.so').read_bytes()).hexdigest(),candidate_modes={'200':{'native':200,'block':128},'201':{'native':200,'block':256},'202':{'native':200,'block':512},'203':{'native':201,'block':256}})
    (folder/'build.json').write_text(json.dumps(record,indent=2));return record
if __name__=='__main__':build()
