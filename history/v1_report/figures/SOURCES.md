# 课程报告配图数据来源与复现索引

本目录 5 张配图均由提交包内的统一脚本 `packaging/generate_figures.py` 直接读取归档实验数据自动生成（300 DPI）。在解压根目录执行 `python3 packaging/generate_figures.py` 即可重新生成全部图片。

| 图号与文件名 | 对应数据来源（包内相对路径） | 实验环境与配置 | 统计口径 |
|---|---|---|---|
| **图 1** `fig1_cross_layer_arch.png` | 架构与数据流示意图；存储大小引自 `baseline/results/goal_memory_20261124T054856529211Z/summary.csv` 与 `baseline/LOSSLESS_BYTE_DESIGN.md` | 四层优化设计 + SIFT1M (N=1,000,000, D=128) | 精确存储载荷（488.3 MiB / 122.1 MiB）与算术边界 |
| **图 2(a)** `fig2_bottleneck_ablation.png` | `baseline/results/perf_20261109T090707225322Z/workload_stat.json` | 本地 Core Ultra 9 275HX，SIFTsmall (N=10,000, D=128, Q=100, K=10)，随机交替 21 次 | 各阶段中位数分别计算；柱顶总耗时为**分阶段中位数之和**（与每次总耗时中位数误差 <0.21 ms） |
| **图 2(b)** `fig2_bottleneck_ablation.png` | `baseline/results/goal_ablation_20261124T054947270218Z/internal_summary.csv` | 本地 Core Ultra 9 275HX，SIFTsmall (N=10,000, D=128, Q=32, K=10)，每版重复 7 次 | 各变体中位耗时及相对变体 0（完整排序+标量）加速比 |
| **图 3(a)** `fig3_faiss_paths_crossover.png` | `evidence/faiss78/sift1m_q{1,2,4,8,32,128,256}_k10_b{0,1,2}.json` | 学校服务器 Xeon Gold 6133，SIFT1M (K=10)，每批交替 7 次，3 批 | 各路径三批中位耗时的中位数除以批量 Q（ms/query） |
| **图 3(b)** `fig3_faiss_paths_crossover.png` | 本地：`baseline/report/goal_summary.csv`；服务器：`evidence/faiss78/configuration_summary.csv` 及对应 `b{0,1,2}.json` | 双机对比，SIFT1M 与 GloVe25 代表性配置 (K=10)，单线程 | 相对该配置最快适用 Faiss 路径的三批中位加速比 |
| **图 4(a)(b)** `fig4_autotune_server.png` | `evidence/faiss78/configuration_summary.csv` 及 `evidence/faiss78/*.json`（78 份原始批记录） | 学校服务器 Xeon Gold 6133，全 26 配置 × 3 批，同轮交替 7 次 | 三批中位耗时与三批加速比区间（同轮原分派 vs 自动校准版） |
| **图 5(a)** `fig5_pipeline_and_amortization.png` | `reproduce.sh`、`reproduce_autotune.py`、`autotune/RESULTS.md` | 全自动复现与指纹缓存流程 | 首次校准 32.4 min、缓存复用 11.16 s、78 项比较另计 |
| **图 5(b)** `fig5_pipeline_and_amortization.png` | 建索引：`baseline/results/goal_memory_20261124T054856529211Z/summary.csv`；查询：`baseline/results/goal_confirmation_20261124T050444493472Z/summary.csv` | 本地 Core Ultra 9 275HX，SIFT1M (Q=8/K=10 及 Q=128/K=100) | 建索引 3 进程中位数 + 累计批数 × 查询三批中位数 |
