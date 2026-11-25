# 课程要求与提交材料对应表

赵信喆　51295903131

| 课程要求 | 提交材料 |
|---|---|
| 研究意义、相关工作、方法与结果 | `report/51295903131_赵信喆_系统优化课程报告.pdf`（第 1–9 节） |
| 真实负载与工作环境 | SIFT1M、GloVe25、SIFTsmall；本地 WSL2 与学校服务器环境记录（含 `OPENBLAS_CORETYPE=Haswell`） |
| 测量、分析、优化、验证闭环 | `workload_stat.json` 阶段剖析、分层消融、正确性回归、78 项 Faiss 同轮对照 |
| 至少两个软硬件不同优化层次 | L1 流式堆算法、L2 AoSoA/分块/无损字节表示、L3 AVX2/VPMADDWD/展开、L4 跨机自动校准 |
| 源代码与配置清单 | `autotune/`、`baseline/src/`、`requirements.txt`、`goal_scope.json` |
| 原始数据与中间/结果数据 | `baseline/data/` 三份原始归档；查询 ID、`raw.csv`、`summary.csv`、`configuration_summary.csv` |
| 可追溯图表与渲染脚本 | `packaging/generate_figures.py`、`packaging/render_report.py`、`report/figures/SOURCES.md` |
| 一键与分步复现脚本 | 根目录 `reproduce.sh`（自动校准版）、`baseline/reproduce.sh`（固定版）、`REPRODUCE.md` |
| 加分项：全自动化执行 | 环境预检、编译、验证、数据准备、校准/复用、78 项对照、自动出报告与打包 |
| 加分项：AI 辅助 | 报告第 7.2 节、`AI_ASSISTANCE_FINAL.md` 与 `autotune/cache_reporting_fix_audit.json` |
| 加分项：形式化验证 | 报告第 6.2 节、36 项有界 Top-K 模型、变异反例、4 项整数算术引理及 SMT-LIB2 日志 |
| 文件完整性校验 | `MANIFEST.json`、`verify_bundle.py`、包外 `SHA256SUMS.txt` 与 `RELEASE_VERIFIED.json` |

正式提交上传课程报告 PDF 和完整 ZIP 即可；ZIP 解压后从 `START_HERE.md` 开始阅读。

> 源码仓库补充：上表对应完整的 Release 课程提交包。本 Git 源码仓库已按体积裁剪，不含 `baseline/data/` 原始负载与固定版独立脚本 `baseline/reproduce.sh`；需要完整数据与全部历史归档请下载 Release 中的完整 ZIP。
