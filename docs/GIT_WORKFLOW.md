# Git Workflow

## Collaboration Rules

三人协作时建议所有人都避免直接推送 `main`：

```powershell
git switch main
git pull --ff-only origin main
git switch -c <name>/<task>
```

分支命名建议：

```text
agent/b-problem-bootstrap
member-a/data-cache
member-b/paper-figures
member-c/topic-labeling
```

## Commit Rhythm

按可回溯的小阶段提交：

1. `docs:` 文档、交接说明、实验记录。
2. `feat:` 新增算法、脚本、数据处理模块。
3. `fix:` 修复读取失败、模型 bug。
4. `exp:` 可复现实验配置或结果摘要。

提交前至少运行：

```powershell
.\.venv\Scripts\python.exe math_test.py
.\.venv\Scripts\python.exe verify_science_stack.py
.\.venv\Scripts\python.exe scripts\inspect_b_data.py --sample-per-dataset 2 --dataset3-rows 3
```

## Data And Outputs

原始数据在仓库平级中文目录 `数模赛数据`，不复制进 git。

`outputs/` 默认被忽略，只保留 `.gitkeep`。需要共享实验结果时，优先提交：

1. 生成结果的脚本；
2. 参数说明；
3. 关键统计摘要；
4. 必要的小型图表或论文用表。

不要提交大体积原始文件、模型缓存或全量中间表。

## Recovery

如果算法崩溃，先保留现场：

```powershell
git status --short
git diff > outputs\b_problem\debug_worktree.diff
```

然后从最近可用提交另开分支继续：

```powershell
git switch main
git pull --ff-only origin main
git switch -c <name>/recovery-<date>
```
