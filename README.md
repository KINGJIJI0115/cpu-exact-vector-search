# 面向 CPU 精确向量检索的跨层优化与跨机器自动校准（v2）

作者：赵信喆（学号 `51295903131`）｜课程：《软件系统优化》｜版本：`v2.0-course`（2026年11月27日）

本项目研究常驻内存向量库上的批量精确平方 L2 最近邻检索（Exact kNN Search），在 **SIFT1M**、**GloVe25** 与 **SIFTsmall** 三个标准真实负载上，完成了从初始基线剖析、四层软硬件跨层优化（v1）到大批量指令级重构与缓存感知分块自动校准（v2）的两轮完整性能优化闭环。

## 核心成果总览（双机 78 项同轮 Faiss 对照）

每项测试均与全部适用 Faiss 路径（`faiss_flat`、`faiss_direct`、`faiss_blas` 及 SIFT 的 `faiss_sq8_direct`）中最快者同轮随机交错比较（单线程绑核，固定 `OPENBLAS_CORETYPE=Haswell`）：

| 测试机器与版本 | 正确性 | 领先批次数 | 总体几何平均加速比 | 加速比范围 | 备注 |
|---|---:|---:|---:|---:|---|
| 本地 Core Ultra 9 275HX（v1 固定版） | 78 / 78 | 78 / 78 | 2.086× | 1.210–4.600× | 四层基础跨层优化 |
| **本地 Core Ultra 9 275HX（v2 自动校准版）** | **78 / 78** | **78 / 78** | **2.488×** | **1.115–7.356×** | SIFT1M 2.738×（峰值 7.356×），GloVe25 1.919× |
| 学校 Xeon Gold 6133（v1 固定版 / v1 自动校准） | 78 / 78 | 57/78 → 67/78 | 1.307× → 1.393× | 0.883–2.130× | 自动改选 `mode 100` 解决 Q=1/2 分化 |
| **学校 Xeon Gold 6133（v2 自动校准版）** | **78 / 78** | **78 / 78** | **1.512×** | **1.085–2.384×** | 消除 512 条 `vpsubw` + 选 `block=128`，大批量全领先 |

- **四层软硬件跨层优化**：流式定长最大堆（L1）+ 8 路 AoSoA/无损 `uint8` 字节布局与预存整数范数（L2）+ AVX2 零 `vpsubw` 整数内积核（L3，热函数静态指令由 3,010 降至 2,604）+ 按机器 CPU/源码 SHA256 指纹自动校准与分块选择 `{128, 256, 512}`（L4）。
- **形式化验证（Z3 4.8.12）**：完整覆盖 36 项有界 Top-K 抽象模型 + 4 项无损字节平方差引理 + 5 项 v2 整数范数内积算术引理（全部 `UNSAT`），并配套双变异反例证伪（全部 `SAT`）。
- **全自动复现（负载随包提供）**：完整课程提交包随附全部三份原始测试负载，解压即可离线准备数据并一键复现。

## 核心文档导航

1. [`report/51295903131_赵信喆_系统优化课程报告.pdf`](report/51295903131_赵信喆_系统优化课程报告.pdf)：14 页完整研究报告（融合 v1 跨层基础与 v2 整数内积升级，含 6 张 300 DPI 中文配图与双机完整 26 配置数据）。
2. [`START_HERE.md`](START_HERE.md)：面向课程评审的快速阅读与验收指引。
3. [`COURSE_CHECKLIST.md`](COURSE_CHECKLIST.md)：课程项目要求与提交材料逐项对应表。
4. [`REPRODUCE.md`](REPRODUCE.md)：全自动一键复现、快速验收与分步执行说明。
5. [`ENVIRONMENT.md`](ENVIRONMENT.md) 与 [`DATA_SOURCES.md`](DATA_SOURCES.md)：软硬件环境、依赖与基准数据来源说明。
6. [`AI_ASSISTANCE_FINAL.md`](AI_ASSISTANCE_FINAL.md)：人机闭环 AI 辅助研发说明（复现无需在线 AI 服务或密钥）。

## 下载完整复现包

**老师复现请下载 [v2.0-course Release](https://github.com/KINGJIJI0115/cpu-exact-vector-search/releases/tag/v2.0-course) 中的 `cpu-exact-vector-search-v2.0-course-full.zip`。** 该附件包含全部三份负载；GitHub 自动生成的 Source code ZIP 不包含原始负载。

源码仓库用户先下载完整附件，再执行 `python3 tools/import_release_data.py /path/to/cpu-exact-vector-search-v2.0-course-full.zip` 导入负载，随后运行下方命令。首次安装缺失依赖需要联网，负载准备无需联网。

## 一键校验与复现

在 Linux x86-64 或 Windows WSL2 中进入完整包解压目录：

```bash
python3 verify_bundle.py
bash reproduce.sh --check-env
bash reproduce.sh --quick
bash reproduce.sh
```

- `--quick`：执行编译、4 组集成回归、三组 Z3 形式化验证、SIFTsmall 48 项回归并生成本机验收 PDF 与 `SUCCESS.json`。
- 默认完整模式：使用 `autotune_v2` 离线准备三份负载，完成 26 配置本机校准（或指纹命中秒级复用）与 78 项同轮 Faiss 对照并生成本机报告（建议预留数小时与至少 8 GiB 可用内存）。
- 可通过 `--cpu <id>` 指定逻辑核心，通过 `--require-performance-target` 启用 78/78 性能门禁。

结果输出至 `results/autotune_<时间戳>/`（含 `SUCCESS.json`、`performance.json`、`steps.json`、`report/reproduction_report.pdf` 与 `reproduction_evidence.zip`）。原 v1 历史记录保留在 `history/`、`autotune/` 与 `baseline/` 中便于完整追溯。
