#!/usr/bin/env python3
"""Import verified workload files from a course release ZIP into baseline/data/."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path, help='Path to the complete course submission/release ZIP')
    p.add_argument('--expected-sha256', default=None, help='Optional expected SHA256 of the ZIP archive')
    a = p.parse_args()

    if a.expected_sha256:
        actual = digest_file(a.archive)
        if actual.lower() != a.expected_sha256.lower():
            raise SystemExit(f'Archive SHA256 mismatch: expected {a.expected_sha256}, got {actual}')

    root = Path(__file__).resolve().parents[1]
    target = (root / 'baseline/data').resolve()
    local_data_manifest = root / 'DATA_MANIFEST.json'
    expected_workloads = {}
    if local_data_manifest.is_file():
        dm = json.loads(local_data_manifest.read_text(encoding='utf-8'))
        for item in dm.get('files', []):
            if isinstance(item, dict) and 'path' in item and 'sha256' in item:
                expected_workloads[item['path']] = item['sha256']

    with zipfile.ZipFile(a.archive) as z:
        manifest = json.loads(z.read('MANIFEST.json'))['files']
        count = 0
        for info in z.infolist():
            if not info.filename.startswith('baseline/data/') or info.is_dir():
                continue
            dest = (root / info.filename).resolve()
            if not dest.is_relative_to(target):
                raise SystemExit('Unsafe archive path')
            payload = z.read(info)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != manifest.get(info.filename):
                raise SystemExit(f'Payload checksum mismatch vs archive MANIFEST: {info.filename}')
            if info.filename in expected_workloads and digest != expected_workloads[info.filename]:
                raise SystemExit(f'Payload checksum mismatch vs local DATA_MANIFEST: {info.filename}')
            if dest.exists() and digest_file(dest) != digest:
                raise SystemExit(f'Refusing to overwrite different local file: {dest}')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
            count += 1
    if count == 0:
        raise SystemExit('No workload files found under baseline/data/ in archive')
    print(f'Imported {count} verified workload files into {target}')


if __name__ == '__main__':
    main()
