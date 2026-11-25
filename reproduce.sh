#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/baseline"
if ! command -v python3 >/dev/null; then
  echo '需要 Python 3.10+；请先在 Ubuntu/WSL 中安装 python3。' >&2
  exit 2
fi
if [[ "${1:-}" == '--check-env' ]]; then
  exec env -u PYTHONPATH python3 check_environment.py
fi
if [[ "${1:-}" == '--help' || "${1:-}" == '-h' ]]; then
  echo '额外选项：--check-env 只检查环境，不安装依赖。'
  exec env -u PYTHONPATH python3 ../reproduce_autotune.py --help
fi
env -u PYTHONPATH python3 check_environment.py --hardware-only
if ! command -v g++ >/dev/null || ! command -v nm >/dev/null || ! command -v objdump >/dev/null || ! env -u PYTHONPATH python3 -c 'import pip, z3, matplotlib, reportlab' >/dev/null 2>&1; then
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update
    apt-get install -y --no-install-recommends g++ binutils python3-pip python3-z3 python3-matplotlib python3-reportlab poppler-utils
  else
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends g++ binutils python3-pip python3-z3 python3-matplotlib python3-reportlab poppler-utils
  fi
fi
if [ ! -f /mnt/c/Windows/Fonts/simsun.ttc ] && [ ! -f /usr/share/fonts/truetype/wqy/wqy-microhei.ttc ] && [ -z "${VECTOR_REPORT_FONT:-}" ]; then
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update
    apt-get install -y --no-install-recommends fonts-wqy-microhei
  else
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends fonts-wqy-microhei
  fi
fi
if ! PYTHONPATH=.deps python3 -c 'import faiss,numpy,threadpoolctl,h5py,importlib.metadata as m; from pathlib import Path; assert all(m.version(n)==v for n,v in (line.strip().split("==") for line in Path("requirements.txt").read_text().splitlines() if "==" in line))' >/dev/null 2>&1; then
  env -u PYTHONPATH python3 -m pip install --upgrade --target .deps -r requirements.txt
fi
exec env -u PYTHONPATH python3 ../reproduce_autotune.py "$@"
