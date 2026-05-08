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

- PaddlePaddle GPU: `paddlepaddle-gpu==3.0.0.dev20250717`，`paddle.__version__ == 3.0.0`
- PaddleOCR: `3.5.0`
- 设备：`gpu:0`
- GPU：NVIDIA GeForce RTX 5090 D，Driver `596.21`，`nvidia-smi` 显示 CUDA `13.2`
- Paddle CUDA：`paddle.device.is_compiled_with_cuda() == True`
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

- [x] 评估并尝试安装 `paddlepaddle-gpu`，将 PaddleOCR 全量清洗从 CPU 切换到 GPU。
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
.\.venv\Scripts\python.exe -m pip uninstall -y paddlepaddle
.\.venv\Scripts\python.exe -m pip install "https://paddle-whl.bj.bcebos.com/nightly/cu129/paddlepaddle_gpu/paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl"
Get-ChildItem Env:*proxy* | Format-Table -AutoSize
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip config list -v
netsh winhttp show proxy
.\.venv\Scripts\python.exe -m pip install --proxy "" --trusted-host paddle-whl.bj.bcebos.com "https://paddle-whl.bj.bcebos.com/nightly/cu129/paddlepaddle_gpu/paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl"
$env:NO_PROXY='*'; $env:no_proxy='*'; .\.venv\Scripts\python.exe -m pip install --trusted-host paddle-whl.bj.bcebos.com "https://paddle-whl.bj.bcebos.com/nightly/cu129/paddlepaddle_gpu/paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl"
$env:NO_PROXY='*'; $env:no_proxy='*'; .\.venv\Scripts\python.exe -m pip install --trusted-host paddle-qa.bj.bcebos.com "https://paddle-qa.bj.bcebos.com/paddle-pipeline/Develop-GpuSomeFreeze-WinAll-CP310-Cuda129-Py310-NewVersion/paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl"
$env:NO_PROXY='*'; $env:no_proxy='*'; .\.venv\Scripts\python.exe -m pip install --trusted-host paddle-qa.bj.bcebos.com "https://paddle-qa.bj.bcebos.com/paddle-pipeline/Develop-TagBuild-Training-Windows-Gpu-Cuda12.9-Cudnn9.9-Trt10.5-Mkl-Avx-VS2019-SelfBuiltPypiUse/86d658f56ebf3a5a7b2b33ace48f22d10680d311/paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl"
@'
import paddle
print('paddle_version', paddle.__version__)
print('compiled_cuda', paddle.device.is_compiled_with_cuda())
paddle.set_device('gpu:0')
print('device', paddle.device.get_device())
print('tensor', (paddle.to_tensor([1.0, 2.0, 3.0]) * 2).numpy().tolist())
'@ | .\.venv\Scripts\python.exe -
rg -n "PaddleOCR|paddle|device|mkldnn|ocr" src\mcm_b\cleaning.py
Get-Content -Path src\mcm_b\cleaning.py | Select-Object -Skip 800 -First 120
.\.venv\Scripts\python.exe -m pip show paddlepaddle-gpu paddlepaddle paddleocr
@'
import inspect
from paddleocr import PaddleOCR
print(inspect.signature(PaddleOCR.__init__))
'@ | .\.venv\Scripts\python.exe -
.\.venv\Scripts\python.exe scripts\run_b_cleaning.py --dataset1-limit 8 --dataset2-limit 2 --dataset3-limit 2 --output-dir outputs\b_problem\cleaning_gpu_smoke --max-chars 8000 --max-file-mb 25
Import-Csv outputs\b_problem\cleaning_gpu_smoke\logs\parse_log.csv | Where-Object { $_.parse_method -like '*ocr*' -or $_.parse_method -like '*paddle*' } | Format-Table file_id,file_name,parse_method,parse_success,text_length,error_message -AutoSize
Import-Csv outputs\b_problem\cleaning_gpu_smoke\logs\ocr_log.csv | Format-Table file_id,page,ocr_used,ocr_confidence,ocr_text_length,ocr_error -AutoSize
git diff -- src\mcm_b\cleaning.py docs\PROJECT_MAIN.md
.\.venv\Scripts\python.exe -m unittest discover -s tests
$env:PADDLEOCR_DEVICE='gpu:0'; .\.venv\Scripts\python.exe scripts\run_b_cleaning.py --output-dir outputs\b_problem\cleaning_ocr_full --max-chars 30000 --max-file-mb 25
Import-Csv outputs\b_problem\cleaning_ocr_full\logs\parse_log.csv | Group-Object parse_method | Sort-Object Count -Descending | Select-Object Count,Name | Format-Table -AutoSize
Import-Csv outputs\b_problem\cleaning_ocr_full\logs\ocr_log.csv | Select-Object -First 8 | Format-Table file_id,page,ocr_used,ocr_confidence,ocr_text_length,ocr_error -AutoSize
Import-Csv outputs\b_problem\cleaning_ocr_full\processed\manual_check_list.csv | Group-Object manual_check_reason | Sort-Object Count -Descending | Select-Object Count,Name | Format-Table -AutoSize
Import-Csv outputs\b_problem\cleaning_ocr_full\logs\parse_log.csv | Where-Object { $_.parse_success -eq '0' } | Group-Object parse_method,error_message | Sort-Object Count -Descending | Select-Object Count,Name | Format-Table -Wrap -AutoSize
Get-ChildItem outputs\b_problem\cleaning_ocr_full -Recurse -File | Select-Object @{Name='RelativePath';Expression={$_.FullName.Replace((Resolve-Path outputs\b_problem\cleaning_ocr_full).Path + '\','')}},@{Name='MB';Expression={[math]::Round($_.Length/1MB,2)}} | Sort-Object RelativePath | Format-Table -AutoSize
git status --short
Get-Content outputs\b_problem\cleaning_ocr_full\cleaning_summary.json
@'
import pandas as pd
from pathlib import Path
base = Path('outputs/b_problem/cleaning_ocr_full')
for rel in ['processed/file_manifest.csv','processed/document_index.csv','processed/manual_check_list.csv','logs/parse_log.csv','logs/ocr_log.csv']:
    p = base / rel
    df = pd.read_csv(p, nrows=0)
    print(f'[{rel}]')
    print(', '.join(df.columns))
'@ | .\.venv\Scripts\python.exe -
Get-Content outputs\b_problem\cleaning_ocr_full\processed\business_dictionary.json -TotalCount 120
(Get-Content docs\数据清洗环节论文参考说明.md | Measure-Object -Line).Lines
Select-String -Path docs\数据清洗环节论文参考说明.md -Pattern '^## ' | Select-Object LineNumber,Line | Format-Table -AutoSize
git status --short
```

下一步计划：

```text
2026-05-08: 用户希望将 OCR 跑在 GPU 上。需要先检查 NVIDIA 驱动/CUDA 环境，再决定是否安装 paddlepaddle-gpu。
2026-05-08: 已检测到 RTX 5090 D + Driver 596.21 + CUDA 13.2；准备尝试安装 CUDA 13.0 对应的 paddlepaddle-gpu==3.3.0。
2026-05-08: 官方 Windows 3.3 pip 文档提供 paddlepaddle-gpu==3.3.0 的 cu118/cu126/cu129；官方 PaddleX 3.3 文档额外说明 Windows + NVIDIA 50 系列 GPU 标准安装不完全支持，需使用专门适配 wheel。当前 GPU 为 RTX 5090 D，因此改为优先尝试 Python 3.10 对应的 50 系列 Windows 适配包 paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl。
2026-05-08: 安装策略：先卸载 CPU 版 paddlepaddle，再安装上述 50 系列 GPU wheel；若失败则记录错误并让人工接管安装，不继续随机尝试其他 OCR 或不明来源包。
2026-05-08: 第一次安装 50 系列 GPU wheel 失败，pip 报 ProxyError / SSLEOFError，说明卡在代理或 TLS 握手，尚未下载 wheel。下一步检查代理环境变量，并尝试 trusted-host 方式。
2026-05-08: `Get-ChildItem Env:*proxy*` 未发现显式代理环境变量；pip 版本为 26.1.1。下一步尝试 `--trusted-host paddle-whl.bj.bcebos.com`。
2026-05-08: 用户确认网络问题由代理导致。后续不更换 Paddle 版本或 OCR 方案，先检查 pip/system 代理配置，优先尝试在当前 pip 命令中临时绕开代理。
2026-05-08: `pip config list -v` 只显示配置文件搜索路径，没有代理项；`netsh winhttp show proxy` 显示 Direct access。代理更可能来自 Windows 用户级网络设置或网络软件透明接管。下一步使用 `pip install --proxy "" --trusted-host paddle-whl.bj.bcebos.com ...` 明确尝试直连。
2026-05-08: `pip install --proxy "" ...` 失败，pip 将空 proxy 后面的 `--trusted-host` 误解析为代理主机，报 `Failed to resolve '--trusted-host'`。下一步改用当前进程环境变量 `NO_PROXY=*` / `no_proxy=*` 绕过代理。
2026-05-08: 设置 `NO_PROXY=*` 后代理问题消失，但 `paddle-whl.bj.bcebos.com/nightly/cu129/...` 路径返回 HTTP 404。随后尝试的 `Develop-GpuSomeFreeze...` 路径也返回 404。官方 PaddleX/PaddleOCR 3.3 最新文档显示完整 50 系列 Windows cp310 wheel 地址为 `https://paddle-qa.bj.bcebos.com/paddle-pipeline/Develop-TagBuild-Training-Windows-Gpu-Cuda12.9-Cudnn9.9-Trt10.5-Mkl-Avx-VS2019-SelfBuiltPypiUse/86d658f56ebf3a5a7b2b33ace48f22d10680d311/paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl`，下一步按该地址安装。
2026-05-08: GPU wheel 安装成功：`paddlepaddle-gpu==3.0.0.dev20250717`，同时安装 `nvidia-cuda-runtime-cu12==12.9.37`、`nvidia-cudnn-cu12==9.9.0.52`、`nvidia-cublas-cu12==12.9.0.13`、`nvidia-cufft-cu12==11.4.0.6`、`nvidia-curand-cu12==10.3.10.19`、`nvidia-cusolver-cu12==11.7.4.40`、`nvidia-cusparse-cu12==12.5.9.5`、`nvidia-nvjitlink-cu12==12.9.86`。下一步验证 `paddle.device.is_compiled_with_cuda()` 和 `paddle.set_device("gpu:0")`。
2026-05-08: CUDA 验证通过：`paddle.__version__ == 3.0.0`，`paddle.device.is_compiled_with_cuda() == True`，`paddle.set_device("gpu:0")` 成功，简单 tensor 计算返回 `[2.0, 4.0, 6.0]`。日志显示 GPU Compute Capability 12.0、Driver API 13.2、Runtime API 12.9。
2026-05-08: 当前包状态：`paddlepaddle-gpu 3.0.0.dev20250717`、`paddleocr 3.5.0`，CPU 包 `paddlepaddle` 已不存在。`cleaning.py` 的 PaddleOCR 初始化尚未显式传入 device，仅传入模型目录和 `enable_mkldnn=False`，需要改为自动选择 GPU 并可用 `PADDLEOCR_DEVICE` 覆盖。
2026-05-08: PaddleOCR 3.5.0 构造函数签名含 `**kwargs`，可传入后端参数。下一步在 `cleaning.py` 中加入 `_resolve_paddleocr_device()`，默认 CUDA 可用时使用 `gpu:0`，否则使用 `cpu`，并允许 `PADDLEOCR_DEVICE` 覆盖。
2026-05-08: 已修改 `src/mcm_b/cleaning.py`：`_paddleocr_engine()` 现在调用 `_resolve_paddleocr_device()`，默认 CUDA 可用时执行 `paddle.set_device("gpu:0")` 并向 PaddleOCR 传入 `device="gpu:0"`；可通过环境变量 `PADDLEOCR_DEVICE` 覆盖，回退值为 `cpu`。`enable_mkldnn=False` 保留。
2026-05-08: GPU OCR smoke 清洗完成：输出目录 `outputs\b_problem\cleaning_gpu_smoke`，耗时 `6.338s`，`document_count=13`，`block_count=1267`，`parse_success_count=8`，`need_manual_check=10`。日志显示加载本地 PP-OCRv5 server det/rec 模型；后续读取 parse/ocr log 核验 OCR 结果。
2026-05-08: 已核验 `outputs\b_problem\cleaning_gpu_smoke\logs\parse_log.csv` 和 `ocr_log.csv`：`D1_0001`、`D1_0007` 均为 `image_paddleocr`，`parse_success=1`，OCR 文本长度分别为 `1155`、`1584`，平均置信度分别约 `0.988503`、`0.998186`。
2026-05-08: 下一步运行 `.\.venv\Scripts\python.exe -m unittest discover -s tests`，确认 Paddle GPU 环境切换后已有测试仍通过。
2026-05-08: 单元测试通过：`Ran 3 tests`，`OK`。
2026-05-08: 准备启动全量 OCR 清洗，目标输出目录 `outputs\b_problem\cleaning_ocr_full`，参数 `--max-chars 30000 --max-file-mb 25`，显式设置 `$env:PADDLEOCR_DEVICE='gpu:0'`。本次会处理全部数据，不设置 dataset limit。
2026-05-08: 全量 OCR 清洗完成：输出目录 `outputs\b_problem\cleaning_ocr_full`，耗时 `1268.986s`，`document_count=7916`，`block_count=598480`，`parse_success_count=6733`，`need_manual_check=6781`。期间加载 PP-OCRv5 server det/rec 本地模型，部分超长/超宽图片被 PaddleOCR 自动缩放到 `max_side_limit=4000` 内。
2026-05-08: 全量 `parse_log.csv` 分流统计：`dataset3_row_parse=3518`，`image_paddleocr=1990`，`image_sidecar_txt:utf-8-sig=1127`，`docx_parse=617`，`txt_parse:utf-8-sig=351`，`excel_parse=176`，`text_pdf=76`，`scanned_pdf_ocr_pending=54`，`scanned_pdf_text_low=5`，`metadata_only=2`。说明图片文件已从旧版 `image_ocr_pending` 切换为 PaddleOCR 实际识别；扫描 PDF 仍是 TODO。
2026-05-08: 全量 `ocr_log.csv` 汇总：`ocr_rows=1990`，`success_rows=1990`，`avg_confidence=0.989121`，`avg_text_length=1437.17`，`min_confidence=0.46594`，`max_confidence=0.999895`。前几条如 `D1_0001`、`D1_0007`、`D1_0011` 均有稳定高置信度 OCR 文本。
2026-05-08: 全量 `manual_check_list.csv` 共 `6781` 行，主要原因：`parse_quality_between_0.5_and_0.7=3471`、`ocr_required_or_pending=1541`、图片侧车 TXT 需原图/OCR 内容 `1127`、质量中等且 OCR 相关 `432`。这代表质量控制触发，不等同于 OCR 失败。
2026-05-08: 全量 `parse_success=0` 只剩三类：`image_sidecar_txt:utf-8-sig=1127`（侧车元数据，按规则不作为主题文本）、`scanned_pdf_ocr_pending=54`（扫描 PDF 转图 OCR 尚未实现）、`metadata_only=2`（超过 25MB 文件大小预算）。图片文件本身的 PaddleOCR 已全部成功。
2026-05-08: 全量清洗产物大小：`processed/document_blocks.jsonl=165.43MB`，`processed/document_index.csv=101.42MB`，`processed/file_manifest.csv=1.88MB`，`processed/manual_check_list.csv=1.60MB`，`logs/parse_log.csv=0.53MB`，`logs/ocr_log.csv=0.07MB`。
2026-05-08: 当前 git 工作区有两处代码/文档改动：`docs/PROJECT_MAIN.md`、`src/mcm_b/cleaning.py`；全量清洗输出位于 ignored `outputs/`，不纳入 git 提交。
```

最近验证状态：

```text
unittest: OK, 3 tests
math_test.py: OK
git branch: agent/b-problem-bootstrap
last commit: d5a07dc feat: add PaddleOCR image cleaning
2026-05-08 12:?? created docs/PROJECT_MAIN.md as required project memory.
2026-05-08: 已卸载 CPU 版 paddlepaddle 3.3.1，准备安装 50 系列 Windows GPU wheel。
2026-05-08: 当前环境已安装 GPU 版 paddlepaddle-gpu 3.0.0.dev20250717，并已通过 CUDA tensor smoke test 与 PaddleOCR GPU smoke 清洗。
2026-05-08: unittest discover 通过，3 tests OK。
2026-05-08: 全量清洗 summary 已核验，`outputs\b_problem\cleaning_ocr_full\cleaning_summary.json` 与脚本终端输出一致。
2026-05-08: 用户要求新增一份面向数模论文撰写的数据清洗环节详细说明 Markdown，需覆盖清洗步骤、输出文件结构、引用模型、参数、日志解释、质量控制和全量清洗统计。计划创建 `docs/数据清洗环节论文参考说明.md`。
2026-05-08: 已读取全量清洗产物字段：`file_manifest.csv`、`document_index.csv`、`manual_check_list.csv`、`parse_log.csv`、`ocr_log.csv` 的列名已确认；`business_dictionary.json` 当前包含 notice/meeting/project/money/contract/personnel/deadline/urgent 八类业务词典。
2026-05-08: 已创建 `docs/数据清洗环节论文参考说明.md`，作为论文“数据预处理/清洗”部分的完整参考。文档覆盖 19 个章节：清洗目标、输入范围、总体流程、文件扫描编号、类型分流、各类文件清洗细节、OCR 模型与 GPU 环境、文本标准化、业务属性抽取、块级结构、质量评估、输出文件结构、主索引字段、日志解释、全量统计、后续建模衔接、论文表述、局限改进和图表建议。
2026-05-08: 用户确认数据清洗阶段基本完成，要求整理目录，删除旧版本/临时输出，只保留最新一版文件和数据。清理原则：保留原始 `B题数据集/`、最新全量清洗输出 `outputs/b_problem/cleaning_ocr_full/`、源码、docs、模型配置；删除旧清洗输出、smoke 输出、旧建模输出和临时样本产物。删除前先列目录确认目标。
2026-05-08: 已列出当前目录：`outputs/b_problem` 中存在旧输出 `cleaning_v1`、`cleaning_v2`、`cleaning_ocr_smoke`、`cleaning_gpu_smoke`、`cleaning_smoke`、`pipeline_*`、`run_*` 以及若干 `sample_*`/`dataset3_head.csv` 临时文件；最新全量清洗结果为 `outputs/b_problem/cleaning_ocr_full`，大小约 `271.02MB`。当前 git 改动为 `docs/PROJECT_MAIN.md`、`src/mcm_b/cleaning.py` 和新增论文参考文档。
```
