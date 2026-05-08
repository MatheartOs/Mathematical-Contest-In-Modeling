# Agent Handoff

## Current Branch

本轮项目构建在分支：

```text
agent/b-problem-bootstrap
```

不要直接在 `main` 上继续大改。接手前先运行：

```powershell
git status --short --branch
git fetch origin
```

## What Was Done

1. 阅读了仓库 README 和 B 题题面要点。
2. 轻量确认了数据集结构，没有全量分析文件正文。
3. 新建 `src/mcm_b/` 包，按路径、读取、特征、建模、复核优先级分层。
4. 新建两个脚本：
   - `scripts/inspect_b_data.py`：默认各抽 8 个文件 + 数据集 3 前 12 行。
   - `scripts/run_b_pipeline_sample.py`：默认历史 60 个、新文件 30 个、数据集 3 前 30 行。
5. 新建 B 题说明、协作流程和算法文档。

## Verification Completed

本轮已在小样本和基础环境上验证：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts\inspect_b_data.py --sample-per-dataset 2 --dataset3-rows 3 --max-chars 2000
.\.venv\Scripts\python.exe scripts\run_b_pipeline_sample.py --history-sample-size 12 --new-file-sample-size 6 --dataset3-rows 6 --clusters 4 --max-chars 3000
.\.venv\Scripts\python.exe math_test.py
.\.venv\Scripts\python.exe verify_science_stack.py
.\.venv\Scripts\python.exe -m compileall src scripts tests
```

注意：端到端样本只证明链路闭合，样本太小，聚类主题词不能作为论文结论。

## Project Map

| 路径 | 作用 |
| --- | --- |
| `src/mcm_b/paths.py` | 数据路径和输出路径配置，可用 `MCM_B_DATA_ROOT` 覆盖 |
| `src/mcm_b/readers.py` | 异构文件轻量读取，统一输出 `DocumentRecord` |
| `src/mcm_b/cleaning.py` | 按最新清洗流程文档生成文件画像、内容块、日志和人工检查表 |
| `src/mcm_b/features.py` | 可解释文本与文件特征 |
| `src/mcm_b/modeling.py` | TF-IDF + KMeans 主题发现与迁移分类 |
| `src/mcm_b/risk.py` | 人工复核优先级与资源场景队列 |
| `scripts/inspect_b_data.py` | 数据结构和读取器小样本验证 |
| `scripts/run_b_pipeline_sample.py` | 端到端小样本基线 |
| `scripts/run_b_pipeline.py` | 带缓存的正式问题链路，输出题目结果表和图 |
| `scripts/run_b_cleaning.py` | 单独运行标准数据清洗流程 |
| `outputs/b_problem/` | 运行输出，不入库 |

## Current Full Run

用户已将完整数据放到项目根目录 `B题数据集/`。路径配置现在优先读取项目内数据，找不到时才回退到平级中文目录。

最新清洗规范来自：

```text
docs/多源异构文件数据清洗流程说明文档.md
```

当前正式清洗结果在：

```text
outputs/b_problem/cleaning_v2/
```

当前正式建模结果在：

```text
outputs/b_problem/run_cleaned_v2/
```

运行命令：

```powershell
.\.venv\Scripts\python.exe scripts\run_b_pipeline.py --clusters 10 --max-chars 30000 --max-file-mb 25 --cleaning-dir outputs\b_problem\cleaning_v2 --output-dir outputs\b_problem\run_cleaned_v2 --force-cleaning
```

关键结果：

- 清洗总文档：7916 条，其中 dataset1=3396、dataset2=1001、dataset3=3518、dataset4=1。
- 清洗分流：图片 OCR 待处理 1990 条，图片侧车 TXT 1127 条，docx 617 条，普通 txt 351 条，excel 176 条，text PDF 76 条。
- 数据集 1：图片和“图片名称/图片编号/下载URL”类侧车文本已保留在清洗索引和块表中，但不进入问题一主题建模。
- 数据集 2：1001 条，可归类文本 923 条。
- 数据集 3：3518 条。
- 新数据归类总数：4425 条。
- 模糊/需复核候选：2784/3614 条。
- S1/S2/S3 复核队列大小：200/266/333。

## Important Caution

数据集 1 有 3396 个文件，数据集 2 有 1001 个文件，其中不少 PDF/XLSX 很大。除非明确需要，不要递归抽取全文。

建议迭代顺序：

1. 先跑小样本确认读取质量。
2. 增加缓存层，把每个文件的抽取结果保存为独立 JSONL/Parquet。
3. 再做分批全量抽取。
4. 最后才做模型调参、主题命名和论文图表。

## Known Environment Note

尝试安装 `pypdf` 和 `python-docx` 时，当前网络出现 SSL 中断。代码已用标准库实现 docx 读取，并为 PDF 提供内置轻量 fallback；后续若网络恢复，可安装 `pypdf` 提高 PDF 文本抽取稳定性。
