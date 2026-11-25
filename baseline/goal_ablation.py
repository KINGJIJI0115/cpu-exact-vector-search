"""Forced-kernel ablation; verify the selected bodies match the official source."""
import csv,datetime,hashlib,io,json,os,random,re,statistics,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent;out=r/'results'/('goal_ablation_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
main=(r/'src/direct_packed.cpp').read_text();candidate=(r/'src/goal_smallbyte.cpp').read_text();equivalence={}
for name in ['byte128_search','fixed25_search']:
 pattern=r'template<int R,int S> int '+name+r'\([^\n]*\)\s*\{[\s\S]*?\n}\n'
 a=re.search(pattern,main).group();b=re.search(pattern,candidate).group();assert a==b,name
 equivalence[name]=hashlib.sha256(a.encode()).hexdigest()
scope=json.loads((r/'goal_scope.json').read_text());indices=random.Random(scope['baseline_seed']).sample(range(128,10000),256);rows=[];runs=[]
env=os.environ.copy();env['PYTHONPATH']=str(r/'.deps');env['OPENBLAS_CORETYPE']='Haswell';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
# Real SIFTsmall layered baseline, with compiler auto-vectorization left enabled.
compile_cmd=['g++','-std=c++17','-O3','-mavx2','-mfma','-ffp-contract=off',str(r/'src/benchmark.cpp'),'-o',str(r/'build/benchmark_ablation')]
subprocess.run(compile_cmd,check=True)
cmd=[str(r/'build/benchmark_ablation'),'10000','32','128','10','7','256',str(r/'data/siftsmall_base.fvecs'),str(r/'data/siftsmall_query.fvecs')]
p=subprocess.run(cmd,text=True,capture_output=True);(out/'internal_raw.csv').write_text(p.stdout);(out/'internal_stderr.log').write_text(p.stderr);p.check_returncode()
internal=list(csv.DictReader(io.StringIO(p.stdout)));assert all(v['topk_match']=='1' for v in internal)
summaries=[dict(variant=variant,median_ms=statistics.median(float(v['ms']) for v in internal if int(v['variant'])==variant)) for variant in sorted({int(v['variant']) for v in internal})]
with (out/'internal_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
(out/'internal_environment.json').write_text(json.dumps(dict(dataset='SIFTsmall real descriptors',n=10000,q=32,d=128,k=10,repeats=7,compile_command=compile_cmd,command=cmd,source_sha256=hashlib.sha256((r/'src/benchmark.cpp').read_bytes()).hexdigest(),data_manifest=json.loads((r/'data/manifest.json').read_text())),indent=2))
for dataset,q,k,modes in [('sift1m',1,100,[7,16,22]),('sift1m',128,100,[7,18,25]),('glove25',128,10,[7,13,20])]:
 label=f'{dataset}_q{q}_k{k}';idx=out/(label+'_indices.json');idx.write_text(json.dumps(indices[:q]));methods=[f'direct_packed_m{i}' for i in modes]+scope['faiss_methods'][dataset]
 print(label,flush=True);cmd=[sys.executable,str(r/'goal_smallbyte_compare.py'),'--dataset',dataset,'--queries',str(q),'--k',str(k),'--repeats','7','--methods',','.join(methods),'--query-indices',str(idx)]
 p=subprocess.run(cmd,env=env,text=True,capture_output=True);(out/(label+'.log')).write_text(p.stdout+p.stderr);p.check_returncode();folder=Path(p.stdout.strip().split('Results: ')[-1]);vals=list(csv.DictReader((folder/'summary.csv').open()))
 rows.extend(dict(dataset=dataset,q=q,k=k,**v) for v in vals);runs.append(dict(label=label,folder=folder.relative_to(r).as_posix()))
with (out/'summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'runs.json').write_text(json.dumps(runs,indent=2));(out/'manifest.json').write_text(json.dumps(dict(status='passed',main_source_sha256=hashlib.sha256((r/'src/direct_packed.cpp').read_bytes()).hexdigest(),identical_function_bodies=equivalence,note='Forced component kernels; same selected function bodies as production. Final dispatcher performance is established separately by 78-case confirmation.'),indent=2));print(out)
