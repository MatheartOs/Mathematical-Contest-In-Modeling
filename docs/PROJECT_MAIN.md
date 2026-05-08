# B 题项目主文档

> 本文档是当前项目的事实源和交接入口。后续每次执行重要命令、得到新结果、修改参数或调整算法，都必须同步更新本文档，再继续推进任务。

## 当前问题定义

竞赛题目为 2026 年第十一届数维杯大学生数学建模挑战赛（春季赛）B 题：智能办公场景下多源异构文件识别与治理优化。

需要解决三类问题：

1. 问题一：对数据集 1 的历史真实文件进行多源异构特征挖掘、分类，并归纳主题体系。
2. 问题二：将数据集 2 和数据集 3 的后续流入数据归入问题一建立的分类体系，并评价归属判断的合理性、可解释性和迁移适用性。
3. 问题三：结合归类结果，从紧急程度、错分风险、复核必要性三方面分级，在数据集 4 的资源约束下决定是否人工复核及复核优先顺序。

当前阶段重点：先按最新《多源异构文件数据清洗流程说明文档》完成统一文件画像构建，再在此基础上做问题一建模。

## 已完成内容

- 已建立 Python 项目结构和 B 题模块。
- 已将完整 `B题数据集/` 放入项目根目录，并加入 `.gitignore`，不提交原始数据。
- 已建立清洗核心模块：`src/mcm_b/cleaning.py`。
- 已建立正式清洗脚本：`scripts/run_b_cleaning.py`。
- 已重构主链路：`scripts/run_b_pipeline.py` 现在基于 `document_index.csv`，不再直接绕过清洗结果读取原文件。
- 已接入 PaddleOCR，仅使用 PaddleOCR，不使用其他 OCR。
- 已验证 PP-OCRv5 server det/rec 可在 CPU 上运行，但需使用 ASCII 模型路径并关闭 MKLDNN。
- 已完成 OCR 小样本验证，log 中已出现 `image_paddleocr`。
- 已提交关键节点：
  - `f6f7ffb feat: bootstrap B problem modeling pipeline`
  - `79ecde1 feat: run full B problem pipeline`
  - `25ee04b feat: refactor around document cleaning workflow`
  - `d5a07dc feat: add PaddleOCR image cleaning`

## 数据清洗方案

清洗目标不是只提取纯文本，而是生成统一、可追踪的文件画像：

```text
D_i = {T_i, L_i, S_i, B_i, Q_i}
```

其中：

- `T_i`：标题、正文、表格语义文本、OCR 文本。
- `L_i`：页码、块类型、bbox、阅读顺序。
- `S_i`：段落数、表格数、图片数、标题数等结构特征。
- `B_i`：资金、项目、通知、合同、截止、紧急等业务属性。
- `Q_i`：解析方式、OCR 置信度、解析质量、人工检查原因。

标准交付物：

- `processed/file_manifest.csv`
- `processed/document_index.csv`
- `processed/document_blocks.jsonl`
- `logs/parse_log.csv`
- `logs/ocr_log.csv`
- `logs/error_log.txt`
- `processed/business_dictionary.json`
- `processed/manual_check_list.csv`

特殊分流规则：

- 图片文件：使用 PaddleOCR，成功时 `parse_method=image_paddleocr`。
- 图片侧车 TXT：包含 `图片名称:`、`图片编号:`、`下载URL:` 的 TXT 标记为 `image_sidecar_txt:*`，保留到索引和块表，但不作为有效历史主题文本。
- 扫描型 PDF：当前仍标记为 OCR 待处理，尚未实现 PDF 转图片 OCR。
- 超大文件：超过 `--max-file-mb` 时只保留元数据。

## 文件结构

核心代码：

```text
src/mcm_b/
├── cleaning.py    # 最新清洗流程核心
├── features.py    # 旧版特征逻辑，部分仍被主链路复用关键词组
├── modeling.py    # TF-IDF + KMeans 主题发现/迁移分类
├── paths.py       # 数据路径配置
├── readers.py     # 旧版读取工具，逐步退居辅助
└── risk.py        # 问题三复核优先级
```

脚本：

```text
scripts/
├── run_b_cleaning.py         # 单独运行清洗流程
├── run_b_pipeline.py         # 基于清洗产物运行问题一/二/三链路
├── inspect_b_data.py         # 轻量数据探查
└── run_b_pipeline_sample.py  # 旧小样本链路
```

重要输出：

```text
outputs/b_problem/cleaning_v2/          # 无 OCR 的清洗 v2 结果
outputs/b_problem/run_cleaned_v2/       # 基于 cleaning_v2 的建模结果
outputs/b_problem/cleaning_ocr_smoke/   # PaddleOCR 小样本验证结果
```

PaddleOCR 模型：

```text
C:\mcm_paddleocr_models\det\PP-OCRv5_server_det_infer
C:\mcm_paddleocr_models\rec\PP-OCRv5_server_rec_infer
```

项目内也有 `models/paddleocr/`，但当前中文项目路径会导致 Paddle 底层读取模型失败，因此代码优先使用上面的 ASCII 路径。`models/` 和 `PP-OCRv5/` 已加入 `.gitignore`。

## 关键算法思路

清洗阶段：

1. 扫描所有数据集，统一编号为 `D1_0001`、`D2_0001`、`D3_0001` 等。
2. 按文件类型分流：TXT、DOCX、XLSX、PDF、图片、数据集 3 行记录。
3. 生成块级结构：段落块、表格块、图片元信息块、OCR 文本块。
4. 标准化文本：全角转半角、统一空白、业务同义词归一。
5. 抽取日期、截止时间、金额、机构、联系方式、业务关键词。
6. 标记业务属性：`has_notice`、`has_meeting`、`has_project`、`has_money`、`has_contract`、`has_personnel`、`has_deadline`、`has_urgent`。
7. 计算 `parse_quality` 和 `need_manual_check`。

建模阶段：

1. 从 `document_index.csv` 构建建模文本：`title + clean_text + business_keywords`。
2. 对数据集 1 中质量足够的历史文件做字符级 TF-IDF。
3. 用 KMeans 建立问题一主题体系。
4. 对数据集 2/3 投影到同一空间，根据主题中心距离进行归属判断。
5. 用距离 margin 估计分类置信度和模糊性。
6. 问题三用紧急程度、错分风险、复核必要性计算 `priority_score`，并按数据集 4 的 S1/S2/S3 资源约束生成复核队列。

## 已验证结论

环境：

- PaddlePaddle: `3.3.1`
- PaddleOCR: `3.5.0`
- 设备：CPU
- PP-OCRv5 server det/rec 模型可用。

关键技术结论：

- Paddle 在当前中文项目路径下读取本地模型会失败，报 JSON parse empty input。
- 复制到 `C:\mcm_paddleocr_models` 后可初始化。
- PP-OCRv5 在当前 CPU/oneDNN 后端下需要 `enable_mkldnn=False`，否则报 oneDNN/PIR 兼容错误。
- OCR 小样本验证成功，`D1_0001.jpg` 和 `D1_0007.jpg` 已识别。

OCR 小样本结果：

```text
outputs/b_problem/cleaning_ocr_smoke/logs/parse_log.csv:
D1_0001 parse_method=image_paddleocr text_length=1155
D1_0007 parse_method=image_paddleocr text_length=1584

outputs/b_problem/cleaning_ocr_smoke/logs/ocr_log.csv:
D1_0001 ocr_confidence=0.988576 ocr_text_length=1155
D1_0007 ocr_confidence=0.998192 ocr_text_length=1584
```

`document_blocks.jsonl` 已写入：

```text
block_type=image_text
source=paddleocr
bbox=[...]
confidence=...
```

无 OCR 的 `cleaning_v2` 分流结果：

```text
dataset3_row_parse: 3518
image_ocr_pending: 1990
image_sidecar_txt:utf-8-sig: 1127
docx_parse: 617
txt_parse:utf-8-sig: 351
excel_parse: 176
text_pdf: 76
scanned_pdf_ocr_pending: 54
scanned_pdf_text_low: 5
metadata_only: 2
```

## TODO

高优先级：

- [ ] 跑完整 PaddleOCR 清洗：输出 `outputs/b_problem/cleaning_ocr_full/`。
- [ ] 基于 `cleaning_ocr_full` 跑主链路：输出 `outputs/b_problem/run_ocr_full/`。
- [ ] 检查 OCR 后问题一主题是否比 `run_cleaned_v2` 更合理。
- [ ] 更新论文可用的清洗统计表和质量控制说明。

中优先级：

- [ ] 给 PDF 扫描页增加“PDF 转图片后 PaddleOCR”的处理。
- [ ] 对 OCR 文本做页眉页脚/表格噪声清理。
- [ ] 对 Excel 表格语义文本增强，避免表格字段主导过强。
- [ ] 根据人工抽查结果调整 `parse_quality` 规则。

低优先级：

- [ ] 增加可视化清洗质量图。
- [ ] 增加抽样人工检查模板。
- [ ] 将旧 `readers.py` 与旧样本脚本进一步清理或标注为 legacy。

## 参数定义

清洗脚本 `scripts/run_b_cleaning.py`：

| 参数 | 当前含义 | 建议值 |
| --- | --- | --- |
| `--output-dir` | 清洗结果输出目录 | `outputs\b_problem\cleaning_ocr_full` |
| `--max-chars` | 单文件最多保留文本字符数 | `30000` |
| `--max-file-mb` | 超过该大小只保留元数据 | `25` |
| `--dataset1-limit` | 数据集 1 限量调试，0 为全量 | 调试用小数，全量用 0 |
| `--dataset2-limit` | 数据集 2 限量调试，0 为全量 | 调试用小数，全量用 0 |
| `--dataset3-limit` | 数据集 3 限量调试，0 为全量 | 调试用小数，全量用 0 |

主链路 `scripts/run_b_pipeline.py`：

| 参数 | 当前含义 | 建议值 |
| --- | --- | --- |
| `--cleaning-dir` | 输入清洗产物目录 | `outputs\b_problem\cleaning_ocr_full` |
| `--output-dir` | 建模结果输出目录 | `outputs\b_problem\run_ocr_full` |
| `--clusters` | KMeans 主题数 | `10`，后续可调 |
| `--max-chars` | 若需重跑清洗时的字符上限 | `30000` |
| `--max-file-mb` | 若需重跑清洗时的文件大小上限 | `25` |
| `--force-cleaning` | 是否强制重跑清洗 | 全量 OCR 时慎用 |

PaddleOCR 模型环境变量：

```powershell
$env:PADDLEOCR_DET_DIR='C:\mcm_paddleocr_models\det\PP-OCRv5_server_det_infer'
$env:PADDLEOCR_REC_DIR='C:\mcm_paddleocr_models\rec\PP-OCRv5_server_rec_infer'
```

## 中间结论

- 当前没有 OCR 的 `run_cleaned_v2` 只能作为清洗结构验证和基线结果，不能作为最终问题一主题结论。
- OCR 对数据集 1 很关键，因为历史数据中大量文件是图片或图片相关说明；不做 OCR 会导致历史主题体系偏向少量 DOCX/PDF/XLSX/TXT。
- 图片侧车 TXT 必须保留但不能直接作为主题文本，否则“图片名称/下载URL/统计表编号”会污染聚类。
- PaddleOCR 小样本效果较好，表格图片能识别出标题、字段和大量单元格文本，适合进入问题一画像。
- 全量 OCR 预计耗时很长，建议单独长跑并保留日志，不要在同一轮中频繁强制重跑。

## 最近命令记录

```powershell
.\.venv\Scripts\python.exe scripts\run_b_cleaning.py --dataset1-limit 8 --dataset2-limit 2 --dataset3-limit 2 --output-dir outputs\b_problem\cleaning_ocr_smoke --max-chars 8000 --max-file-mb 25
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe math_test.py
Get-Content -TotalCount 80 docs\PROJECT_MAIN.md
git status --short --branch
```

最近验证状态：

```text
unittest: OK, 3 tests
math_test.py: OK
git branch: agent/b-problem-bootstrap
last commit: d5a07dc feat: add PaddleOCR image cleaning
2026-05-08 12:?? created docs/PROJECT_MAIN.md as required project memory.
```
