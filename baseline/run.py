"""Run under Linux/WSL: python3 run.py [--full]. Standard library only."""
import csv
import datetime
import io
import json
import pathlib
import platform
import statistics
import subprocess
import sys
import hashlib

ROOT = pathlib.Path(__file__).resolve().parent
BUILD = ROOT / 'build'
BUILD.mkdir(exist_ok=True)
OUT = ROOT / 'results' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT.mkdir(parents=True)
flags = ['-std=c++17', '-O3', '-mavx2', '-ffp-contract=off', '-fno-tree-vectorize']
if '--auto' in sys.argv:
    flags.remove('-fno-tree-vectorize')
cmd = ['g++', *flags, str(ROOT / 'src/benchmark.cpp'), '-o', str(BUILD / 'benchmark')]
subprocess.run(cmd, check=True)
def capture(args):
    p = subprocess.run(args, text=True, capture_output=True)
    return {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
environment = {'platform': platform.platform(), 'compile_command': cmd,
               'compiler': capture(['g++', '--version']), 'cpu': capture(['lscpu']),
               'seed': 20261109, 'data': 'synthetic uniform; no real dataset claims'}
environment['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/benchmark.cpp',ROOT/'run.py']}
environment['affinity']=capture(['taskset','-pc',str(__import__('os').getpid())])
extra=[]
if '--real' in sys.argv:
    extra=[str(ROOT/'data/siftsmall_base.fvecs'),str(ROOT/'data/siftsmall_query.fvecs')]
    environment['data']=json.loads((ROOT/'data/manifest.json').read_text())
(OUT / 'environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
# Boundary dimensions, SIMD tail, K=N, and non-divisible tiles.
for case in [(1,1,1,1), (17,3,7,17), (37,9,13,5), (64,8,16,1)]:
    subprocess.run([str(BUILD / 'benchmark'), *map(str, case), '1', '11'], check=True, stdout=subprocess.DEVNULL)
subprocess.run([str(BUILD/'benchmark'),'37','9','13','5','1','11','--duplicates'],check=True,stdout=subprocess.DEVNULL)
cases = [(10000,32,128,10,5,256), (50000,32,128,10,5,256)]
if '--full' in sys.argv:
    cases = [(n,q,d,10,7,b) for n in [10000,100000] for q in [1,32]
             for d in [64,128,384] for b in [64,256,1024]]
if '--real' in sys.argv:
    cases=[(10000,q,128,10,7,b) for q in [1,32,100] for b in [64,256,1024]]
rows=[]
for case in cases:
    print('Running', case, flush=True)
    p=subprocess.run([str(BUILD / 'benchmark'), *map(str,case),*extra], check=True, text=True, capture_output=True)
    (OUT / ('raw_'+'_'.join(map(str,case))+'.csv')).write_text(p.stdout)
    rows.extend(csv.DictReader(io.StringIO(p.stdout)))
groups={}
for r in rows:
    key=tuple(r[c] for c in ['n','nq','d','k','block','variant'])
    groups.setdefault(key,[]).append(float(r['ms']))
with (OUT/'summary.csv').open('w', newline='') as f:
    w=csv.writer(f)
    w.writerow(['n','nq','d','k','block','variant','median_ms','min_ms','max_ms','speedup'])
    for key,values in groups.items():
        base=statistics.median(groups[key[:-1]+('0',)])
        w.writerow([*key, statistics.median(values), min(values), max(values),base/statistics.median(values)])
print('Validated all cases. Results:',OUT)
