# v2：瓶颈测量与整数内积候选

这是独立开发分支中的实验入口，不改变根目录默认复现流程，不覆盖v1.0-course。

## 文件

- `build_profile.py`：从现有内核生成无插桩对照和抽样诊断库。
- `profile_bottlenecks.py`：六个诊断项（四个大批量短板，以及Q4/K10的两种内核）。
- `build_candidates.py`：生成mode 200/201整数范数—内积候选；不修改autotune/src内的发布源码。
- `screen_candidates.py`：分块和整数内积筛选，冻结选择后测试三批新查询。
- `formal_dot.py`：5项整数算术证明和一个错误公式的SAT反例。
- `measure_setup.py`：交错独立进程测量索引构建和内存。

## 运行

需要Linux x86-64、AVX2/FMA、g++、NumPy；形式化验证另需python3-z3。使用已验收Release的数据目录，不复制或修改原始数据。先设置下面三个变量：

```bash
DATA=/你的完整项目/baseline/data
DEPS=/你的完整项目/baseline/.deps
CPU=0   # 换成允许使用的空闲逻辑CPU
export PYTHONPATH="$DEPS"
RUN=experiments/v2/runs/my_machine
python3 experiments/v2/profile_bottlenecks.py --data "$DATA" --out "$RUN/profile" --cpu "$CPU" --repeats 5 --periods 32,128,512
python3 experiments/v2/screen_candidates.py --data "$DATA" --control "$RUN/profile/build/control.so" --out "$RUN/screen" --cpu "$CPU" --repeats 5 --confirm-repeats 5
python3 experiments/v2/measure_setup.py --data "$DATA" --control "$RUN/profile/build/control.so" --candidate "$RUN/screen/build/candidate.so" --out "$RUN/setup" --cpu "$CPU"
python3 experiments/v2/formal_dot.py --out "$RUN/formal"
```

输出目录必须不存在，避免覆盖上一轮证据。共享服务器建议在外层加 `nice -n 5 ionice -c 3`，程序自身会绑定单核并降低优先级。不要改变其他用户进程或全局CPU/PMU设置。

服务器初筛可用 `--repeats 3 --confirm-repeats 5 --fast-screen`。这时筛选8种方法，确认仍然每批5次随机交错；方法与本机完整12候选筛选不同，见保存的policy.json。

## 测量解释

诊断以伪随机方式抽样8候选向量的计算tile，分别记录距离累加与“累加器归约、阈值掩码、堆维护”。统计字段的selection不是纯粹的堆耗时。计时调用本身有成本，百分比只用于定位，应同时检查不同抽样频率和无插桩对照的差异，不能直接拼成发布版精确耗时堆叠图。

性能筛选与确认使用无插桩库，记录ctypes搜索调用及输出数组分配，不包含索引构建、校准和原AdaptiveIndex的全部Python输入检查。新增候选尚未接入正式自动校准与默认搜索API，因此不是新的正式78项结果。

新的确认查询排除旧基线训练、旧78项确认、旧校准训练及验证查询。选择在新查询测试前写入frozen_selection.json并保持哈希不变。新查询仍属于同一真实数据集，不等于独立新数据集。

整数路径对距离和ID要求完全一致，并使用官方groundtruth检查百万向量结果的距离。小规模回归另外使用独立float64穷举，覆盖重复、尾部、K=N、0/255以及浮点查询/数据库回退。

## 当前候选设计

D=128且数据库与查询都属于0..255整数时，使用范数+内积精确恢复平方L2；每个数据库向量多保存一个int32范数。其他输入回到原mode 7，保持发布版的浮点计算和排序行为。mode 200为8查询分组、mode 201为4查询分组。没有BLAS/Faiss调用。

v1.0源码、根目录默认入口和线上Release均保留。实验原始记录放在runs/（不自动提交），可审阅证据归档在evidence/。
