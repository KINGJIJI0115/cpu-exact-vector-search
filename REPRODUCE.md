# 复现步骤

## 1. 环境、资源与前置条件

- **系统与硬件**：Ubuntu 22.04 或 WSL2 Ubuntu，Python 3.10+，x86-64 CPU 且支持 AVX2/FMA。程序绑定单一逻辑 CPU，搜索与 BLAS/OpenMP 均为单线程。
- **OpenBLAS 固定路径**：默认复现脚本与历史对照均设置 `OPENBLAS_CORETYPE=Haswell`（单线程），用于在跨机器比较中保持 BLAS 底层指令路径一致。
- **建议可用资源**：
  - **内存**：建议预留至少 **4 GiB 可用内存**（百万级数据集会同时建立自研双布局索引与多条 Faiss 对照索引，并缓存参考答案；不能仅按单个索引 RSS 估算整条流水线峰值内存）。
  - **磁盘**：建议预留至少 **3 GiB 可用磁盘空间**（用于解压包内原始数据、保存转换后的二进制向量、参考答案缓存及新运行结果目录）。
  - **网络与权限**：SIFT1M、GloVe25、SIFTsmall 三份原始归档已随包提供（`sift.tar.gz.part` 为完整已校验归档，脚本自动解压；GloVe HDF5 自动归一化转换）。仅当机器缺少 GCC、binutils、Python 依赖、Z3 或中文字体时，首次安装需要联网软件源及相应权限；共享服务器可先由管理员预装。

在解压根目录先执行文件与环境检查：

```bash
python3 verify_bundle.py
bash reproduce.sh --check-env
```

## 2. 默认完整运行（自动校准版）

```bash
bash reproduce.sh          # 或 ./reproduce.sh
# 指定空闲逻辑核：
bash reproduce.sh --cpu 0
```

流程依次执行：环境预检 → 编译 → 边界回归与 Z3 形式化验证 → 原始数据解压转换 → 本机 26 配置自动校准（或指纹缓存复用）→ 冻结选择并运行 78 项 Faiss 同轮对照 → 自动生成本机报告与证据包。

当前机器的选择写入 `autotune/profiles/local.json`，再次运行且 CPU、缓存、编译器、源码与数据指纹一致时自动复用；任一指纹变化则重新校准。`autotune/profiles/host.json` 保存学校服务器的归档选择。

**三类耗时参考（务必区分，勿混同）：**
- **快速模式（`--quick`）**：约 **1–2 分钟**（编译、候选/缓存回归、Z3 验证、生成简短报告）。
- **本机自动校准环节**：学校服务器首次 26 配置校准实测约 **32.4 分钟**（1943.2 秒）；命中本机指纹缓存复用约 **11.16 秒**。
- **完整默认运行（含 78 项 Faiss 对比）**：学校服务器已有参考答案缓存时，仅 78 项对比另需约 **67.7 分钟**；全新环境还包含数据解压、格式转换与双精度参考真值计算，完整运行建议预留 **2–3 小时**。

## 3. 查看结果与三类状态说明

结果保存在 `results/autotune_时间戳/`：

| 文件或目录 | 内容 |
|---|---|
| `report/reproduction_report.pdf`、`.md` | 当前机器的新生成报告 |
| `confirmation/summary.csv`、`raw.csv` | 78 项性能汇总与每次交替计时 |
| `calibration/`、`selected_profile.json` | 本轮校准或复用记录与最终选核 |
| `environment.json`、`steps.json` | 硬件/软件环境、命令、退出码与各步耗时 |
| `SUCCESS.json`、`performance.json` | 流程状态、正确性状态与性能达标统计 |
| `reproduction_evidence.zip` | 本轮报告与实验证据归档 |

程序严格区分三类独立状态：**流程执行完成**、**正确性全部通过**、**性能领先批次数**。默认模式下，只要流程无异常且 78 项正确性全部通过即返回退出码 `0`，即使在新机器上性能领先数未达 78/78 也会保留全部较慢配置并生成完整报告。若需将全配置性能达标作为退出门禁，可附加 `--require-performance-target`（未全达标时先保存报告与结果，再返回 `3`）；执行出错时记录 `FAILED.json` 并返回非零码。

## 4. 快速检查与图表重绘

```bash
bash reproduce.sh --quick                 # 功能、缓存与 Z3 快速验收（性能状态为 not_evaluated）
python3 packaging/generate_figures.py     # 直接从包内归档数据重绘报告 5 张配图
python3 packaging/render_report.py        # 重新渲染 report/ 下的最终 PDF 报告
```

## 5. 分步运行自动校准版

默认入口已自动串联以下步骤；如需分步调试，先完成依赖与数据准备，再执行：

```bash
cd autotune
export PYTHONPATH="$(realpath ../baseline/.deps)"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_CORETYPE=Haswell
CPU=0
taskset -c "$CPU" python3 test_adaptive.py
nice -n 15 ionice -c 3 python3 calibrate.py --data ../baseline/data --cpu "$CPU" --profile profiles/local.json
nice -n 15 ionice -c 3 python3 compare_faiss78_portable.py --base ../baseline --out results/my_faiss78 --cpu "$CPU"
```

## 6. 单独复现固定版与形式化验证

- 固定版一键复现：`cd baseline && bash reproduce.sh`（或 `./reproduce.sh`）。
- 单独运行 Z3 形式化验证：在 `baseline/` 中执行 `python3 formal_verify.py` 和 `python3 formal_verify_byte.py`。

补充：复现完全使用随包归档源码与数据，无需在线 AI 服务或 API 密钥。历史完整性能数据来自归档的本地与学校服务器实验，最终提交包保留了相同核心源码与指纹校验链；默认入口已完成本地快速验收，新机器上的实际性能以新生成的本机报告为准。


## 源码仓库补充

本文原有随包数据说明与第 6 节固定版独立入口 `baseline/reproduce.sh` 均针对 Release 完整提交包。本源码仓库不包含原始负载及 `baseline/reproduce.sh`，请以根目录 `reproduce.sh` 为默认入口，并在完整运行前先执行 `python3 tools/import_release_data.py <完整ZIP路径>`。源码裁剪后的历史材料以 README 和配图来源索引为准；完整历史记录与固定版独立脚本在 Release 附件中。
