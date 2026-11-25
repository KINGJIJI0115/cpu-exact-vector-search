# 负载、来源与再分发核查

核查日期：2026年11月25日。

完整Release的 `cpu-exact-vector-search-v1.0-course-full.zip` 保留SIFTsmall、SIFT1M和GloVe25全部原始负载，与课程定稿逐文件SHA256一致。老师下载此ZIP后不需要从其他网站下载数据；首次安装软件依赖仍可能联网。

## 来源和处理

| 负载 | 来源与固定版本 | 用途 |
|---|---|---|
| SIFTsmall | [vecdata/siftsmall](https://huggingface.co/datasets/vecdata/siftsmall)，归档下载版本 `3106e1b83049c44713b1ce06942d0ab474bbdfb6`；原始提供方TEXMEX | 10,000条128维图像描述子，前期消融 |
| SIFT1M | [zjd2000/ANN_SIFT](https://huggingface.co/datasets/zjd2000/ANN_SIFT/tree/main)，归档版本 `8956d7e088e0b79b6901c234632e801fa37d731d`；原始提供方TEXMEX | 1,000,000条128维图像描述子 |
| GloVe25 | [ANN-Benchmarks数据列表](https://github.com/erikbern/ann-benchmarks/blob/main/README.md)的 `glove-25-angular.hdf5`，来源为Stanford GloVe Twitter 27B词向量 | 1,183,514条25维词向量及10,000条查询 |

SIFT1M文件名 `sift.tar.gz.part` 是已完整校验的归档，不能作为下载碎片删除。GloVe经float64归一化后保存float32，比较的是所存向量的精确平方L2距离，重新计算参考答案。各文件大小及SHA256见 `DATA_MANIFEST.json`；处理实现见 `baseline/prepare_*.py`。

## 已核实的许可信息

- **GloVe：上游许可已找到。** [Stanford官方项目页](https://nlp.stanford.edu/projects/glove/)明确将预训练向量按PDDL v1.0提供。[PDDL原文](https://opendatacommons.org/licenses/pddl/1-0/)说明其共享和使用安排。ANN-Benchmarks的[转换代码](https://github.com/erikbern/ann-benchmarks/blob/main/ann_benchmarks/datasets.py)将GloVe25来源对应到 `glove.twitter.27B.zip`；这条来源链与本项目使用的HDF5数据集名称、维度和划分相符。没有用ANN-Benchmarks代码许可证替代数据许可。
- **SIFTsmall：只核实到镜像标注。** 当前[镜像数据卡](https://huggingface.co/datasets/vecdata/siftsmall/blob/main/README.md)标注MIT；它是镜像上传者的声明，不等于已经核实TEXMEX原作者授权，也不能直接作为所下载固定历史版本的授权证明。
- **SIFT1M：明确的上游再分发许可尚未核实。** 镜像文件列表没有提供可确认的许可声明；本次访问[TEXMEX原站](http://corpus-texmex.irisa.fr/)失败。归档内部只有向量及参考答案文件，没有LICENSE或README授权文件。其他SIFT数据集、SIFT算法实现或第三方论文的许可证不能替代这一归档的授权。

**当前状态：全部负载已经保留，来源与哈希已核对；SIFT两项的上游再分发依据仍待补充。公开下载不自动等于授予再分发许可，本说明不将它们改标为MIT、CC0或CC BY。** 如取得原作者或授权提供方的明确许可，应把原文、来源及适用数据版本补入本文件。此状态也记录在 `DATA_RIGHTS_STATUS.json`。

## 引用与第三方依赖

SIFT/TEXMEX：Hervé Jégou、Matthijs Douze、Cordelia Schmid，Product Quantization for Nearest Neighbor Search，IEEE TPAMI，2011。
GloVe：Jeffrey Pennington、Richard Socher、Christopher D. Manning，GloVe: Global Vectors for Word Representation，EMNLP，2014。
ANN-Benchmarks提供HDF5整理及基准数据划分。

Faiss、NumPy、OpenBLAS、Z3、h5py、matplotlib、ReportLab等依赖保留各自许可。作者尚未为自研代码指定开源许可证；公开可见性与授予开源许可证是两回事。
