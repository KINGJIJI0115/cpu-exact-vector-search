# 面向批量精确向量检索的 CPU 跨层性能优化

**课程完整材料：** [完整复现 ZIP（含全部负载）](https://github.com/KINGJIJI0115/cpu-exact-vector-search/releases/download/v1.0-course/cpu-exact-vector-search-v1.0-course-full.zip) · [14 页课程报告 PDF](https://github.com/KINGJIJI0115/cpu-exact-vector-search/releases/download/v1.0-course/course-report.pdf) · [Release 页面 (`v1.0-course`)](https://github.com/KINGJIJI0115/cpu-exact-vector-search/releases/tag/v1.0-course)

作者：赵信喆（软件系统优化课程项目）

本项目以百万级常驻内存向量库上的批量精确最近邻检索（Exact kNN / 平方 L2）为真实负载，围绕 **测量剖析 → 四层软硬件跨层优化 → 跨微架构自动校准 → 形式化验证与一键复现** 完成端到端性能优化。Faiss 仅作为外部性能对照基准，不参与自研内核的任何计算。

## 主要结果与亮点

| 实验平台与方案 | 领先最快适用 Faiss 批次数 | 三批全领先配置数 | 几何平均加速比 | 加速比范围 |
|---|---:|---:|---:|---:|
| 本地 Core Ultra 9 275HX（固定版） | **78 / 78** | **26 / 26** | **2.086×** | 1.21–4.60× |
| 学校 Xeon Gold 6133（自动校准版） | **67 / 78** | **22 / 26** | **1.393×** | 0.883–2.130× |

- **逐层消融验证**：SIFTsmall 上阶段剖析定位瓶颈由 Top-K 筛选（60.8%）转移至距离计算（84.9%），组合流式最大堆、候选分块与 AVX2 后相对全排序基线加速 **9.43×**。
- **跨机自适应**：在 Xeon Gold 6133 上自动以紧凑字节核（`mode 100`）替代固定展开核（`mode 110`），使 SIFT Q=1 提速 **1.38–1.40×** 并转为领先 Faiss，同轮领先批次数由 58/78 提升至 **67/78**，正确性 **78/78** 全部通过。
- **形式化验证与全自动复现**：内置 **Z3 形式化验证**（36 项有界 Top-K 抽象模型、变异证伪反例与 4 项无损整数算术引理）、3292 项边界回归测试、全自动一键复现脚本及完整的 [AI 辅助研发记录](AI_ASSISTANCE_FINAL.md)。

> 主实验覆盖 SIFT1M 与 GloVe25 共 26 个配置 × 3 批查询，所有方法与 BLAS/OpenMP 均为单线程并固定 `OPENBLAS_CORETYPE=Haswell`。以上数字来自归档实测，新机器运行将生成本机报告。

![学校服务器 SIFT1M 路径切换与双机代表性配置加速比对比](report/figures/fig3_faiss_paths_crossover.png)

## 四层软硬件跨层优化

- **L1 算法与数据结构层**：完整排序 $O(N \log N)$ → 流式定长最大堆 $O(N \log K)$，消除 $O(N)$ 距离数组并将替换合并为单次下沉调整。
- **L2 内存与缓存层**：8 路 AoSoA 交错布局、64 字节对齐、256 候选块级缓存分块；0–255 整数输入启用无损 `uint8` 表示（单份存储体积降低 4×）。
- **L3 指令集与微架构层**：AVX2 256-bit 8 通道并行、`VPMADDWD` 无损整数乘加、128/25 维固定展开、1/2/4/8 查询寄存器复用与 SIMD 阈值掩码剪枝。
- **L4 编译与运行时自适应层**：确定性编译选项 + 17 候选模式本机自动校准，基于 CPU/缓存/源码 SHA256 指纹实现缓存复用（首次校准约 32.4 分钟，指纹命中复用约 11.16 秒）。

![四层软硬件跨层优化体系与 8 路 AoSoA / VPMADDWD 数据流](report/figures/fig1_cross_layer_arch.png)

## 快速复现（推荐方式）

**推荐直接下载 [v1.0-course Release](https://github.com/KINGJIJI0115/cpu-exact-vector-search/releases/tag/v1.0-course) 中的 [`cpu-exact-vector-search-v1.0-course-full.zip`](https://github.com/KINGJIJI0115/cpu-exact-vector-search/releases/download/v1.0-course/cpu-exact-vector-search-v1.0-course-full.zip)**（已随包附带 SIFTsmall、SIFT1M、GloVe25 全部原始负载与完整实验证据，无需另行下载数据；请勿使用 GitHub 自动生成的 `Source code` 压缩包代替）。

解压后在 Ubuntu 22.04 / WSL2 终端进入根目录执行：

```bash
python3 verify_bundle.py
bash reproduce.sh --quick   # 快速验收：编译、回归测试、Z3 形式化验证与报告生成（约 1 分钟）
bash reproduce.sh           # 完整复现：本机 26 配置校准 + 78 项 Faiss 同轮对照（预留数小时）
```

> 可附加 `--cpu <id>` 指定空闲逻辑 CPU。首次缺少系统工具或 Python 依赖时脚本会自动安装（需联网与相应权限）。

## 从本源码仓库运行

本 Git 仓库保留完整核心代码、14 页课程报告、5 张配图及主要归档结果（不含大体积原始负载与构建产物）。克隆后可直接完成校验与快速验收：

```bash
python3 verify_bundle.py
bash reproduce.sh --quick
```

如需在本源码仓库内运行完整 78 项实验，先从上述 Release 完整包导入经过 SHA256 校验的原始负载（不覆盖源码）：

```bash
python3 tools/import_release_data.py /path/to/cpu-exact-vector-search-v1.0-course-full.zip
bash reproduce.sh
```

从归档数据一键重绘 5 张配图与重编 PDF 报告：

```bash
python3 packaging/generate_figures.py
python3 packaging/render_report.py
```

## 环境要求与输出说明

- **运行环境**：Ubuntu 22.04 / WSL2 Ubuntu，Python 3.10+，x86-64 CPU 支持 AVX2/FMA，建议预留 ≥ 4 GiB 内存与 ≥ 3 GiB 磁盘空间。
- **结果目录**：新运行输出在 `results/autotune_时间戳/`，含步骤日志 `steps.json`、状态摘要 `SUCCESS.json`、78 项对比 `confirmation/` 与本机报告 `report/`。流程执行、正确性检查与性能领先数三项状态独立记录（快速模式性能状态为 `not_evaluated`）。

## 仓库导航

| 内容 | 路径 |
|---|---|
| 14 页课程报告 PDF 与源稿 | [report/](report/) |
| 配图数据来源与重绘脚本 | [report/figures/SOURCES.md](report/figures/SOURCES.md) · [packaging/generate_figures.py](packaging/generate_figures.py) |
| 默认自动校准内核与测试 | [autotune/](autotune/) |
| 固定版内核与分层消融代码 | [baseline/src/](baseline/src/) |
| 学校服务器 78 项对照记录 | [evidence/faiss78/summary.csv](evidence/faiss78/summary.csv) |
| 详细复现与分步指南 | [REPRODUCE.md](REPRODUCE.md) |
| 课程要求对照表与 AI 辅助记录 | [COURSE_CHECKLIST.md](COURSE_CHECKLIST.md) · [AI_ASSISTANCE_FINAL.md](AI_ASSISTANCE_FINAL.md) |
| 基准数据来源与第三方引用 | [DATA_SOURCES.md](DATA_SOURCES.md) |
| Release 发布与独立验收记录 | [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md) · [docs/PUBLIC_VALIDATION.md](docs/PUBLIC_VALIDATION.md) |

## 使用与数据说明

本项目源码与报告用于《软件系统优化》课程项目提交与复现评审；所含 SIFT / GloVe 基准数据集与 Faiss、OpenBLAS、Z3 等第三方依赖仅用于课程评测与可复现性验证，相关来源与学术引用见 [DATA_SOURCES.md](DATA_SOURCES.md)，权利归原提供方所有。独立环境下的快速功能验证与离线数据准备测试记录见 [docs/PUBLIC_VALIDATION.md](docs/PUBLIC_VALIDATION.md)。
