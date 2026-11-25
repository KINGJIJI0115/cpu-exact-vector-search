"""Five disjoint real-query batches; matched methods, fixed seed, raw provenance."""
import csv,datetime,json,os,random,statistics,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'results'/('representative_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
out.mkdir(parents=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
env=os.environ.copy();env['PYTHONPATH']=str(root/'.deps')
indices=random.Random(20261114).sample(range(32,10000),160)
rows=[];runs=[]
for batch in range(5):
    path=out/f'indices_{batch}.json'
    path.write_text(json.dumps(indices[batch*32:(batch+1)*32]))
    print('Batch',batch+1,'/ 5',flush=True)
    cmd=[sys.executable,str(root/'compare.py'),'--dataset','sift1m','--queries','32','--k','10','--repeats','5','--methods','custom_all,stream_all,faiss_flat,faiss_blas','--query-indices',str(path)]
    p=subprocess.run(cmd,env=env,text=True,capture_output=True)
    (out/f'batch_{batch}.log').write_text(p.stdout+p.stderr)
    p.check_returncode()
    folder=Path(p.stdout.strip().split('Results: ')[-1])
    meta=json.loads((folder/'environment.json').read_text())
    assert meta['query_indices']==indices[batch*32:(batch+1)*32]
    assert meta['dataset']['external_gt_checked'] and all(x['correct'] for x in meta['validation'])
    runs.append(str(folder.relative_to(root)))
    for row in csv.DictReader((folder/'summary.csv').open()):
        rows.append({'batch':batch,**row,'derived_queries_per_second':32000/float(row['median_ms'])})
with (out/'batch_medians.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary=[]
for method in ['custom_all','stream_all','faiss_flat','faiss_blas']:
    values=[float(r['median_ms']) for r in rows if r['method']==method]
    summary.append({'method':method,'median_ms':statistics.median(values),'min_batch_median_ms':min(values),'max_batch_median_ms':max(values),'derived_queries_per_second':32000/statistics.median(values)})
with (out/'summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
(out/'manifest.json').write_text(json.dumps({'seed':20261114,'population':'SIFT1M query indices 32..9999; excludes original first32','batches':5,'queries_per_batch':32,'repeats':5,'k':10,'runs':runs,'affinity':sorted(os.sched_getaffinity(0)),'note':'Batch medians vary in both query contents and process/time. Ranges are descriptive, not confidence intervals.'},indent=2))
print(json.dumps(summary,indent=2));print(out,flush=True)
