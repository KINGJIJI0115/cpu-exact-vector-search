# 源码发布版验收

2026年11月25日，在本机WSL Ubuntu独立临时目录复制源码版并顺序运行：

| 检查 | 结果 |
|---|---|
| `python3 verify_bundle.py` | 通过 |
| `bash reproduce.sh --quick` | 退出0，约25.38秒，实际编译、回归、Z3检查和报告生成 |
| `python3 tools/import_release_data.py <完整ZIP>` | 通过，校验完整ZIP及每个导入负载文件 |
| `python3 packaging/generate_figures.py` | 五张图重建成功 |
| `python3 packaging/render_report.py` | 报告重建成功 |

临时目录已删除，运行日志保存在本地发布目录的validation/，不需要上传到源码仓库。完整课程ZIP本身另有独立快速验收记录。

此轮为源码整理后的功能验收，没有重新运行26配置校准或78项性能对比。性能结果沿用报告中的归档实测。

基本凭据格式扫描未发现私钥或常见访问令牌格式；源码仓库无超过100 MiB的文件。报告包含课程署名和学号，默认按公开课程仓库发布。
