from pathlib import Path
import json,csv,statistics,math
ROOT=Path(__file__).resolve().parent

def summarize(folder):
    manifest=json.loads((folder/'manifest.json').read_text());rows=list(csv.DictReader((folder/'summary.csv').open()))
    for r in rows:
        for k in ['gain','custom_ms','best_faiss_ms','gain_over_original']:r[k]=float(r[k])
        r['passed']=r['passed']=='True'
    groups={}
    for dataset in sorted(set(r['dataset'] for r in rows)):
        a=[r for r in rows if r['dataset']==dataset];groups[dataset]=dict(cases=len(a),wins=sum(r['passed'] for r in a),geomean=math.exp(statistics.mean(math.log(r['gain']) for r in a)),minimum=min(r['gain'] for r in a),maximum=max(r['gain'] for r in a))
    configs=[]
    for key in dict.fromkeys((r['dataset'],r['q'],r['k']) for r in rows):
        a=[r for r in rows if (r['dataset'],r['q'],r['k'])==key]
        configs.append(dict(dataset=key[0],q=int(key[1]),k=int(key[2]),wins=sum(r['passed'] for r in a),mode=a[0]['mode'],block=a[0]['block'],custom_ms=statistics.median(r['custom_ms'] for r in a),faiss_ms=statistics.median(r['best_faiss_ms'] for r in a),gain_min=min(r['gain'] for r in a),gain_max=max(r['gain'] for r in a)))
    return dict(manifest=manifest,datasets=groups,configs=configs,slower=[r for r in rows if not r['passed']])
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();s=summarize(a.folder)
    if a.out:a.out.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=s['manifest']['status'],cases=s['manifest']['cases'],passed=s['manifest']['passed'],datasets=s['datasets'],slower=[{'label':r['label'],'gain':r['gain']} for r in s['slower']]),ensure_ascii=False))
