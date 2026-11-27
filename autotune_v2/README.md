# 开发版自动校准：整数内积候选

本课程提交包的根目录 `reproduce.sh` 默认使用本目录的v2自动校准流程。代码基于 `dev/v2-bottleneck-20261127` 开发分支；原 `autotune/` 和 `baseline/` 保留历史实现与证据。

## 这次增加了什么

保留原有全部候选，额外加入四个模式。只有128维、0至255整数数据库与查询，且Q≥8时，新模式才参与校准。

|保存的模式编号|底层内核|查询分组|候选分块|
|---|---|---:|---:|
|200|整数范数＋内积|8|128|
|201|整数范数＋内积|8|256|
|202|整数范数＋内积|8|512|
|203|整数范数＋内积|4|256|

这些是自动校准配置的编号。阶段实验脚本中的native mode 200/201则分别表示8/4查询分组；`adaptive.py`中的DOT_MODES负责两者的映射。

数据库范数在建索引时计算。搜索不会暗中调优；它读取与机器、CPU绑定、编译产物、代码和数据库匹配的配置。缺失、损坏或失配时回到原mode 7。新配置读取时还校验模式与分块大小是否匹配。

## 从完整负载复现

需要Linux x86-64、AVX2/FMA、g++、NumPy、Faiss和threadpoolctl。使用完整Release中的原始负载并完成原包的数据准备步骤。设置BASE为包含`data/`与`.deps/`的项目目录。

```bash
BASE=/path/to/prepared/full/project
CPU=0  # 选择允许使用且空闲的逻辑CPU
export PYTHONPATH="$BASE/.deps"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 autotune_v2/test_adaptive.py
python3 autotune_v2/check_siftsmall.py --data "$BASE/data" --cpu "$CPU" --out autotune_v2/results/siftsmall_correctness.json
python3 autotune_v2/calibrate.py --data "$BASE/data" --cpu "$CPU" --profile autotune_v2/profiles/my_host.json --force
python3 autotune_v2/compare_faiss78_portable.py --base "$BASE" --cpu "$CPU" --profile autotune_v2/profiles/my_host.json --out autotune_v2/results/my_faiss78
# 再次执行校准命令，检查配置复用；不要加--force。
python3 autotune_v2/calibrate.py --data "$BASE/data" --cpu "$CPU" --profile autotune_v2/profiles/my_host.json
```

比较输出目录必须不存在。脚本保留26配置×3批次，七次随机交错重复，Faiss默认、直接、BLAS路径以及SIFT适用的SQ8直接路径均参与对照。所有搜索为单线程。计时包含公开Python搜索调用与输出分配；构建、校准和答案计算另记。SIFTsmall承担原课程项目的逐层消融实验，78项主比较使用SIFT1M和GloVe25。

校准使用两批训练查询、两批独立验证查询；只有在两批训练中都比mode 7快至少3%的候选才能入选。选择在验证前冻结。正式78项比较也使用与训练、验证分离的查询。负结果照常保存，不根据正式比较结果反选内核。

## 文件与证据

`build_kernels.py`复用`experiments/v2/build_candidates.py`中已验证的源码变换，从原`autotune/src/`生成独立v2库。因此需保留仓库目录结构。生成的源代码与库放在本目录的src/build中，不覆盖正式版。

`test_adaptive.py`检查候选正确性、缓存身份与回退、新模式配置保存及错误分块拒绝。原始实验与汇总见RESULTS.md。新目录不包含数据副本，不修改Release、原定稿或现有机器配置。
