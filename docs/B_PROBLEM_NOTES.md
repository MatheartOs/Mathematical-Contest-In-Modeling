# B Problem Notes

## Problem Understanding

B 题是“智能办公场景下多源异构文件识别与治理优化”。需要围绕四个数据集完成三层任务：

1. 对数据集 1 的历史真实文件做多源异构特征挖掘、分类，并归纳主题。
2. 将数据集 2、数据集 3 的后续流入数据迁移归入问题一建立的主题体系，并评价合理性、可解释性和迁移适用性；对多主题或无法明确归类的数据提出识别与处理方式。
3. 结合归类结果，从紧急程度、错分风险、复核必要性三方面分级并设置权重；在数据集 4 的资源约束下决定是否人工复核和复核优先顺序。

## Confirmed Lightweight Data Shape

当前只做了轻量结构确认，未全量读取文件正文。

| 数据集 | 结构 |
| --- | --- |
| 数据集 1 | 历史真实文件数据，共 3396 个文件，含 `.docx/.jpg/.pdf/.png/.txt/.xlsx` |
| 数据集 2 | 后续流入半结构化记录数据，共 1001 个文件，含 `.docx/.pdf/.png/.txt/.xlsx` |
| 数据集 3 | Excel 表，3518 条记录，字段为 `文件编号`、`正文片段`、`时间信息` |
| 数据集 4 | Excel 表，3 个资源场景：S1/S2/S3，含每日人工工时、自动归档上限、人工复核上限 |

## Initial Algorithm

当前项目先采用“可解释基线 + 后续可替换增强模型”的路线：

1. 异构读取层：将 `txt/docx/xlsx/pdf/image` 统一转为 `DocumentRecord`。图片先提取尺寸、亮度等元数据，不做 OCR；PDF 优先使用 `pypdf`，未安装时使用内置轻量 ToUnicode 提取器。
2. 特征层：文本长度、字符比例、文件大小、扩展名、关键词组计数。关键词组覆盖资金、紧急、政策、教育、科技、政府、健康、环境、人事、法律等方向。
3. 问题一：使用字符级 TF-IDF + KMeans 对历史文件建立主题簇，并输出每簇高权重词作为主题命名依据。
4. 问题二：将新数据投影到同一 TF-IDF 空间，按聚类中心距离分类；用置信度和 margin 判定模糊样本。
5. 问题三：融合紧急关键词、资金关键词、分类置信度、模糊标记，计算人工复核优先级；在 S1/S2/S3 资源约束下截取复核队列。

## Guardrails

默认脚本只跑小样本：

```powershell
.\.venv\Scripts\python.exe scripts\inspect_b_data.py
.\.venv\Scripts\python.exe scripts\run_b_pipeline_sample.py
```

小样本输出只用于检查读取器和流程，不代表最终分类质量。

全量实验需要另写脚本或显式扩大参数，不建议在没有缓存和日志设计前直接全量跑。

当前已提供正式链路：

```powershell
.\.venv\Scripts\python.exe scripts\run_b_cleaning.py --output-dir outputs\b_problem\cleaning_v2
.\.venv\Scripts\python.exe scripts\run_b_pipeline.py --clusters 10 --max-chars 30000 --max-file-mb 25 --cleaning-dir outputs\b_problem\cleaning_v2 --output-dir outputs\b_problem\run_cleaned_v2
```

清洗脚本按最新流程文档输出 `file_manifest.csv`、`document_index.csv`、`document_blocks.jsonl`、`parse_log.csv`、`ocr_log.csv`、`error_log.txt`、`business_dictionary.json` 和 `manual_check_list.csv`。主链路不再直接从原文件抽文本，而是基于 `document_index.csv` 构建问题一的历史主题体系。

PaddleOCR 接入说明：

- 使用 PP-OCRv5 server det/rec 本地模型。
- 当前 Windows + 中文路径下，Paddle 推理读取项目内模型会失败；代码优先使用 `C:\mcm_paddleocr_models` 下的 ASCII 路径模型。
- CPU 推理需设置 `enable_mkldnn=False`，否则 PP-OCRv5 在当前 PaddlePaddle 3.3.1 环境下会触发 oneDNN/PIR 兼容问题。
- OCR 输出会写入 `document_blocks.jsonl` 的 `image_text` 块，以及 `logs/ocr_log.csv`。
