# v1.0-course：完整课程复现包

本Release提供包含全部负载的完整项目包。老师无需另行寻找或下载SIFTsmall、SIFT1M、GloVe25。

## 下载

- `cpu-exact-vector-search-v1.0-course-full.zip`：源码、全部负载、实验证据与一键复现入口。
- `course-report.pdf`：课程报告。
- `SHA256SUMS.txt`：上述附件的SHA256。

GitHub自动生成的Source code ZIP仅含源码仓库，不能代替完整复现包。

## 运行

在Ubuntu/WSL终端解压完整包，进入根目录：

```bash
python3 verify_bundle.py
bash reproduce.sh --quick
bash reproduce.sh
```

第一条检查文件完整性；quick执行编译、回归、形式化检查并生成报告；默认完整模式进行本机校准和78项Faiss对照。数据已随包，首次软件依赖安装仍可能需要网络及相应权限。完整模式预留数小时。

## 结果

本地固定版78/78领先、几何平均2.086倍；学校服务器自动校准版67/78领先、几何平均1.393倍且正确性78/78。均为报告记录的机器及单线程配置，新机器以实际输出为准。

## 数据与本次整理

移除两份历史学校调度脚本，保留实验计算代码、全部负载及测量数据。GloVe上游许可已核实为PDDL；SIFTsmall镜像MIT标注及SIFT1M上游授权的未确认事项见DATA_SOURCES.md。本地文件准备完成不表示SIFT再分发授权已经取得。
