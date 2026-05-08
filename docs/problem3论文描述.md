# Problem 3 论文描述：人工复核优先级与资源约束优化

> 本文档用于支撑数维杯 B 题论文中“问题三：复核优先级与资源约束优化”部分的撰写。内容对应当前实现 `src/mcm_b/problem3_optimization.py`、运行脚本 `scripts/run_problem3_optimization.py`，以及输出目录 `outputs/b_problem/problem3_optimization/`。本文档中的数学符号与问题二保持衔接：`p_{i1}` 表示样本 `i` 的最高类别概率，`p_{i2}` 表示第二类别概率，`H_i` 表示归一化熵，`MII_i` 表示解释性指数，`TAI_i` 表示迁移适用性。

## 1. 问题三目标

问题三要求结合问题二结果，对数据集 2 和数据集 3 的新流入文件进行风险分层和复核调度。具体目标包括：

1. 从紧急程度、错分风险、复核必要性三个维度划分高、中、低等级。
2. 重点关注主题不明确文件、高时效文件和资金分配相关文件。
3. 综合考虑归档准确性、时效性和经济成本，判断是否需要人工复核。
4. 在数据集 4 的三种资源约束场景 S1、S2、S3 下，给出复核优先顺序和处理建议。

本项目采用“熵权-AHP 融合 + 特殊关注增强 + 资源约束优先队列”的方法，简称：

```text
RTF-RPO: Risk-Timeliness-Fund Review Priority Optimizer
```

## 2. 输入与输出

问题三输入包括：

```text
outputs/b_problem/problem2_transfer/problem2_transfer_classification.csv
outputs/b_problem/cleaning_ocr_full/processed/document_index.csv
B题数据集/数据集4：业务规则与资源约束表.xlsx
```

问题三输出目录为：

```text
outputs/b_problem/problem3_optimization/
```

最终论文交付表还汇总到：

```text
outputs/b_problem/final_results/
```

## 3. 符号定义

设共有 `n` 个待处理文件，文件编号为 `i = 1,2,...,n`。问题二已经给出每个文件的类别概率和状态标签。

| 符号 | 含义 |
| --- | --- |
| `p_{i1}` | 文件 `i` 的最高类别概率 |
| `p_{i2}` | 文件 `i` 的第二类别概率 |
| `m_i` | 主次类相对边际差，`m_i = (p_{i1}-p_{i2})/p_{i1}` |
| `H_i` | 类别概率归一化熵 |
| `MII_i` | 模型解释指数 |
| `TAI_i` | 迁移适用性指数 |
| `Q_i` | 清洗解析质量 |
| `U_i` | 紧急程度得分 |
| `R_i` | 错分风险得分 |
| `N_i` | 复核必要性得分 |
| `P_i` | 综合优先级得分 |
| `\Theta_i` | 时效信号 |
| `\Phi_i` | 资金信号 |
| `G_i` | 项目属性信号 |
| `t_i` | 预计人工复核时间 |
| `\delta_i` | 是否进入人工复核队列，1 表示复核，0 表示不复核 |

全文中 `U_i` 始终表示紧急程度，`R_i` 始终表示错分风险，`N_i` 始终表示复核必要性，`P_i` 始终表示综合优先级，避免同一含义使用多个符号。

## 4. 紧急程度建模

紧急程度用于衡量文件是否需要快速处理。模型从四类信息构造时效信号：

1. 文本中是否出现“截止、请于、前完成、公示、通知、紧急、限期、反馈、整改、考试、会议”等词。
2. 清洗阶段是否识别到截止时间字段 `has_deadline`。
3. 是否识别到紧急标记 `has_urgent`。
4. 文件日期是否接近当前竞赛年度。

记时效信号为 `\Theta_i`，资金信号为 `\Phi_i`，项目属性为 `G_i`，则：

```text
U_i = 0.62 \Theta_i + 0.18 \Phi_i + 0.20 G_i
```

其中所有分数均归一化到 `[0,1]`。

## 5. 错分风险建模

错分风险来自问题二的分类不确定性。若最高类别概率低、类别熵高、主次类差距小、迁移适用性低或解析质量差，则错分风险更高。

```text
R_i = 0.30(1 - p_{i1})
    + 0.26H_i
    + 0.22(1 - m_i)
    + 0.12(1 - TAI_i)
    + 0.10(1 - Q_i)
```

其中：

```text
m_i = (p_{i1} - p_{i2}) / max(p_{i1}, \varepsilon)
```

`\varepsilon` 是极小正数，用于避免除零。

## 6. 复核必要性建模

复核必要性不仅取决于分类不确定性，还与问题二状态、解释性和业务风险有关。首先根据问题二状态给出基础复核强度 `S_i`：

| 问题二状态 | `S_i` |
| --- | ---: |
| `A_clear_auto_archive` | 0.08 |
| `A_assisted_archive` | 0.30 |
| `B_overlap_manual_review` | 0.82 |
| `C_unknown_expert_review` | 0.92 |

复核必要性定义为：

```text
N_i = 0.36S_i
    + 0.24R_i
    + 0.16(1 - MII_i)
    + 0.14\Phi_i
    + 0.10\Theta_i
```

其中 `1 - MII_i` 表示解释不足程度。若模型无法给出集中、清晰的主题词解释，则复核必要性提高。

## 7. 熵权-AHP 融合权重

三个维度分别为：

```text
V_{i1}=U_i, V_{i2}=R_i, V_{i3}=N_i
```

主观权重来自题意和业务判断：

```text
w^s = (0.34, 0.38, 0.28)
```

其中错分风险略高，体现归档准确性优先；紧急程度其次，体现办公时效性；复核必要性用于承接人机协同策略。

客观熵权计算如下。先做比例归一化：

```text
z_{ij} = V_{ij} / sum_{i=1}^{n} V_{ij}
```

信息熵为：

```text
e_j = - (1 / ln n) * sum_{i=1}^{n} z_{ij} ln z_{ij}
```

客观权重为：

```text
w^o_j = (1 - e_j) / sum_{r=1}^{3}(1 - e_r)
```

为避免纯熵权被单一离散维度支配，最终采用主客观加权融合：

```text
w_j = (1 - \lambda) w^s_j + \lambda w^o_j
```

其中：

```text
\lambda = 0.35
```

当前运行得到：

| 维度 | 主观权重 | 熵权 | 综合权重 |
| --- | ---: | ---: | ---: |
| 紧急程度 `U_i` | 0.34 | 0.871833 | 0.526142 |
| 错分风险 `R_i` | 0.38 | 0.025656 | 0.255980 |
| 复核必要性 `N_i` | 0.28 | 0.102511 | 0.217879 |

## 8. 特殊关注增强

题目明确要求重点关注三类文件：

1. 主题不明确文件。
2. 高时效文件。
3. 资金分配相关文件。

定义特殊关注指示变量：

```text
I_i =
1, 若文件 i 属于主题不明确、高时效或资金相关
0, 否则
```

基础综合得分为：

```text
P_i^0 = w_1 U_i + w_2 R_i + w_3 N_i
```

特殊关注增强后的综合优先级为：

```text
P_i = P_i^0(1 + \mu I_i)
```

当前参数：

```text
\mu = 0.18
```

## 9. 高中低等级划分

对每个维度分别采用分位数划分。设 `Q_{30}` 和 `Q_{70}` 分别为该维度分数的 30% 和 70% 分位数，则：

```text
Level(x_i) =
高, x_i >= Q_{70}
中, Q_{30} <= x_i < Q_{70}
低, x_i < Q_{30}
```

该规则得到的是相对等级，适合资源调度和优先队列排序。由于错分风险、复核必要性和综合优先级使用同一分位数策略，总量通常接近 30% / 40% / 30%；这不表示三种分数完全相同，而是分位数分级规则导致的数量结构。

当前等级分布：

| 维度 | 高 | 中 | 低 |
| --- | ---: | ---: | ---: |
| 紧急程度 | 1622 | 2738 | 159 |
| 错分风险 | 1356 | 1807 | 1356 |
| 复核必要性 | 1356 | 1807 | 1356 |
| 综合优先级 | 1356 | 1807 | 1356 |

## 10. 是否复核与建议动作

根据问题二状态和综合优先级，将文件划分为五类动作：

| 动作编码 | 中文含义 | 处理逻辑 |
| --- | --- | --- |
| `expert_review` | 专家研判 | 问题二为未知样本，优先复核 |
| `manual_review` | 人工复核 | 问题二为多类别重叠样本 |
| `priority_sampling` | 重点抽检 | 高优先级、资金相关或高时效样本 |
| `auto_archive` | 自动归档 | 清晰自动归档样本 |
| `assisted_archive` | 辅助归档 | 可归档但保留解释或后续抽检 |

论文中的“是否复核”可根据 `needs_review_zh` 字段读取：

```text
是：expert_review, manual_review, priority_sampling
否：auto_archive, assisted_archive
```

## 11. 复核时间与资源约束

复核时间 `t_i` 与文本长度、状态、资金信号和时效信号有关：

```text
t_i = 10 + min(16, 1.8 ln(1 + text_length_i))
```

若为未知专家研判，增加 7 分钟；若为重叠复核，增加 4 分钟；资金相关增加 3 分钟；高时效增加 2 分钟。最终限制在：

```text
8 <= t_i <= 35
```

数据集 4 给出三种资源场景：

| 场景 | 人工工时上限 | 人工复核数量上限 | 自动归档能力上限 |
| --- | ---: | ---: | ---: |
| S1 | 60 小时/天 | 200 份/天 | 1200 份/天 |
| S2 | 80 小时/天 | 300 份/天 | 1500 份/天 |
| S3 | 100 小时/天 | 400 份/天 | 1800 份/天 |

## 12. 资源分配优化模型

设场景为 `s`，人工复核时间上限为 `L_s`，人工复核数量上限为 `K_s`。决策变量为：

```text
\delta_i =
1, 文件 i 被选入场景 s 的复核队列
0, 文件 i 暂不复核
```

复核队列满足：

```text
sum_i t_i \delta_i <= L_s
sum_i \delta_i <= K_s
```

为了符合题目重点，复核优先级采用三层排序：

1. `expert_review`：主题不明确样本，优先进入队列。
2. `manual_review`：多类别重叠样本。
3. `priority_sampling`：高时效、资金相关或高综合优先级抽检样本。

同一层内按照：

```text
overall_level -> P_i -> P_i/t_i
```

排序，其中 `P_i/t_i` 表示单位复核时间带来的治理价值。

自动归档队列按照归档可靠性排序：

```text
A_i^{arch} = 0.45 p_{i1} + 0.35 ARS_i + 0.20 MII_i
```

## 13. 运行结果

当前处理文件数：

```text
record_count = 4519
```

三种资源场景结果：

| 场景 | 复核文件数 | 总成本指数 | 最大完工时间/小时 | 未复核风险 | 高等级覆盖率 | 自动归档数 | 未知复核 | 重叠复核 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 137 | 59.978900 | 59.979 | 1490.465329 | 0.101032 | 1200 | 102 | 34 |
| S2 | 173 | 79.929683 | 79.930 | 1363.929117 | 0.127581 | 1500 | 102 | 71 |
| S3 | 210 | 99.829683 | 99.830 | 1236.019877 | 0.154867 | 1800 | 102 | 108 |

结论：

1. 三种场景均优先覆盖 102 个未知专家研判样本，符合题目对主题不明确文件的重点关注要求。
2. S1 资源最紧，除未知样本外只能覆盖 34 个重叠样本。
3. S2 增加人工工时后，重叠复核覆盖数提升到 71。
4. S3 资源最充足，可覆盖 108 个重叠样本，未复核风险最低。
5. 三个场景人工资源利用率均接近 100%，说明资源约束被充分利用。

## 14. 输出文件解释

### 14.1 problem3_risk_priority.csv

该表为文件级复核优先级表，包含每个文件的三维得分、等级、综合得分、是否复核和建议动作。论文中可选取以下字段展示：

| 字段 | 含义 |
| --- | --- |
| `file_id` | 文件编号 |
| `dataset_id` | 数据集编号 |
| `top1_topic_name` | 问题二预测主题 |
| `urgency_score` | 紧急程度得分 |
| `urgency_level` | 紧急程度等级 |
| `misclassification_risk_score` | 错分风险得分 |
| `risk_level` | 错分风险等级 |
| `review_necessity_score` | 复核必要性得分 |
| `review_necessity_level` | 复核必要性等级 |
| `priority_score` | 综合优先级得分 |
| `overall_level` | 综合等级 |
| `needs_review_zh` | 是否复核 |
| `recommended_action_zh` | 建议动作 |
| `special_focus_reason` | 重点关注原因 |

### 14.2 problem3_scenario_comparison.csv

该表为资源约束场景对比表，直接对应解析文末建议的第五类结果表。

| 字段 | 含义 |
| --- | --- |
| `review_selected_count` | 复核文件数量 |
| `total_cost_index` | 总成本指数，当前等于复核工时成本 |
| `max_completion_hours` | 最大完工时间，单位小时 |
| `unreviewed_risk_value` | 未复核风险值 |
| `high_level_coverage_rate` | 高等级文件覆盖率 |
| `unknown_reviewed` | 未知样本复核数 |
| `overlap_reviewed` | 重叠样本复核数 |

### 14.3 队列表

```text
problem3_review_queue_S1.csv
problem3_review_queue_S2.csv
problem3_review_queue_S3.csv
```

这三张表给出不同资源场景下的复核顺序。字段 `review_rank` 越小，越应优先处理。

### 14.4 自动归档表

```text
problem3_auto_archive_S1.csv
problem3_auto_archive_S2.csv
problem3_auto_archive_S3.csv
```

这三张表给出各场景下优先自动归档的文件。字段 `archive_rank` 越小，系统自动归档可靠性越高。

## 15. 图表解释

### 15.1 problem3_level_distribution.png

该图展示紧急程度、错分风险、复核必要性和综合优先级四个维度的高、中、低数量分布。

对应数据：

```text
problem3_level_distribution_plot_data.csv
problem3_level_distribution.png.csv
```

图中错分风险、复核必要性和综合优先级数量接近 30% / 40% / 30%，原因是采用分位数相对分级；紧急程度由于大量低时效样本分值并列，分布略有偏移。

### 15.2 problem3_scenario_comparison.png

该图对比 S1、S2、S3 下人工复核、自动归档和延后处理数量。随着资源增加，自动归档能力和复核能力同步提高，延后处理数量下降。

对应数据：

```text
problem3_scenario_comparison_plot_data.csv
problem3_scenario_comparison.png.csv
```

### 15.3 problem3_action_distribution.png

该图展示数据集 2、3 在五类建议动作上的分布，用于说明自动归档、辅助归档、重点抽检、人工复核和专家研判之间的比例。

对应数据：

```text
problem3_action_distribution_plot_data.csv
problem3_action_distribution.png.csv
```

### 15.4 problem3_review_queue_topic_distribution.png

该图展示 S1、S2、S3 复核队列中不同主题的分布，用于说明复核资源主要流向哪些业务类别。

对应数据：

```text
problem3_review_queue_topic_distribution_plot_data.csv
problem3_review_queue_topic_distribution.png.csv
```

## 16. 最终交付表位置

为方便论文手直接引用，最终五类结果表已汇总到：

```text
outputs/b_problem/final_results/
```

其中：

| 文件 | 对应解析要求 |
| --- | --- |
| `data_preprocessing_statistics.csv` | 数据预处理统计表 |
| `problem1_classification_result_table.csv` | 问题一分类结果表 |
| `problem2_assignment_evaluation_table.csv` | 问题二归属评价表 |
| `problem3_review_priority_table.csv` | 问题三复核优先级表 |
| `resource_scenario_comparison_table.csv` | 资源约束场景对比表 |

## 17. 可直接写入论文的总结

```text
针对问题三，本文构建了面向智能办公治理的 RTF-RPO 复核优先级优化模型。模型首先承接问题二输出的类别概率、归属合理性 ARS、解释性指数 MII、迁移适用性 TAI 和状态标签，从紧急程度、错分风险、复核必要性三个维度对文件进行评分。随后采用 AHP 主观权重与熵权客观权重融合，得到综合优先级分数，并对主题不明确、高时效和资金相关文件设置特殊关注增强项。

在资源调度阶段，模型根据数据集 4 给出的 S1、S2、S3 三种资源约束，构建复核优先队列。主题不明确样本优先进入专家研判队列，多类别重叠样本进入人工复核队列，高时效和资金相关样本进入重点抽检队列。每个场景同时满足人工工时上限、人工复核数量上限和自动归档能力上限。实验结果表明，S1、S2、S3 分别复核 137、173、210 个文件，均优先覆盖全部 102 个未知专家研判样本；随着资源增加，重叠样本覆盖数从 34 增至 108，未复核风险逐步降低。该结果说明所建模型能够在归档准确性、时效性和经济成本之间形成可解释的人机协同治理方案。
```
