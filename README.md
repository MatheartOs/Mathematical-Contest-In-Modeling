# Mathematical Contest In Modeling

这个仓库用于数学建模竞赛期间共享代码、数据处理脚本、模型验证脚本和实验结果。当前已经准备了 Python 基础数学测试脚本，并配置了一组常用科学计算第三方库。

## 推荐环境

- Python: 3.10.x
- 操作系统: Windows / macOS / Linux 均可
- 推荐使用虚拟环境，避免污染个人电脑上的全局 Python

## 快速开始

在仓库根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python math_test.py
python verify_science_stack.py
python science_complex_test.py
```

如果 PowerShell 禁止激活脚本，可以临时使用：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

也可以不激活虚拟环境，直接运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe math_test.py
.\.venv\Scripts\python.exe verify_science_stack.py
.\.venv\Scripts\python.exe science_complex_test.py
```

## 远程仓库

GitHub 地址：

```text
git@github.com:MatheartOs/Mathematical-Contest-In-Modeling.git
```

提交或同步前建议运行：

```powershell
.\.venv\Scripts\python.exe math_test.py
.\.venv\Scripts\python.exe verify_science_stack.py
.\.venv\Scripts\python.exe science_complex_test.py
.\.venv\Scripts\python.exe -m pip check
```

## 已包含的第三方科学计算包

| 包名 | 用途 |
| --- | --- |
| numpy | 数组、矩阵、线性代数、随机数、基础数值计算 |
| scipy | 优化、积分、插值、统计、稀疏矩阵、科学计算算法 |
| pandas | 表格数据读取、清洗、合并、统计分析 |
| matplotlib | 基础绘图、论文和报告图表输出 |
| seaborn | 统计可视化，更适合快速画分布图、相关性图 |
| scikit-learn | 机器学习、聚类、回归、分类、模型评估 |
| statsmodels | 统计建模、回归分析、时间序列分析 |
| sympy | 符号计算、公式推导、代数化简 |
| networkx | 图论、网络分析、路径和连通性建模 |
| openpyxl | 读写 Excel `.xlsx` 文件 |
| jupyterlab | Notebook 实验环境，适合探索性建模 |
| notebook | 传统 Jupyter Notebook 支持 |

## 当前测试脚本

`math_test.py` 会执行以下检查：

- 二次方程求根
- 数值积分
- 高斯消元求解线性方程组
- 线性系统残差验证
- 幂迭代估计矩阵主特征值
- 复数多项式计算

运行成功时会看到类似输出：

```text
Python math environment OK
Linear system solution: [1.0, 2.0, -1.0, 1.0]
Linear system residual norm: 0.00e+00
Dominant eigenvalue estimate: 14.07347775
```

`verify_science_stack.py` 用于检查第三方科学计算包是否已经安装成功。运行成功时会列出每个包的版本；如果有缺失，会明确打印缺失包名。

`science_complex_test.py` 是综合科学计算测试，会实际调用 NumPy、SciPy、Pandas、Matplotlib、Seaborn、Scikit-learn、Statsmodels、Sympy 和 NetworkX，覆盖线性代数、优化、积分、统计回归、机器学习、符号计算、图论和绘图输出。运行后会生成 `outputs/science_complex_test.png`。

## B 题项目入口

本次比赛已确定选择 B 题。代码目录已新增 `src/mcm_b/` 和 `scripts/`，用于多源异构文件识别、主题归类和人工复核优先级建模。

默认命令只做轻量小样本，不会全量解析几千个文件：

```powershell
.\.venv\Scripts\python.exe scripts\inspect_b_data.py
.\.venv\Scripts\python.exe scripts\run_b_pipeline_sample.py
```

项目内放置完整 `B题数据集/` 后，可运行正式链路：

```powershell
.\.venv\Scripts\python.exe scripts\run_b_cleaning.py --output-dir outputs\b_problem\cleaning_v2
.\.venv\Scripts\python.exe scripts\run_b_pipeline.py --clusters 10 --max-chars 30000 --max-file-mb 25 --cleaning-dir outputs\b_problem\cleaning_v2 --output-dir outputs\b_problem\run_cleaned_v2
```

清洗链路会生成 `document_index.csv`、`document_blocks.jsonl`、`parse_log.csv`、`manual_check_list.csv` 等标准清洗产物。正式链路会基于 `document_index.csv` 生成 `RESULT_SUMMARY.md`、问题 1/2/3 的 CSV 表和 PNG 图；`B题数据集/` 与 `outputs/` 均不提交到 git。

交接和协作说明见：

- `docs/B_PROBLEM_NOTES.md`
- `docs/ALGORITHM_SKETCH.md`
- `docs/AGENT_HANDOFF.md`
- `docs/GIT_WORKFLOW.md`

## 协作建议

- 代码脚本放在 `src/` 或按题目模块分文件管理。
- 原始数据建议放在 `data/raw/`，清洗后的数据放在 `data/processed/`。
- 图表和中间结果建议放在 `outputs/`。
- 重要实验请记录参数、输入数据版本和运行结论。
- 提交前先运行 `python math_test.py`，确认基础环境没有损坏。

## 常见问题

PowerShell 启动时可能出现 profile 执行策略提示：

```text
无法加载 Microsoft.PowerShell_profile.ps1，因为在此系统上禁止运行脚本
```

这个提示通常不影响 Python 运行。如果需要激活虚拟环境，可以在当前 PowerShell 会话中临时执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
