# v2 复现指南与分步执行说明

作者：赵信喆（`51295903131`）｜默认流水线：`autotune_v2`

## 1. 一键复现入口

在支持 AVX2/FMA 的 Linux x86-64 或 Windows WSL2 环境中进入解压根目录：

```bash
python3 verify_bundle.py
bash reproduce.sh --check-env
bash reproduce.sh --quick
bash reproduce.sh
```

常用参数与模式说明：
- `--check-env`：仅执行环境预检（GCC、AVX2/FMA、Python 依赖与 CPU 绑核检查），不改动环境。
- `--quick`：执行编译、4 组集成回归、三组 Z3 形式化验证（36 项 Top-K + 4 项字节算术 + 5 项 v2 整数内积与双反例）、SIFTsmall 离线准备与 48 项功能回归，生成本机 PDF 与 `SUCCESS.json`（性能状态显式标记为 `not_evaluated`）。
- 默认完整模式：在快速验收基础上，离线准备 SIFT1M 与 GloVe25，运行 26 配置本机校准（若本机指纹已缓存则秒级复用，本机实测 7.4 s、服务器 13.7 s），随后冻结配置运行 78 项随机交错 Faiss 对照并生成本机报告与证据包。
- `--cpu <id>`：显式指定允许绑定的逻辑 CPU；请勿同时并行运行两轮性能测量。
- `--require-performance-target`：完整测量完成后先保留全部报告与证据，若 78 项中存在未领先项则返回退出码 `3`。

## 2. 离线数据与运行资源需求

- SIFTsmall、SIFT1M 与 GloVe25 三份原始归档已完整随包存放在 `baseline/data/`，并记录于 `DATA_MANIFEST.json`。脚本直接本地校验解压与转换，无需联网下载数据集。
- 仅首次在全新环境安装缺失 Python/系统依赖时可能需要访问软件源与相应权限。复现全过程本地执行，无需在线 AI 服务或 API 密钥。
- 完整模式建议预留数小时、至少 8 GiB 可用内存及 10 GiB 可用磁盘空间；ARM 或未暴露 AVX2/FMA 的处理器不在当前执行范围内。

## 3. 输出产物位置

每次运行会在 `results/autotune_<UTC时间戳>/` 下生成完整独立归档：
- `SUCCESS.json` / `performance.json` / `steps.json`：状态标记、性能汇总与各步骤耗时。
- `report/reproduction_report.pdf`：当前机器实测自动生成的复现报告。
- `reproduction_evidence.zip`：本次运行日志、配置指纹与实测结果打包。

## 4. 分步执行与报告图表重建

- **单独执行 v2 分步校准与对照**：先运行 `baseline/prepare_data.py`、`prepare_sift1m.py`、`prepare_glove.py` 准备数据，再按 `autotune_v2/README.md` 中的分步命令依次执行编译、回归、校准与 78 项对照。
- **重建课程报告图表与 PDF**：
  ```bash
  python3 packaging/generate_v2_figures.py   # 重建 4 张 v2 300 DPI 中文配图与 V2_SOURCES.md
  python3 packaging/generate_figures.py      # 保留 v1 历史剖析与路径切换图生成流程
  python3 packaging/render_report.py         # 将 report/*.md 渲染为 14 页课程报告 PDF
  ```
- **历史版本追溯**：`baseline/reproduce.sh` 保留第一阶段固定版流程，`autotune/` 保留第一阶段自动校准代码与记录，当前 v2 归档主结果位于 `experiments/v2/evidence/integrated-local-20261127` 与 `integrated-server-20261127`。

## 源码仓库与完整包

`baseline/data/` 原始负载与固定版独立入口 `baseline/reproduce.sh` 仅随 Release 完整提交包提供。本源码仓库默认入口是根目录 `reproduce.sh`，使用 v2 自动校准版。源码用户先从完整 ZIP 导入负载；老师直接下载完整 ZIP 即可。
