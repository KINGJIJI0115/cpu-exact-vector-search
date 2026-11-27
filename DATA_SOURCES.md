# 基准数据来源与第三方依赖说明

本v2完整课程包附带SIFTsmall、SIFT1M、GloVe25三份原始负载，存放在baseline/data/。解压后无需另行下载数据集，大小与SHA256见DATA_MANIFEST.json。

## 数据来源与预处理

| 负载 | 公开来源与版本 | 规模与用途 |
|---|---|---|
| SIFTsmall | [vecdata/siftsmall](https://huggingface.co/datasets/vecdata/siftsmall)（版本 `3106e1b83049c44713b1ce06942d0ab474bbdfb6`，原始来源 TEXMEX） | 10,000 × 128 图像局部描述子；用于阶段剖析与分层消融 |
| SIFT1M | [zjd2000/ANN_SIFT](https://huggingface.co/datasets/zjd2000/ANN_SIFT/tree/main)（版本 `8956d7e088e0b79b6901c234632e801fa37d731d`，原始来源 TEXMEX） | 1,000,000 × 128 图像局部描述子；主性能基准 |
| GloVe25 | [ANN-Benchmarks](https://github.com/erikbern/ann-benchmarks/blob/main/README.md) 提供的 `glove-25-angular.hdf5`（原始来源 Stanford GloVe Twitter 27B） | 1,183,514 × 25 词向量及 10,000 条查询；主性能基准 |

- SIFT1M 归档文件 `sift.tar.gz.part` 为完整且经 SHA256 校验的输入归档，脚本会自动解压，请勿作为临时碎片删除。
- GloVe25 经 `float64` 归一化后存为 `float32`，评测时在所存向量上重算精确平方 L2 参考答案。各文件大小与 SHA256 见 `DATA_MANIFEST.json`，预处理代码见 `baseline/prepare_*.py`。

## 学术引用与许可说明

- **GloVe**：Jeffrey Pennington, Richard Socher, Christopher D. Manning. *GloVe: Global Vectors for Word Representation*, EMNLP 2014。[Stanford GloVe 官方主页](https://nlp.stanford.edu/projects/glove/)以 [PDDL v1.0](https://opendatacommons.org/licenses/pddl/1-0/) 发布预训练词向量；ANN-Benchmarks 提供对应 HDF5 切分。
- **SIFT / TEXMEX**：Hervé Jégou, Matthijs Douze, Cordelia Schmid. *Product Quantization for Nearest Neighbor Search*, IEEE TPAMI, 2011。本项目通过公开镜像获取上述标准研究基准（SIFTsmall 镜像页标注 MIT，SIFT1M 原始 TEXMEX 归档内未附独立许可文件，详细核查记录保存在 `docs/DATA_RIGHTS_STATUS.json`）。
- **第三方依赖**：Faiss、NumPy、OpenBLAS、Z3、h5py、matplotlib、ReportLab 等均遵循其各自原有许可协议，由脚本按需安装，不纳入源码仓库。

本仓库及复现包内包含的基准数据集仅用于《软件系统优化》课程评测与可复现性验证，权利归原提供方所有。

补充：SIFTsmall 镜像带有 MIT 标注，SIFT1M 上游未核实到明确的再分发许可；这两项的上游再分发状态仍记录为未确认，详见 `docs/DATA_RIGHTS_STATUS.json`。本项目的源码许可不覆盖第三方数据。
