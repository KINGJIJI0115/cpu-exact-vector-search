import hashlib,json,sys
from pathlib import Path
r=Path(__file__).resolve().parent
m=json.loads((r/'MANIFEST.json').read_text(encoding='utf-8'))
bad=[]
for name,wanted in m['files'].items():
 p=r/name
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=wanted:bad.append(name)
print(json.dumps({'checked':len(m['files']),'passed':not bad,'bad':bad},ensure_ascii=False))
sys.exit(bool(bad))
