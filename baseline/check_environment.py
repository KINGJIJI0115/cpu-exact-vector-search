"""Fail early on unsupported execution environments; never claims cross-CPU performance."""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def assess(facts):
    errors = []
    if facts['system'] != 'Linux':
        errors.append('需要 Linux；Windows 请在 Ubuntu/WSL 内运行，不能直接使用 PowerShell。')
    if facts['machine'].lower() not in ('x86_64', 'amd64'):
        errors.append('当前实现要求 x86-64；ARM/Apple Silicon 无原生兼容路径。')
    if tuple(facts['python_version']) < (3, 10):
        errors.append('需要 Python 3.10 或更新的兼容版本；已验证环境为 Ubuntu 22.04 / Python 3.10。')
    if not facts['allowed_cpus']:
        errors.append('需要 Linux sched_getaffinity，且至少有一个可用逻辑 CPU。')
    missing = sorted({'avx', 'avx2', 'fma'} - set(facts['selected_cpu_flags']))
    if missing:
        errors.append('所选逻辑 CPU 未向操作系统暴露指令集：' + ', '.join(missing) + '。无法运行本版 SIMD 内核。')
    return errors


def collect(root=ROOT, hardware_only=False):
    allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else []
    cpu = {}
    if Path('/proc/cpuinfo').exists():
        for block in Path('/proc/cpuinfo').read_text().split('\n\n'):
            fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line)
            fields = {k.strip(): v.strip() for k, v in fields.items()}
            if allowed and fields.get('processor') == str(allowed[0]):
                cpu = fields
                break
    memory = {}
    if Path('/proc/meminfo').exists():
        memory = {line.split(':')[0]: line.split(':')[1].strip() for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:', 'MemAvailable:'))}
    facts = dict(system=platform.system(), machine=platform.machine(), platform=platform.platform(),
                 python_version=list(sys.version_info[:3]), python=sys.version, cpu_model=cpu.get('model name', 'unknown'),
                 allowed_cpus=allowed, selected_cpu=allowed[0] if allowed else None,
                 selected_cpu_flags=cpu.get('flags', '').split(), memory=memory,
                 free_disk_bytes=shutil.disk_usage(root).free,
                 tested_environment='Ubuntu 22.04 x86-64 / Python 3.10 / AVX2+FMA; other compatible Linux systems are not guaranteed tested',
                 scope='Compatibility preflight only; does not guarantee performance or successful dependency installation.')
    errors = assess(facts)
    if not hardware_only:
        facts['tools'] = {name: shutil.which(name) for name in ('g++', 'nm', 'objdump', 'ldd')}
        errors.extend('缺少工具：' + name for name, path in facts['tools'].items() if not path)
        facts['system_modules'] = {name: importlib.util.find_spec(name) is not None for name in ('z3', 'matplotlib', 'reportlab')}
        errors.extend('缺少系统 Python 模块：' + name for name, found in facts['system_modules'].items() if not found)
        # This isolated child resolves the pinned benchmark packages from .deps.
        import subprocess
        env = os.environ.copy(); env['PYTHONPATH'] = str(root / '.deps')
        code = "import faiss,numpy,threadpoolctl,h5py,importlib.metadata,json; names=['faiss-cpu','numpy','packaging','threadpoolctl','h5py']; print(json.dumps({n:importlib.metadata.version(n) for n in names}))"
        p = subprocess.run([sys.executable, '-c', code], env=env, text=True, capture_output=True)
        facts['benchmark_packages'] = json.loads(p.stdout) if p.returncode == 0 else {}
        if p.returncode:facts['dependency_import_error']=p.stderr[-2000:]
        expected = dict(line.strip().split('==') for line in (root / 'requirements.txt').read_text().splitlines() if '==' in line)
        if facts['benchmark_packages'] != expected:
            errors.append('固定依赖版本不匹配；请使用 bash reproduce.sh 安装 requirements.txt 中的版本。')
        font = os.environ.get('VECTOR_REPORT_FONT')
        fonts = [font] if font else ['/mnt/c/Windows/Fonts/simsun.ttc', '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc']
        if not any(Path(f).is_file() for f in fonts):
            errors.append('缺少中文字体；请安装 fonts-wqy-microhei 或设置 VECTOR_REPORT_FONT。')
    facts['errors'] = errors
    facts['status'] = 'unsupported' if errors else 'passed'
    return facts


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--hardware-only', action='store_true'); ap.add_argument('--json', type=Path); args = ap.parse_args()
    result = collect(hardware_only=args.hardware_only)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True); args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'selected_cpu_flags'}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 2)
