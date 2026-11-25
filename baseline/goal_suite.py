"""Resumable full-scope screen/confirmation with frozen source hashes."""
import argparse,csv,datetime,hashlib,json,os,random,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['baseline','confirmation'],default='baseline');ap.add_argument('--resume',type=Path);a=ap.parse_args()
scope=json.loads((r/'goal_scope.json').read_text());out=a.resume.resolve() if a.resume else r/'results'/('goal_'+a.stage+'_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(parents=True,exist_ok=True)
names=['compare.py','hybrid.py','src/direct_packed.cpp','src/library.cpp','src/benchmark.cpp','goal_scope.json','goal_suite.py','oracle_cache.py']
def hashes():return {n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in names}
if (out/'manifest.json').exists():
 manifest=json.loads((out/'manifest.json').read_text());assert manifest['source_hashes']==hashes();assert manifest['stage']==a.stage
else:
 manifest={'status':'running','stage':a.stage,'source_hashes':hashes(),'scope':scope}
 for name in names:
  dst=out/'sources'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((r/name).read_bytes())
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
seed=scope['baseline_seed'] if a.stage=='baseline' else scope['confirmation_seed'];batches=1 if a.stage=='baseline' else scope['confirmation_batches']
training_indices=random.Random(scope['baseline_seed']).sample(range(128,10000),256)
pool=[i for i in range(128,10000) if a.stage=='baseline' or i not in set(training_indices)]
indices=random.Random(seed).sample(pool,256*batches)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});env=os.environ.copy();env['PYTHONPATH']=str(r/'.deps');env['OPENBLAS_CORETYPE']='Haswell'
runs=json.loads((out/'runs.json').read_text()) if (out/'runs.json').exists() else []
rows=list(csv.DictReader((out/'partial.csv').open())) if (out/'partial.csv').exists() else []
ratios=json.loads((out/'ratios.json').read_text()) if (out/'ratios.json').exists() else []
for dataset,q,k in scope['configs']:
 for batch in range(batches):
  label=f'{dataset}_q{q}_k{k}_b{batch}'
  if any(x['label']==label for x in runs):continue
  assert hashes()==manifest['source_hashes'],'Source changed during measurement'
  print(f'{len(runs)+1}/{len(scope["configs"])*batches} {label}',flush=True)
  idx=out/(label+'_indices.json');idx.write_text(json.dumps(indices[batch*256:batch*256+q]))
  cmd=[sys.executable,str(r/'compare.py'),'--dataset',dataset,'--queries',str(q),'--k',str(k),'--repeats',str(scope['repeats']),'--methods',','.join(['direct_auto']+scope['faiss_methods'][dataset]),'--query-indices',str(idx)]
  p=subprocess.run(cmd,env=env,text=True,capture_output=True);(out/(label+'.log')).write_text(p.stdout+p.stderr);p.check_returncode()
  f=Path(p.stdout.strip().split('Results: ')[-1]);meta=json.loads((f/'environment.json').read_text());assert hashes()==manifest['source_hashes']
  assert meta['dataset']['n']==scope['datasets'][dataset]['n'];assert all(c['correct'] for c in meta['validation'])
  vals=list(csv.DictReader((f/'summary.csv').open()));times={x['method']:float(x['median_ms']) for x in vals};best=min(scope['faiss_methods'][dataset],key=times.get)
  ratio={'label':label,'dataset':dataset,'q':q,'k':k,'batch':batch,'custom_ms':times['direct_auto'],'best_faiss_method':best,'best_faiss_ms':times[best],'ratio':times['direct_auto']/times[best]}
  ratio['pass']=ratio['ratio']<=1;ratios.append(ratio)
  runs.append({'label':label,'folder':f.relative_to(r).as_posix()});rows.extend({'dataset':dataset,'q':q,'k':k,'batch':batch,**x} for x in vals)
  (out/'runs.json').write_text(json.dumps(runs,indent=2));(out/'ratios.json').write_text(json.dumps(ratios,indent=2))
  with (out/'partial.csv').open('w',newline='') as ff:
   w=csv.DictWriter(ff,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  print(f'  custom/Faiss={ratio["ratio"]:.4f}; best={best}',flush=True)
(out/'summary.csv').write_bytes((out/'partial.csv').read_bytes());manifest.update(status='completed',completed_cases=len(runs),passed_cases=sum(x['pass'] for x in ratios),all_cases_pass=all(x['pass'] for x in ratios));(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print(out)
