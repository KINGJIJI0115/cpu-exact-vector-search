# v2 整理与脚本重建验收记录

日期：2026年11月27日。对 v2 完整包解压目录依次验证以下脚本链路：

| 检查项 | 结果 |
|---|---|
| `python3 verify_bundle.py` | 全部文件 SHA256 校验通过 |
| `python3 packaging/generate_v2_figures.py` | 4 张 v2 中文配图重建成功 |
| `python3 packaging/render_report.py` | 14 页课程研究报告 PDF 重建成功 |
| `bash reproduce.sh --check-env` / `--quick` | 编译、回归、三组 Z3 形式化检查与本机 PDF 生成通过 |
| 核心实测源码与原始负载校验 | 与归档实验逐字节一致 |

注：本轮整理仅升级研究报告、统一中文配图并同步发布文档，未修改任何实测计算内核、校准逻辑或原始实验记录；主性能结果沿用双机归档 78 项同轮实测。
