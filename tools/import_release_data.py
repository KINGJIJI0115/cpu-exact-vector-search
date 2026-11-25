#!/usr/bin/env python3
"""Import only verified workload files from the original course ZIP."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path
EXPECTED = {"eafc6f60aeb814b6b5afd3006d19914728e99378b7a23f34290cf218ee48a39e", "d2b0300179b31ddf915d03d709a379b550d2c000e22867363137f1c90f958cdc"}
def digest_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);a=p.parse_args()
    if digest_file(a.archive) not in EXPECTED:raise SystemExit('Archive SHA256 mismatch: expected a verified original or public course release ZIP')
    root=Path(__file__).resolve().parents[1];target=(root/'baseline/data').resolve()
    with zipfile.ZipFile(a.archive) as z:
        manifest=json.loads(z.read('MANIFEST.json'))['files'];count=0
        for info in z.infolist():
            if not info.filename.startswith('baseline/data/') or info.is_dir():continue
            dest=(root/info.filename).resolve()
            if not dest.is_relative_to(target):raise SystemExit('Unsafe archive path')
            payload=z.read(info)
            if hashlib.sha256(payload).hexdigest()!=manifest.get(info.filename):raise SystemExit('Payload checksum mismatch')
            if dest.exists() and digest_file(dest)!=manifest[info.filename]:raise SystemExit(f'Refusing to overwrite different local file: {dest}')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload);count+=1
    print(f'Imported {count} verified workload files into {target}')
if __name__=='__main__':main()
