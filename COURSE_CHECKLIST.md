# 课程项目要求与 v2 提交材料对应表

姓名：赵信喆　学号：51295903131

| 课程要求 | 对应提交材料 |
|---|---|
| 研究报告（意义、方法、实验结果、相关工作对比） | `report/51295903131_赵信喆_系统优化课程报告.pdf`（14 页完整融合 v1+v2 研究报告）及同名 `.md` 源文档 |
| 真实应用负载与真实工作环境 | `baseline/data/` 内全部三份原始负载（SIFTsmall、SIFT1M、GloVe25）；`ENVIRONMENT.md` 与两机环境归档 |
| 完整的测量、分析、优化、验证闭环 | 报告第 2–6 节：v1 筛选→距离瓶颈转移与 9.43× 消融；v2 75%–84% 热点再剖析、512 条 `vpsubw` 消减与双机 78/78 验证 |
| 至少两个软硬件不同层次优化 | 覆盖四个层次：算法数据结构（L1）、内存与缓存布局分块（L2）、AVX2 指令级微核（L3）、跨机自动校准（L4） |
| 源代码 | `autotune_v2/`、`experiments/v2/`、`autotune/src/`、`baseline/src/` 及全部 Python 驱动与测试脚本 |
| 环境与配置清单 | `ENVIRONMENT.md`、`baseline/requirements.txt`、`autotune_v2/goal_scope.json` 及编译/库指纹记录 |
| 原始、中间与结果数据 | `baseline/data/`、`DATA_MANIFEST.json`、分段剖析与静态指令统计、校准训练/验证记录、双机 78 项 `raw.csv`/`summary.csv`/`setup.json` |
| 一键/分步复现脚本与前置条件 | 根目录 `bash reproduce.sh`（支持 `--check-env`/`--quick`/完整模式）、`reproduce_autotune.py`、`REPRODUCE.md`、`autotune_v2/README.md` |
| 加分项：全自动化执行 | `bash reproduce.sh` 自动串联预检、编译、回归、Z3 验证、离线数据准备、校准/复用、78 项对比与 PDF 生成 |
| 加分项：AI 辅助 | `AI_ASSISTANCE_FINAL.md` 与报告第 7.2 节人机闭环说明；复现完全离线本地化，无需 AI 服务或密钥 |
| 加分项：形式化验证 | Z3 4.8.12 完成 36 项 Top-K 模型 + 4 项字节算术 + 5 项 v2 整数内积引理与双变异反例证伪；默认复现自动重跑 |
| 图表与 PDF 可追溯重建 | `packaging/generate_v2_figures.py`、`packaging/generate_figures.py`、`packaging/render_report.py` 及 `report/figures/V2_SOURCES.md` |
| 完整性校验 | 包内 `MANIFEST.json` 与 `verify_bundle.py`；包外 `SHA256SUMS.txt` 与 `SUBMISSION_VERIFIED.json` |

## 源码仓库与完整包

`baseline/data/` 原始负载与固定版独立入口 `baseline/reproduce.sh` 仅随 Release 完整提交包提供。本源码仓库默认入口是根目录 `reproduce.sh`，使用 v2 自动校准版。源码用户先从完整 ZIP 导入负载；老师直接下载完整 ZIP 即可。
