# 环境与配置清单

- 平台：Linux x86-64或Windows WSL2，CPU须支持AVX2/FMA；Python 3.10+、g++、binutils。
- 数值依赖：baseline/requirements.txt固定Faiss CPU 1.15.1、NumPy 2.2.6、threadpoolctl 3.8.0、h5py 3.12.1等版本。
- 报告与验证：Python Z3、matplotlib、ReportLab、Poppler及中文字体；Ubuntu缺失组件由reproduce.sh通过apt安装。
- 编译：C++17、-O3 -mavx2 -mfma -ffp-contract=off。精确编译器版本、源文件和二进制SHA256随每次运行保存。
- 线程：OPENBLAS_NUM_THREADS=1、OMP_NUM_THREADS=1、MKL_NUM_THREADS=1，OPENBLAS_CORETYPE=Haswell；自研和Faiss绑定同一逻辑CPU。
- 校准：两批训练、两批独立验证，每批重复5次。两批训练均快于mode 7至少3%的候选才具备入选资格。
- 主实验：autotune_v2/goal_scope.json定义26配置，三批查询，七次随机交错重复，共78项。SIFTsmall另作功能检查。
- 内存与存储：建议至少8 GB可用内存、10 GB空闲磁盘。完整测试预留数小时；依赖已装、答案缓存已建立时耗时减少。
- AI：研发阶段使用AI辅助，复现阶段不需要AI软件、在线模型或密钥。

两机实测环境与线程池记录位于experiments/v2/evidence/integrated-*/run/faiss78/manifest.json。形式化求解器版本和SMT2见experiments/v2/evidence/local-20261127/formal_dot_v1；复现时另保存当前Z3版本和结果。
