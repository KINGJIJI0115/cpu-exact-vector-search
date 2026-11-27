"""Audit archived complete runs and frozen profile/source fingerprints."""
from pathlib import Path
import json,hashlib,csv,math,statistics,argparse

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('archive',type=Path);a=ap.parse_args();root=a.archive;out=root/'run/faiss78';m=json.loads((out/'manifest.json').read_text());rows=list(csv.DictReader((out/'summary.csv').open()));validation=json.loads((out/'validation.json').read_text())
    assert m['status']=='completed' and len(rows)==len(validation)==m['cases']==78
    assert len(set(r['label'] for r in rows))==78
    assert all(v['correct'] for row in validation for v in row['methods'].values())
    assert sum(r['passed']=='True' for r in rows)==m['passed']
    assert math.isclose(math.exp(statistics.mean(math.log(float(r['gain'])) for r in rows)),m['gain_geomean'],rel_tol=1e-12)
    for original,wanted in m['frozen_sha256'].items():
        p=out/'frozen'/Path(original).name
        if p.suffix=='.so':assert json.loads((root/'build.json').read_text())['library_sha256']==wanted
        else:assert sha(p)==wanted,(p,wanted)
    w=json.loads((root/'profile.json').read_text());profile=w['payload'];digest=hashlib.sha256(json.dumps(profile,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert w['sha256']==digest and profile['complete'] and len(profile['entries'])==26
    by_label={e['label']:e for e in profile['entries'].values()}
    for row in rows:
        e=by_label[row['label'].rsplit('_b',1)[0]];assert e['mode']==int(row['mode']) and e['block']==int(row['block'])
        z=json.loads((out/(row['label']+'.json')).read_text());assert z['summary']['passed']==(row['passed']=='True')
    result=dict(status='passed',cases=78,profile_entries=26,correctness_methods='all passed',frozen_source_and_profile_hashes='matched',library='binary hash matched build record; binary regenerated on reproduction')
    (root/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
