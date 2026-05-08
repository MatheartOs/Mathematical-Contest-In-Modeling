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
| `src/mcm_b/features.py` | 可解释文本与文件特征 |
| `src/mcm_b/modeling.py` | TF-IDF + KMeans 主题发现与迁移分类 |
| `src/mcm_b/risk.py` | 人工复核优先级与资源场景队列 |
| `scripts/inspect_b_data.py` | 数据结构和读取器小样本验证 |
| `scripts/run_b_pipeline_sample.py` | 端到端小样本基线 |
| `outputs/b_problem/` | 运行输出，不入库 |

## Important Caution

数据集 1 有 3396 个文件，数据集 2 有 1001 个文件，其中不少 PDF/XLSX 很大。除非明确需要，不要递归抽取全文。

建议迭代顺序：

1. 先跑小样本确认读取质量。
2. 增加缓存层，把每个文件的抽取结果保存为独立 JSONL/Parquet。
3. 再做分批全量抽取。
4. 最后才做模型调参、主题命名和论文图表。

## Known Environment Note

尝试安装 `pypdf` 和 `python-docx` 时，当前网络出现 SSL 中断。代码已用标准库实现 docx 读取，并为 PDF 提供内置轻量 fallback；后续若网络恢复，可安装 `pypdf` 提高 PDF 文本抽取稳定性。
