import os,sys,json,subprocess,time,shutil,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parent
server=Path('/home/ubuntu/hdd2/zxz/vector-search-repro-20261124-01')
if server.exists():
 base=server/'project';python=server/'.venv/bin/python';cpu=19;calcache=Path('/home/ubuntu/hdd2/zxz/vector-search-autotune-20261124-01/.oracle_cache');confirmcache=Path('/home/ubuntu/hdd2/zxz/vector-search-autotune-20261124-01/results/faiss78_confirmation_20261124/.oracle_cache');label='server'
else:
 base=Path('/mnt/d/系统优化/vector-search');python=Path(sys.executable);cpu=0;calcache=Path('/mnt/d/系统优化/vector-search-autotune/.oracle_cache');confirmcache=base/'.oracle_cache';label='local'
out=ROOT/'experiments/v2/runs'/('integrated_'+label);out.mkdir(parents=True,exist_ok=False)
os.sched_setaffinity(0,{cpu});os.nice(15);resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3));subprocess.run(['ionice','-c','3','-p',str(os.getpid())],check=True)
env=os.environ.copy();env.update(PYTHONPATH=str(base/'.deps'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
# Copy oracle files so any cache repair stays inside the new experiment directory.
cache=ROOT/'autotune_v2/.oracle_cache';cache.mkdir(parents=True,exist_ok=True)
for p in calcache.glob('*.npz'):shutil.copy2(p,cache/p.name)
comparebase=out/'base';comparebase.mkdir();(comparebase/'data').symlink_to(base/'data',target_is_directory=True);(comparebase/'.oracle_cache').mkdir()
for p in confirmcache.glob('*.npz'):shutil.copy2(p,comparebase/'.oracle_cache'/p.name)
profile=ROOT/'autotune_v2/profiles'/f'{label}.json'
commands=[('regression',[str(ROOT/'autotune_v2/test_adaptive.py')]),('calibration',[str(ROOT/'autotune_v2/calibrate.py'),'--data',str(base/'data'),'--cpu',str(cpu),'--profile',str(profile),'--force']),('faiss78',[str(ROOT/'autotune_v2/compare_faiss78_portable.py'),'--base',str(comparebase),'--out',str(out/'faiss78'),'--cpu',str(cpu),'--profile',str(profile)]),('cache_reuse',[str(ROOT/'autotune_v2/calibrate.py'),'--data',str(base/'data'),'--cpu',str(cpu),'--profile',str(profile)])]
steps=[]
try:
 for name,args in commands:
  print('RUN',name,flush=True);t=time.monotonic()
  with (out/(name+'.log')).open('w') as log:p=subprocess.run([str(python),*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
  steps.append(dict(step=name,exit=p.returncode,seconds=time.monotonic()-t));(out/'steps.json').write_text(json.dumps(steps,indent=2));print(steps[-1],flush=True)
  if p.returncode:raise RuntimeError(name+' failed')
 (out/'SUCCESS.json').write_text(json.dumps(dict(status='passed',steps=steps,cpu=cpu),indent=2))
except Exception as exc:
 (out/'FAILED.json').write_text(json.dumps(dict(error=str(exc),steps=steps),indent=2));raise
