# 课程评审快速指引（v2 提交包）

姓名：赵信喆　学号：51295903131　课程：软件系统优化　日期：2026年11月27日

本提交包为整合第一阶段（v1 四层跨层优化与自动校准）与第二阶段（v2 整数范数内积与缓存感知分块）的最终课程材料，双机 78 项同轮 Faiss 对照均取得 **78/78 领先**且正确性全部通过（本机几何平均 **2.488×**，学校服务器 **1.512×**）。

## 建议阅读顺序

1. `report/51295903131_赵信喆_系统优化课程报告.pdf`：14 页完整研究报告（含 6 张 300 DPI 中文配图、双机全部 26 配置数据、静态指令分析、Z3 形式化验证与成本摊销）。
2. `COURSE_CHECKLIST.md`：课程要求与包内文件逐项对照清单。
3. `REPRODUCE.md` 与 `ENVIRONMENT.md`：复现命令、前置条件与环境配置。
4. `AI_ASSISTANCE_FINAL.md` 与 `DATA_SOURCES.md`：AI 辅助说明与原始基准负载来源。

## 快速验证命令（Linux x86-64 / WSL2）

```bash
python3 verify_bundle.py          # 校验包内全部文件 SHA256 完整性
bash reproduce.sh --check-env     # 检查编译器、AVX2/FMA、依赖与 CPU 亲和性
bash reproduce.sh --quick         # 快速验收：编译、回归、三组 Z3 验证、SIFTsmall 与 PDF 生成
bash reproduce.sh                 # 完整复现：离线数据准备 + 26 配置校准/复用 + 78 项 Faiss 对照
```

- 全部三份原始负载已包含在 `baseline/data/` 中，脚本离线准备数据，无需联网下载数据集。
- 仅首次安装缺失的系统/Python 依赖时可能需要访问软件源；复现过程不依赖任何在线 AI 服务或密钥。
- 重建报告配图与 PDF：`python3 packaging/generate_v2_figures.py` 与 `python3 packaging/render_report.py`。
