# 公开发布说明

本仓库及 `v1.0-course` Release 面向《软件系统优化》课程评测与可复现性验证公开发布：

- **源码仓库**：包含完整自研 C++/Python 源码、14 页课程报告、5 张配图与可追溯绘图/渲染脚本、核心实验结果以及 Z3 形式化验证材料，不跟踪大体积原始数据集与编译产物。
- **Release 完整包**：`cpu-exact-vector-search-v1.0-course-full.zip` 随包附带全部三份标准负载与完整归档证据，支持解压后离线准备数据并一键复现。
- **完整性与环境记录**：仓库与完整包分别维护独立的根目录 `MANIFEST.json` 并通过 `verify_bundle.py` 校验；姓名与学号按课程署名规范保留，历史实验记录中的硬件与路径信息仅作为实测溯源证据，不含凭据或私钥。
- **数据来源与引用**：各基准数据集的来源、哈希与许可信息统一记录于 `DATA_SOURCES.md`、`DATA_MANIFEST.json` 与 `docs/DATA_RIGHTS_STATUS.json`。
