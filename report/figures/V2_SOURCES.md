# v2 报告配图数据来源与统计口径

以下图表均由 `packaging/generate_v2_figures.py` 直接读取归档实验数据自动生成（300 DPI 中文学术配色），并与 `report/figures/SOURCES.md` 中的 v1 历史剖析与路径切换图共同构成完整报告配图体系：

1. `v2_arch.png`：v1+v2 四层软硬件跨层架构与 v2 整数范数展开/AVX2 内积数据流；静态指令数源自 `experiments/v2/evidence/local-20261127/static_instruction_counts.json`，索引载荷源自 `setup_v1/summary.json`。
2. `v2_kernel_gain.png`：
   - (a) 大批量分段抽样距离计算占比（周期 128）：源自 `experiments/v2/evidence/local-20261127/local_profile_v1/summary.csv` 与 `server-20261127/server_profile_v1/summary.csv`；静态指令数源自 `static_instruction_counts.json`。
   - (b)/(c) 双机四重点配置旧自研核与 v2 整数内积核耗时对比（三批中位耗时的中位数）：源自 `local_screen_v2/confirmation.json` 与 `server_screen_v1/confirmation.json`。
3. `v2_all_configs.png`：双机全部 26 配置（78 项）v2 自动校准相对最快适用 Faiss 的三批加速比中位数与极值误差线，叠加同轮原固定分派（`original_ms`）对照点；源自 `integrated-local-20261127/run/faiss78/summary.csv` 与 `integrated-server-20261127/run/faiss78/summary.csv`。
4. `v2_pipeline_and_amortization.png`：
   - (a) `bash reproduce.sh` v2 全自动复现与指纹复用流水线；校准与复用时间源自双机 `steps.json`。
   - (b) 双机 SIFT1M（Q=128, K=100）建索引 + 持续查询累计耗时摊销曲线；建索引耗时源自双机 `faiss78/setup.json`，批次查询耗时源自双机 `faiss78/summary.csv` 三批中位数。
