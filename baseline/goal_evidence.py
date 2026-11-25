"""Recompute the acceptance decision from raw timings and frozen provenance."""
import csv,hashlib,json,math,random,statistics
from pathlib import Path

def load_verified(root, confirmation=None, require_target=False):
 r=Path(root).resolve();current=hashlib.sha256((r/'src/direct_packed.cpp').read_bytes()).hexdigest();matches=[]
 if confirmation is not None:confirmation=(r/confirmation).resolve()
 files=sorted((r/'results').glob('goal_confirmation_*/manifest.json')) if confirmation is None else [Path(confirmation)/'manifest.json']
 for file in files:
  m=json.loads(file.read_text())
  if m.get('status')=='completed' and m.get('source_hashes',{}).get('src/direct_packed.cpp')==current:matches.append((file,m))
 assert matches,'No completed confirmation for current source';file,m=matches[-1];out=file.parent;scope=m['scope']
 assert m['status']=='completed' and m['completed_cases']==78
 for name,digest in m['source_hashes'].items():
  assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest,'Changed frozen input: '+name
  assert hashlib.sha256((out/'sources'/name).read_bytes()).hexdigest()==digest,'Changed source snapshot: '+name
 assert scope==json.loads((r/'goal_scope.json').read_text())
 runs=json.loads((out/'runs.json').read_text());ratios=json.loads((out/'ratios.json').read_text());stored={v['label']:v for v in ratios}
 expected={(dataset,q,k,batch) for dataset,q,k in scope['configs'] for batch in range(3)};seen=set();checks=[];metas=[];rebuilt=[]
 training=set(random.Random(scope['baseline_seed']).sample(range(128,10000),256));pool=[i for i in range(128,10000) if i not in training];indices=random.Random(scope['confirmation_seed']).sample(pool,768)
 assert len(set(indices))==768 and not set(indices)&training
 for run in runs:
  ratio=stored[run['label']];dataset,q,k,batch=(ratio[x] for x in ['dataset','q','k','batch']);case=(dataset,q,k,batch);assert case in expected and case not in seen;seen.add(case)
  folder=r/run['folder'];meta=json.loads((folder/'environment.json').read_text());raw=list(csv.DictReader((folder/'raw.csv').open()));summary=list(csv.DictReader((folder/'summary.csv').open()))
  assert meta['query_indices']==indices[batch*256:batch*256+q]
  assert meta['dataset']['n']==scope['datasets'][dataset]['n'] and meta['dataset']['d']==scope['datasets'][dataset]['d'] and meta['dataset']['queries']==q and meta['dataset']['k']==k
  assert meta['direct_packed']['source_sha256']==current and len(meta['affinity'])==1 and meta['openblas_coretype_environment']=='Haswell'
  assert all(v['num_threads']==1 for v in meta['threadpools'])
  methods=['direct_auto']+scope['faiss_methods'][dataset];assert set(v['method'] for v in raw)==set(methods)
  times={}
  for method in methods:
   values=[float(v['ms']) for v in raw if v['method']==method];assert len(values)==7 and all(math.isfinite(v) and v>0 for v in values)
   assert {int(v['repeat']) for v in raw if v['method']==method}==set(range(7))
   times[method]=statistics.median(values);reported=next(float(v['median_ms']) for v in summary if v['method']==method);assert math.isclose(times[method],reported,abs_tol=1e-9)
  best=min(scope['faiss_methods'][dataset],key=times.get);value=times['direct_auto']/times[best];assert math.isclose(value,ratio['ratio'],rel_tol=1e-12)
  assert ratio['pass']==(value<=1.0),'Stored performance decision differs from raw timings'
  assert ratio['best_faiss_method']==best and math.isclose(ratio['custom_ms'],times['direct_auto'],abs_tol=1e-9) and math.isclose(ratio['best_faiss_ms'],times[best],abs_tol=1e-9)
  assert all(v['correct'] for v in meta['validation']) and set(v['method'] for v in meta['validation'])==set(methods)
  for v in meta['validation']:
   if dataset=='sift1m' and v['method']=='direct_auto':assert v['strict_id_matches']==v['total_ids'] and v['max_absolute_distance_error']==0 and v['max_rank_distance_gap']==0
   checks.append(dict(dataset=dataset,q=q,k=k,batch=batch,**v))
  rebuilt.append(dict(ratio,ratio=value));metas.append(meta)
 assert seen==expected and len(runs)==len(ratios)==78
 for dataset in ['sift1m','glove25']:
  assert len({v['oracle_cache']['database_sha256'] for v in metas if v['dataset']['kind']==dataset})==1
 passed=sum(x['ratio']<=1.0 for x in rebuilt)
 assert m['passed_cases']==passed and m['all_cases_pass']==(passed==len(seen))
 if require_target:assert passed==len(seen),'Evidence is valid, but the all-cases performance target was not met'
 return dict(folder=out,manifest=m,ratios=rebuilt,checks=checks,metas=metas,source_sha256=current,verified_raw_cases=len(seen),performance_passed_cases=passed,performance_target_met=passed==len(seen))

if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--confirmation',type=Path);ap.add_argument('--require-performance-target',action='store_true');a=ap.parse_args()
 r=Path(__file__).resolve().parent;v=load_verified(r,a.confirmation);result=dict(status='passed',cases=v['verified_raw_cases'],performance_passed_cases=v['performance_passed_cases'],performance_target_met=v['performance_target_met'],source_sha256=v['source_sha256'],confirmation=str(v['folder'].relative_to(r)),worst_ratio=max(x['ratio'] for x in v['ratios']),checks='Raw medians, complete grid, all applicable Faiss controls, source hashes, query split, single threads, exact SIFT IDs/distances, validation records')
 (v['folder']/'evidence_verified.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 if a.require_performance_target and not v['performance_target_met']:raise SystemExit(3)
