import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
ROOT=Path(__file__).resolve().parent
out=ROOT/'results'/('profile_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
out.mkdir(parents=True)
cmd=['g++','-std=c++17','-O3','-mavx2','-ffp-contract=off',str(ROOT/'src/profile.cpp'),'-o',str(ROOT/'build/profile')]
subprocess.run(cmd,check=True)
result=subprocess.run([str(ROOT/'build/profile'),str(ROOT/'data/siftsmall_base.fvecs'),str(ROOT/'data/siftsmall_query.fvecs')],check=True,capture_output=True,text=True)
(out/'raw.csv').write_text(result.stdout)
rows=list(csv.DictReader(result.stdout.splitlines()))
summary=[]
for mask in ['0','1','5','7']:
    selected=[r for r in rows if r['variant']==mask]
    item={'variant':mask}
    for key in ['allocation_ms','distance_ms','selection_ms']:
        item[key]=statistics.median(float(r[key]) for r in selected)
    summary.append(item)
meta={'compile_command':cmd,'affinity':sorted(os.sched_getaffinity(0)),
      'perf_executable':shutil.which('perf'),'cpu_pmu_present':any(p.name in ['cpu','cpu_core','cpu_atom'] for p in Path('/sys/bus/event_source/devices').iterdir()),
      'peak_rss_kib':max(int(r['process_peak_rss_kib']) for r in rows),
      'note':'RSS is cumulative process high-water mark across variants, not per-variant allocation. Instrumented stages exclude cleanup and driver.',
      'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/profile.cpp',ROOT/'src/benchmark.cpp']}}
p=Path('/proc/sys/kernel/perf_event_paranoid')
meta['perf_event_paranoid']=p.read_text().strip() if p.exists() else None
(out/'environment.json').write_text(json.dumps(meta,indent=2))
(out/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2));print(json.dumps(meta,indent=2));print(out)
