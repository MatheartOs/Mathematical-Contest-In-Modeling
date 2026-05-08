# B 题项目主文档

> 本文档是当前项目的事实源和交接入口。后续每次执行重要命令、得到新结果、修改参数或调整算法，都必须同步更新本文档，再继续推进任务。

## 当前问题定义

竞赛题目为 2026 年第十一届数维杯大学生数学建模挑战赛（春季赛）B 题：智能办公场景下多源异构文件识别与治理优化。

需要解决三类问题：

1. 问题一：对数据集 1 的历史真实文件进行多源异构特征挖掘、分类，并归纳主题体系。
2. 问题二：将数据集 2 和数据集 3 的后续流入数据归入问题一建立的分类体系，并评价归属判断的合理性、可解释性和迁移适用性。
3. 问题三：结合归类结果，从紧急程度、错分风险、复核必要性三方面分级，在数据集 4 的资源约束下决定是否人工复核及复核优先顺序。

当前阶段重点：基于 `outputs/b_problem/cleaning_ocr_full/` 的全量 OCR 文件画像，完成问题一历史主题体系；同时将清洗阶段的人工复核标记从“保守质量提示”调整为“数据集 4 资源约束下的复核分配结果”。

## 2026-05-08 本轮接手记录

### 当前问题定义

本轮任务聚焦两个点：

1. 阅读题面与建模手参考，继续完成问题一：对数据集 1 历史真实文件提取内容、结构、业务和质量特征，建立可解释主题分类体系。
2. 优化清洗日志中 `need_manual_check=6781/7916` 的过度保守问题：依据数据集 4 的资源约束表，重新调整清洗质量评分权重与人工复核分配规则，使自动归档、元数据归档、人工复核数量匹配 S1/S2/S3 场景。

### 已完成内容

- 已读取 `docs/` 下项目交接、算法草图、B 题说明、清洗流程与清洗论文参考文档。
- 已读取题面 PDF。题目三明确要求重点考虑主题不明确、时效要求高、涉及资金分配的文件，而不是把所有 OCR 或中等质量样本都人工复核。
- 已读取数据集 4：`S1/S2/S3` 三种资源场景如下：

| 场景 | 每日人工工时 | 自动归档上限 | 人工复核上限 | 按 18 分钟/份折算后复核容量 |
| --- | ---: | ---: | ---: | ---: |
| S1 | 60 | 1200 | 200 | 200 |
| S2 | 80 | 1500 | 300 | 266 |
| S3 | 100 | 1800 | 400 | 333 |

- 已修改 `src/mcm_b/cleaning.py`：
  - 新增 `QUALITY_WEIGHTS`，质量评分由文本、OCR、版面、业务信号、格式稳定性五因子构成。
  - 取消“所有 OCR 文件直接人工复核”的规则，改为仅对 OCR 置信度低、扫描 PDF 待 OCR、超大元数据、文本异常短等硬风险标记。
  - 对数据集 3 采用更短的文本下限，避免匿名片段因为天然短文本被误判为清洗失败。
  - 新增 `hard_manual_check`、`manual_review_priority`、`archive_decision`、`resource_scenario` 字段。
  - 新增资源约束分配：硬风险优先，其余按 `manual_review_priority` 补满各场景复核容量。
- 已新增 `scripts/recalibrate_cleaning_review.py`，可不重跑 OCR，直接基于现有 `document_index.csv` 重算质量分和复核清单。
- 已修改 `scripts/run_b_pipeline.py`：
  - 问题一建模文本只保留中文语义和业务关键词，过滤数字、小数点、英文编码和 Excel 模板词，减少统计表噪声对字符 TF-IDF 的污染。
  - 问题一主题摘要新增代表文件编号与代表标题。
  - 主题命名加入基于 top terms 的规则，如地区指标统计、宏观经济统计、文旅活动评价、企业投资统计、服务业经营统计、制造业统计、城市月度指标等。
- 已修改 `src/mcm_b/modeling.py`：正式 TF-IDF 增加 `min_df=2`、`max_df=0.85`，削弱偶然噪声和过泛词。

### 数据清洗方案

新方案将“清洗质量风险”和“资源约束复核决策”拆成两层：

1. 质量评分：

```text
Q_i = 0.20 q_text + 0.25 q_ocr + 0.20 q_layout + 0.20 q_business + 0.15 q_format
```

## 2026-05-08 附录与符号说明整理

当前新增论文收尾材料：

```text
docs/附录与支撑材料.md
docs/数学符号定义与说明.md
```

已完成内容：

```text
1. 按论文附录要求整理支撑材料列表：包含实际使用软件、运行命令、源程序文件名及作用。
2. 按论文附录要求整理结果文件列表：覆盖清洗、问题一、问题二、问题三和最终交付结果。
3. 附录 3 仅列求解代码粘贴顺序，不在 Markdown 中展开源码，便于后续由论文手自行复制。
4. 新建符号说明文件，按“数学符号 LaTeX + 符号说明”的格式逐行列出全文主要符号。
5. 为避免符号冲突，问题三是否进入复核队列的决策变量统一改为 \delta_i；问题二预测类别仍为 y_i。
6. 为避免 L 的歧义，MII 解释词数量统一为 L_e，资源场景时间上限保留 L_s。
```

当前符号统一结论：

```text
y_i: 预测主题类别
\delta_i: 是否进入人工复核队列
P_i: 综合优先级
\mathbf{p}_i: 类别概率向量
C: 业务锚点特征矩阵
L_s: 场景 s 的人工复核时间上限
K_s: 场景 s 的人工复核数量上限
L_e: MII 解释词数量
```

其中 `q_business` 不再强制要求每个文件都有日期和金额；只有当文件命中截止/资金相关语义时，才把日期/金额缺失作为完整性风险。这样避免把普通通知、统计图、短片段误判为低质量。

2. 复核优先级：

```text
P_i = 0.45(1-Q_i) + 0.15 OCR风险 + 0.15 短文本风险 + 0.15 业务风险 + 0.10 格式风险
```

其中业务风险重点包含 `has_money`、`has_deadline`、`has_urgent`、`has_contract`。最终先纳入硬风险文件，再按 `P_i` 从高到低补足 S1/S2/S3 容量。

### 文件结构

本轮新增或更新：

```text
scripts/
├── recalibrate_cleaning_review.py  # 不重跑 OCR 的清洗质量/复核清单重校准脚本
└── run_b_pipeline.py               # 已优化问题一建模文本与主题摘要

src/mcm_b/
├── cleaning.py                     # 已加入资源感知复核分配
└── modeling.py                     # 已调整 TF-IDF 过滤参数

outputs/b_problem/cleaning_ocr_full/processed/
├── manual_check_list.csv           # S1 基准主复核清单，200 份
├── manual_check_list_S1.csv        # 200 份
├── manual_check_list_S2.csv        # 266 份
└── manual_check_list_S3.csv        # 333 份

outputs/b_problem/run_ocr_full/
├── problem1_topic_summary.csv
├── problem1_topic_summary.md
├── problem1_history_topic_assignments.csv
├── problem1_history_features.csv
├── topic_model.joblib
└── RESULT_SUMMARY.md
```

### 关键算法思路

- 问题一历史主题发现仍采用可解释基线：清洗文本 -> 中文语义过滤 -> 字符级 TF-IDF -> KMeans。
- 中文语义过滤的目的不是删除业务信息，而是移除 OCR 表格中大量数字、百分号、小数点、Excel 固定模板词，防止聚类按数值格式而非主题聚合。
- 主题命名采用“模型 top terms + 业务关键词组 + 代表文件”三者结合，避免只依赖关键词组造成误命名。
- 清洗复核优化采用“硬风险必优先 + 资源容量补足”的策略。硬风险包括扫描 PDF 待 OCR、元数据-only、短文本异常、OCR 置信度低等；资源剩余容量用于抽检高优先级边界样本。

### 已验证结论

- 全量清洗目录已完成资源感知重校准：

```text
document_count = 7916
need_manual_check = 200
hard_manual_check = 90
auto_archive_count = 6589
metadata_archive_count = 1127
```

- S1/S2/S3 复核清单大小：

```text
S1 = 200
S2 = 266
S3 = 333
```

- 原 `6781` 的人工复核数主要来自旧规则：`parse_quality_between_0.5_and_0.7`、所有 OCR 文件、图片侧车 TXT。新规则确认这些不应全部进入人工复核，图片侧车 TXT 归入 `metadata_archive`。
- 正式主链路已基于优化后的全量 OCR 清洗产物跑通：

```text
outputs/b_problem/run_ocr_full/run_summary.json
problem1_topics = 10
problem2_classified_records = 4012
problem2_ambiguous_records = 337
problem3_manual_review_records = 1229
scenario_queue_sizes = S1:200, S2:266, S3:333
```

- 问题一当前 10 类主题输出位于 `outputs/b_problem/run_ocr_full/problem1_topic_summary.md`。当前主题包括地区指标统计、资金项目材料、项目案件信息、宏观经济统计、文旅活动评价、企业投资统计、服务业经营统计、制造业统计、城市月度指标等。

### TODO

- [x] 读取题面与建模手参考，确认三问关系和问题一/三重点。
- [x] 基于数据集 4 调整清洗质量评分与人工复核分配。
- [x] 不重跑 OCR，回写 `cleaning_ocr_full` 的优化后复核清单与 summary。
- [x] 基于 `cleaning_ocr_full` 跑正式主链路，输出 `run_ocr_full`。
- [x] 优化问题一建模文本，降低数字/模板噪声。
- [ ] 对问题一主题结果做人工抽样核验，必要时把相近统计类主题合并为更高层主题体系。
- [ ] 若论文需要更强模型，可在现有 TF-IDF/KMeans 基线外补充 BERT/GCN/AHP-熵权法作为增强方案说明。
- [ ] 扫描 PDF 转图片 OCR 仍未实现，当前 54 份进入硬风险复核/后续修复队列。

### 参数定义

清洗质量权重：

| 参数 | 当前值 |
| --- | ---: |
| `q_text` | 0.20 |
| `q_ocr` | 0.25 |
| `q_layout` | 0.20 |
| `q_business` | 0.20 |
| `q_format` | 0.15 |

人工复核优先级权重：

| 参数 | 当前值 |
| --- | ---: |
| `quality_risk` | 0.45 |
| `ocr_risk` | 0.15 |
| `short_text_risk` | 0.15 |
| `business_risk` | 0.15 |
| `format_risk` | 0.10 |

资源折算：

```text
minutes_per_review = 18
scenario_capacity = min(人工复核能力上限, 每日人工工时 * 60 / 18)
```

问题一建模参数：

```text
clusters = 10
TfidfVectorizer(analyzer="char", ngram_range=(2,4), min_df=2, max_df=0.85, max_features=10000)
```

### 中间结论

- 旧版 `need_manual_check=6781` 更像“质量提示池”，不适合作为真实人工复核数量。按数据集 4 的每日资源约束，应输出场景化复核队列。
- 图片 OCR 平均置信度很高，不能仅因 `ocr_used=1` 全量人工复核；只有低置信度、文本异常短或业务高风险 OCR 才优先进入人工池。
- 图片侧车 TXT 是元数据追踪文件，当前归入 `metadata_archive`，不作为主题文本，也不占用人工复核资源。
- 问题一主题结果仍受历史数据中大量统计图片影响，当前主题偏向统计指标类、企业投资类、产业类和少量办公材料类；论文中应把这解释为数据集 1 的真实分布特征，并可在后续人工命名阶段合并相近统计主题。

## 2026-05-08 题目一创新实现记录

用户补充说明：`docs/解析.md` 是赛题解析文件，`docs/题目.md` 是原题目文件。后续以这两个 Markdown 为准，不再使用 PDF 轻量抽取文本。

### manual_check_list_S1/S2/S3 含义

`manual_check_list_S1.csv`、`manual_check_list_S2.csv`、`manual_check_list_S3.csv` 分别对应数据集 4 的三种资源约束场景下的人工复核队列：

| 清单 | 对应场景 | 资源解释 | 当前队列规模 |
| --- | --- | --- | ---: |
| `manual_check_list.csv` | 默认基准，等同 S1 | 最保守资源配置下最终需要人工复核的文件 | 200 |
| `manual_check_list_S1.csv` | S1 | 60 小时人工工时、人工复核上限 200 份/天 | 200 |
| `manual_check_list_S2.csv` | S2 | 80 小时人工工时、人工复核上限 300 份/天，按 18 分钟/份折算为 266 | 266 |
| `manual_check_list_S3.csv` | S3 | 100 小时人工工时、人工复核上限 400 份/天，按 18 分钟/份折算为 333 | 333 |

三份清单不是不同数据集，而是同一批清洗结果在不同资源强度下的复核队列。所有场景先保留 `hard_manual_check=1` 的硬风险文件，再按 `manual_review_priority` 从高到低补足容量。

### 创新模型实现

根据 `docs/解析.md` 中“文本-单词异构图、PMI、GCN 聚合、c-TF-IDF 主题归纳”的建议，已新增一个可复现的轻量创新实现：

```text
src/mcm_b/problem1_innovative.py
scripts/run_problem1_innovative.py
```

当前环境没有 torch / sentence-transformers，且临时安装 PyMuPDF 失败；因此实现采用“不依赖深度学习框架”的图传播近似方案：

1. 对数据集 1 历史文件构造中文语义文本，过滤数字、英文编码和模板噪声。
2. 用字符 2-4 gram TF-IDF 构建文档-词边。
3. 用滑动窗口统计词-词共现，并计算正 PMI，构建词-词图。
4. 进行两跳图传播：

```text
X_graph = X_tfidf + 0.60 * X_tfidf * W_ppmi + 0.30 * X_tfidf * W_ppmi^2
```

5. 拼接结构特征和业务特征：页数、段落数、表格数、图片数、标题数、OCR 置信度、清洗质量、资金/项目/合同/会议/截止/紧急等业务标记。
6. 使用 SVD 降维 + KMeans 聚类形成问题一类别。
7. 对每类合并为“类文档”，用 c-TF-IDF 提取主题词，并根据主题词、业务画像、代表文件自动命名。

### 创新模型输出

运行命令：

```powershell
.\.venv\Scripts\python.exe scripts\run_problem1_innovative.py --cleaning-dir outputs\b_problem\cleaning_ocr_full --output-dir outputs\b_problem\problem1_innovative --clusters 10 --max-terms 2500
```

输出目录：

```text
outputs/b_problem/problem1_innovative/
├── problem1_graph_metrics.json
├── problem1_graph_topic_assignments.csv
├── problem1_graph_topic_summary.csv
└── problem1_graph_topic_summary.md
```

已验证输出：

```text
document_count = 2225
term_count = 2500
clusters = 10
word_graph_edges = 366841
word_graph_windows = 404135
silhouette = 0.013804
calinski_harabasz = 26.407962
davies_bouldin = 3.981225
```

当前题目一 10 类主题摘要：

| 主题 | 数量 | 当前名称 |
| ---: | ---: | --- |
| 9 | 959 | 项目案件信息类 |
| 2 | 240 | 资金财政统计类 |
| 3 | 237 | 生态环境治理类 |
| 0 | 201 | 文旅活动评价类 |
| 8 | 166 | 养老服务机构类 |
| 6 | 131 | 教育教学管理类 |
| 1 | 118 | 社会民生指标类 |
| 7 | 114 | 制造业产业统计类 |
| 4 | 47 | 居民收入统计类 |
| 5 | 12 | 城市月度指标类 |

### 新的 TODO

- [x] 改用 `docs/解析.md` 和 `docs/题目.md` 作为赛题/解析事实源。
- [x] 新增异构图 PMI 传播 + 结构业务融合 + c-TF-IDF 的题目一创新模型。
- [x] 跑通创新模型并输出题目一类别表、分配表和指标表。
- [x] 新增 `docs/problem1论文描述.md`，汇总题目一算法步骤、数学推导、模型参数、输出解释和论文可誊写表述。
- [ ] 对 `topic_id=9` 的大类做二级主题拆分，当前 959 份偏大，可能混合了项目、地区、企业统计等子主题。
- [ ] 为论文补一张“异构图建模流程图”和一张“问题一主题体系表”。

## 2026-05-08 题目二创新实现记录

用户要求开始解决问题二：继续依据 `docs/题目.md` 与 `docs/解析.md`，在题目一最新主题体系上加入创新点、完成代码实现并生成美观输出；论文描述需等用户审核通过后再写。

### 当前问题定义

问题二目标是将数据集 2、数据集 3 的后续流入数据迁移到题目一建立的 10 类历史主题体系中，同时评价：

1. 分类效果：新文件的类别概率、主类别、次类别与归档状态。
2. 合理性：主类概率与主次类边际差是否支持当前归属。
3. 可解释性：归属类别的 c-TF-IDF 主题词是否能在新文件中找到贡献证据。
4. 迁移适用性：数据集 2/3 与历史源域在嵌入空间中的分布差异。
5. 边界处理：识别多类别重叠样本与无法明确归类样本。

### 已完成内容

已新增代码：

```text
src/mcm_b/problem2_transfer.py
scripts/run_problem2_transfer.py
```

运行命令：

```powershell
.\.venv\Scripts\python.exe scripts\run_problem2_transfer.py --cleaning-dir outputs\b_problem\cleaning_ocr_full --output-dir outputs\b_problem\problem2_transfer --clusters 10 --max-terms 2500
```

输出目录：

```text
outputs/b_problem/problem2_transfer/
├── problem2_transfer_classification.csv   # 每条新文件的分类、概率、ARS、MII、TAI、状态和解释词
├── problem2_dataset_evaluation.csv        # 数据集级评价表
├── problem2_topic_distribution.csv        # 数据集-主题-状态分布
├── problem2_boundary_samples.csv          # 多类别重叠/未知样本示例与复核清单
├── problem2_source_topic_summary.csv      # 源域题目一主题体系
├── problem2_transfer_report.md            # 可直接审核的 Markdown 汇总报告
├── problem2_transfer_metrics.json         # 参数与运行指标
├── problem2_topic_distribution.png        # 主题归属分布图
├── problem2_topic_distribution_plot_data.csv
├── problem2_topic_distribution.png.csv
├── problem2_state_distribution.png        # 自动归档/复核状态分布图
├── problem2_state_distribution_plot_data.csv
├── problem2_state_distribution.png.csv
├── problem2_ars_mii_scatter.png           # 合理性-可解释性散点图
├── problem2_ars_mii_scatter_plot_data.csv
└── problem2_ars_mii_scatter.png.csv
```

其中 `*_plot_data.csv` 是面向论文手的易读作图数据表；`*.png.csv` 是与 PNG 严格同名的作图数据 sidecar。两类表内容一致，均包含中文标签、英文标签和原始数值，方便中文论文重画图。

### 数据清洗与样本筛选

源域仍使用题目一规则：数据集 1 中非图片侧车文件，`parse_quality >= 0.45` 且清洗文本长度不低于 40 的历史文件，共 2225 份。

目标域使用数据集 2、数据集 3 全量记录，共 4519 份。其中：

```text
target_modelable_count = 4419
target_unclassifiable_count = 100
```

不可直接分类样本包括图片侧车元数据、仅元数据、扫描 PDF 待 OCR、有效中文语义过短或解析质量低于迁移阈值的记录，统一进入 `C_unknown_expert_review`。

### 关键算法思路

题目二沿用题目一的异构图主题空间，但增加迁移分类评价层：

1. 源域建模：用数据集 1 训练字符 2-4 gram TF-IDF，构造文档-词边。
2. 词图传播：用源域滑动窗口计算正 PMI 词-词图，得到两跳传播表示：

```text
X_graph = X_tfidf + 0.60 * X_tfidf * W_ppmi + 0.30 * X_tfidf * W_ppmi^2
```

3. 特征融合：拼接结构特征、清洗质量、OCR 置信度、文本长度、文件大小和八类业务标签。
4. 共享空间：在源域上拟合 Normalizer、SVD、StandardScaler、KMeans，并对目标域复用同一套变换。
5. 概率化归属：根据目标样本到 10 个主题中心的距离，使用温度 softmax 转为类别概率分布。
6. 归属合理性 ARS：

```text
ARS = alpha * p1 + (1 - alpha) * (p1 - p2) / p1
alpha = 0.60
```

7. 可解释性 MII：用预测主题的 c-TF-IDF 主题词在目标文本中的命中贡献构造伪注意力分布，再用归一化熵计算解释集中度。
8. 迁移适用性 TAI：源域与目标域嵌入分布计算 RBF-MMD，再转为：

```text
TAI = exp(-MMD^2)
```

9. 边界识别：
   - `A_clear_auto_archive`：最高概率、ARS、主次类边际差、熵和 MII 均满足清晰归档条件。
   - `A_assisted_archive`：可归档，但建议保留系统解释或抽检。
   - `B_overlap_manual_review`：前两类概率接近，属于多类别重叠。
   - `C_unknown_expert_review`：低概率、低质量、分布外或无法形成稳定迁移表征。

### 参数定义

```text
n_clusters = 10
max_terms = 2500
embedding_dim = 80
min_model_text_len = 40
min_model_parse_quality = 0.35
alpha_ars = 0.60
probability_temperature_scale = 0.12 * median(source_nearest_center_distance)
lexical_probability_weight = 0.45
meta_feature_weight = 1.00
```

状态阈值：

```text
A_clear_auto_archive:
  p1 >= 0.34
  ARS >= 0.36
  relative_margin >= 0.18
  entropy <= 0.88
  MII >= 0.03

B_overlap_manual_review:
  relative_margin < 0.10
  or (p1 < 0.26 and probability_margin < 0.03)

C_unknown_expert_review:
  p1 < 0.18
  or entropy > 0.92
  or parse_quality < 0.35
```

### 已验证结论

运行结果：

```text
source_document_count = 2225
target_document_count = 4519
target_modelable_count = 4419
target_unclassifiable_count = 100
clusters = 10
term_count = 2500
embedding_dim = 80
dataset2_TAI = 0.622962
dataset3_TAI = 0.590697
```

数据集级评价：

| 数据集 | 记录数 | 自动/辅助归档 | 清晰自动归档 | 重叠复核 | 未知专家复核 | 平均主类概率 | 平均 ARS | 平均 MII | TAI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dataset2 | 1001 | 874 | 129 | 16 | 111 | 0.312426 | 0.409915 | 0.243360 | 0.622962 |
| dataset3 | 3518 | 2449 | 649 | 769 | 300 | 0.306985 | 0.309476 | 0.349149 | 0.590697 |

中间结论：

- 数据集 2 作为半结构化流入数据，迁移适用性和清晰归档比例更高。
- 用户抽样 `docs/dataset3抽样.md` 显示数据集 3 养老主题并不占主导；初版结果中 dataset3 大量吸附到 `养老服务机构类` 属于模型偏差。
- 已修正问题二模型：保持问题一源域主题体系不变，新增语义锚定概率校准，过滤“服务/中心/项目/单位”等泛词，并补充教育、养老、生态、制造、文旅、财政等主题锚词。
- 修正后 dataset3 主题分布不再集中于养老类，主要分布为教育教学管理类 1409、项目案件信息类 673、文旅活动评价类 466、养老服务机构类 439、社会民生指标类 143、资金财政统计类 120、制造业产业统计类 101、城市月度指标类 65、生态环境治理类 62、居民收入统计类 18。
- 数据集 3 作为匿名真实文件/行记录，边界复核比例显著更高，符合“信息不完整、来源匿名、主题重叠”的题面描述。
- 新模型没有把所有低置信样本简单丢弃，而是拆分为重叠复核和未知专家研判，方便后续问题三接入错分风险与人工复核优先级。

### TODO

- [x] 完成题目二创新迁移分类模型代码。
- [x] 输出题目二分类表、评价表、边界样本表、Markdown 报告和三张图。
- [x] 为每张题目二 PNG 图同步输出中英文作图数据表：`*_plot_data.csv` 与 `*.png.csv`。
- [x] 验证代码可编译：`python -m compileall src\mcm_b scripts\run_problem2_transfer.py` 通过。
- [ ] `python -m unittest discover -s tests` 当前无法运行，因为工作区没有可导入的 `tests/` 目录；如需测试，应补建测试目录或运行既有独立测试脚本。
- [x] 新增 `docs/problem2论文描述.md`，汇总题目二算法步骤、数学推导、模型参数、输出解释和图表解释。

## 2026-05-08 题目三创新实现记录

用户要求开始解决最后的问题三：继续阅读 `docs/题目.md` 与 `docs/解析.md`，结合问题二结果，加入自己的创新思路，完成代码实现并生成好看的输出；论文描述需等用户审核通过后再写。

### 当前问题定义

问题三承接问题二的迁移归属结果，需要对数据集 2、数据集 3 的 4519 条后续流入文件，从以下三方面划分高/中/低等级：

1. 紧急程度：识别高时效、限期、通知、公示、考试、会议、整改等文件。
2. 错分风险：利用问题二概率、熵、主次类边际差、迁移适用性和解析质量判断分类不稳定性。
3. 复核必要性：综合主题不明确、类别重叠、低解释性、资金相关和高时效信号。

重点关注对象：

```text
主题不明确文件：C_unknown_expert_review
多类别重叠文件：B_overlap_manual_review
高时效文件：含 deadline/urgent/通知/公示/截止/会议/考试等信号
资金分配相关文件：含 资金/财政/预算/补助/经费/投资/收入/支出 等信号
```

最终目标是在数据集 4 的 S1/S2/S3 三种资源约束下，判断是否需要人工复核、给出复核优先顺序，并比较三种场景下的处理效果。

### 已完成内容

新增代码：

```text
src/mcm_b/problem3_optimization.py
scripts/run_problem3_optimization.py
```

运行命令：

```powershell
.\.venv\Scripts\python.exe scripts\run_problem3_optimization.py --cleaning-dir outputs\b_problem\cleaning_ocr_full --problem2-dir outputs\b_problem\problem2_transfer --output-dir outputs\b_problem\problem3_optimization
```

输出目录：

```text
outputs/b_problem/problem3_optimization/
├── problem3_risk_priority.csv                         # 每条文件的三维评分、等级、重点原因和建议动作
├── problem3_level_summary.csv                         # 紧急/风险/复核必要性/综合优先级的高中低分布
├── problem3_scenario_comparison.csv                   # S1/S2/S3 资源约束对比
├── problem3_special_focus.csv                         # 主题不明确、高时效、资金相关样本清单
├── problem3_review_queue_S1.csv                       # S1 复核队列
├── problem3_review_queue_S2.csv                       # S2 复核队列
├── problem3_review_queue_S3.csv                       # S3 复核队列
├── problem3_auto_archive_S1.csv                       # S1 自动归档队列
├── problem3_auto_archive_S2.csv                       # S2 自动归档队列
├── problem3_auto_archive_S3.csv                       # S3 自动归档队列
├── problem3_optimization_report.md                    # 审核用 Markdown 报告
├── problem3_metrics.json                              # 模型参数与运行指标
├── problem3_level_distribution.png                    # 三维等级分布图
├── problem3_level_distribution_plot_data.csv
├── problem3_level_distribution.png.csv
├── problem3_scenario_comparison.png                   # 三场景处理量对比图
├── problem3_scenario_comparison_plot_data.csv
├── problem3_scenario_comparison.png.csv
├── problem3_action_distribution.png                   # 建议动作分布图
├── problem3_action_distribution_plot_data.csv
├── problem3_action_distribution.png.csv
├── problem3_review_queue_topic_distribution.png       # 复核队列主题分布图
├── problem3_review_queue_topic_distribution_plot_data.csv
└── problem3_review_queue_topic_distribution.png.csv
```

和问题二保持一致：每张 PNG 都有 `*_plot_data.csv` 和 `*.png.csv` 两份同源作图数据，包含中文标签、英文标签和原始数值，方便论文手重画图。

### 创新模型实现

当前题目三采用“熵权-AHP 融合 + 特殊关注增强 + 资源约束优先队列”的治理优化模型，可称为：

```text
RTF-RPO: Risk-Timeliness-Fund Review Priority Optimizer
```

核心思路不是把问题三简化成单一阈值判断，而是把每个文件拆成三个治理维度：

1. `urgency_score`：时效信号、截止/紧急字段、日期新近性、项目属性。
2. `misclassification_risk_score`：问题二分类不确定性，包括 `1-p1`、归一化熵、`1-relative_margin`、`1-TAI`、`1-parse_quality`。
3. `review_necessity_score`：人工复核必要性，包括问题二状态、错分风险、`1-MII`、资金信号和时效信号。

特殊关注增强项：

```text
special_focus = 主题不明确 or 高时效 or 资金相关
priority_score = base_priority_score * (1 + mu * special_focus)
mu = 0.18
```

资源分配策略：

1. `C_unknown_expert_review` 和 `B_overlap_manual_review` 属于必须复核池，优先进入资源分配。
2. 高时效/资金相关但仍可归档的文件进入 `priority_sampling`，作为重点抽检池。
3. 同一优先层内按照 `overall_level`、`priority_score`、`value_density` 排序。
4. 自动归档池按照 `archive_score = 0.45*p1 + 0.35*ARS + 0.20*MII` 排序。
5. 每个场景同时满足人工工时上限、人工复核数量上限和自动归档数量上限。

### 数据集 4 资源约束

当前从 `B题数据集/数据集4：业务规则与资源约束表.xlsx` 读取三种场景：

| 场景 | 人工工时/天 | 自动归档上限/天 | 人工复核上限/天 |
| --- | ---: | ---: | ---: |
| S1 | 60 | 1200 | 200 |
| S2 | 80 | 1500 | 300 |
| S3 | 100 | 1800 | 400 |

注意：最终复核条数低于人工复核上限，是因为每条文件估计复核时间不同；模型优先填满人工工时约束，而不是机械凑满件数约束。

### 参数定义

主观权重：

```text
urgency = 0.34
misclassification_risk = 0.38
review_necessity = 0.28
```

客观熵权：

```text
urgency = 0.912352
misclassification_risk = 0.014840
review_necessity = 0.072808
```

融合方式：

```text
combined_weight = (1 - entropy_blend) * subjective_weight + entropy_blend * entropy_weight
entropy_blend = 0.35
```

最终综合权重：

```text
urgency = 0.540323
misclassification_risk = 0.252194
review_necessity = 0.207483
```

等级划分规则：

```text
高：score >= Q70
中：Q30 <= score < Q70
低：score < Q30
```

复核时间估计：

```text
base = 10 + min(16, log(1 + text_length) * 1.8)
C_unknown_expert_review: +7 min
B_overlap_manual_review: +4 min
资金相关: +3 min
高时效: +2 min
最终限制在 8-35 min
```

### 已验证结论

代码验证：

```text
python -m compileall src\mcm_b\problem3_optimization.py scripts\run_problem3_optimization.py
结果：通过
```

等级分布：

| 维度 | 高 | 中 | 低 |
| --- | ---: | ---: | ---: |
| 紧急程度 | 1622 | 2738 | 159 |
| 错分风险 | 1356 | 1807 | 1356 |
| 复核必要性 | 1356 | 1807 | 1356 |
| 综合优先级 | 1357 | 1806 | 1356 |

资源场景对比：

| 场景 | 复核数 | 复核工时 | 人工利用率 | 自动归档数 | 延后处理数 | 覆盖复核价值 | 剩余风险值 | 未知复核 | 重叠复核 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 139 | 59.929 | 0.998816 | 1200 | 3180 | 89.095011 | 1571.252062 | 47 | 92 |
| S2 | 188 | 79.844 | 0.998044 | 1500 | 2831 | 116.972854 | 1437.748244 | 58 | 130 |
| S3 | 237 | 99.927 | 0.999265 | 1800 | 2482 | 144.373171 | 1295.410566 | 78 | 159 |

中间结论：

- S3 资源最充足，能够复核更多主题不明确和重叠样本，剩余风险最低，适合高风险时期或正式归档前集中治理。
- S1 资源最紧，应优先处理 C/B 必须复核文件中的高优先级样本，并将重点抽检与低风险自动归档延后。
- 三个场景人工利用率均接近 100%，说明队列选择充分利用了数据集 4 的人工工时预算。
- 队列前排主要是 `C_unknown_expert_review` 且同时命中“主题不明确、高时效、资金相关”的样本，符合题目对重点关注对象的要求。
- 当前模型输出了自动归档队列和人工复核队列，可直接作为实际办公场景下的日处理建议清单。

### TODO

- [x] 完成题目三创新复核优先级与资源约束优化代码。
- [x] 生成三维等级表、场景对比表、复核队列、自动归档队列、重点关注样本表和审核报告。
- [x] 为每张题目三 PNG 图同步输出中英文作图数据表：`*_plot_data.csv` 与 `*.png.csv`。
- [x] 修正复核队列排序：C/B 必须复核类优先，重点抽检类次之，同层内按综合优先级排序。
- [x] 验证代码可编译。
- [x] 已新增 `docs/problem3论文描述.md`。

## 2026-05-08 全流程重跑与最终验收记录

用户要求清空 `outputs/b_problem` 后，从数据清洗开始完整重跑三问，并检查解析文末建议的五类结果表和图。

### 已完成内容

- 已清空 `outputs/b_problem` 旧结果并从全量清洗重跑。
- 已完成全量 OCR 清洗、问题一创新主题建模、问题二迁移归属、问题三复核优化。
- 已新增最终交付汇总脚本：`scripts/build_final_deliverables.py`。
- 已生成最终论文结果目录：`outputs/b_problem/final_results/`。
- 已新建 `docs/problem3论文描述.md`。
- 已同步更新 `docs/problem1论文描述.md` 与 `docs/problem2论文描述.md` 中的最新模型参数、阈值、结果表和符号说明。

### 关键修正

1. 问题一新增业务锚点增强：
   - 新增 `TOPIC_ANCHORS` 和 `ANCHOR_EMBEDDING_WEIGHT = 3.0`。
   - 将业务锚点矩阵 `A` 与图传播文本向量、结构业务特征一起融合。
   - 修复纯聚类被“地区/单位/服务/项目”等泛词牵引的问题。

2. 问题二同步使用业务锚点空间：
   - 源域和目标域均拼接同一套锚点特征。
   - 保持问题二与问题一主题空间一致。
   - 根据锚点增强后的概率分布，调整状态阈值：

```text
A_clear_auto_archive:
  p1 >= 0.30
  ARS >= 0.30
  relative_margin >= 0.12
  entropy <= 0.90
  MII >= 0.03

B_overlap_manual_review:
  relative_margin < 0.08
  or (p1 < 0.22 and probability_margin < 0.025)

C_unknown_expert_review:
  p1 < 0.16
  or entropy > 0.97
  or parse_quality < 0.35
```

3. 问题三资源队列修正：
   - 专家研判 `expert_review` 优先于重叠人工复核 `manual_review`。
   - 重叠人工复核优先于重点抽检 `priority_sampling`。
   - 场景对比表新增解析要求字段：`total_cost_index`、`max_completion_hours`、`unreviewed_risk_value`、`high_level_coverage_rate`。

### 全流程命令

```powershell
$env:PADDLEOCR_DEVICE='gpu:0'
.\.venv\Scripts\python.exe scripts\run_b_cleaning.py --output-dir outputs\b_problem\cleaning_ocr_full --max-chars 30000 --max-file-mb 25
.\.venv\Scripts\python.exe scripts\run_problem1_innovative.py --cleaning-dir outputs\b_problem\cleaning_ocr_full --output-dir outputs\b_problem\problem1_innovative --clusters 10 --max-terms 2500
.\.venv\Scripts\python.exe scripts\run_problem2_transfer.py --cleaning-dir outputs\b_problem\cleaning_ocr_full --output-dir outputs\b_problem\problem2_transfer --clusters 10 --max-terms 2500
.\.venv\Scripts\python.exe scripts\run_problem3_optimization.py --cleaning-dir outputs\b_problem\cleaning_ocr_full --problem2-dir outputs\b_problem\problem2_transfer --output-dir outputs\b_problem\problem3_optimization
.\.venv\Scripts\python.exe scripts\build_final_deliverables.py --cleaning-dir outputs\b_problem\cleaning_ocr_full --problem1-dir outputs\b_problem\problem1_innovative --problem2-dir outputs\b_problem\problem2_transfer --problem3-dir outputs\b_problem\problem3_optimization --output-dir outputs\b_problem\final_results
```

### 清洗结果

```text
document_count = 7916
block_count = 598480
parse_success_count = 6733
need_manual_check = 200
ocr_rows = 1990
avg_ocr_confidence = 0.989121
```

解析方式统计：

```text
dataset3_row_parse = 3518
image_paddleocr = 1990
image_sidecar_txt:utf-8-sig = 1127
docx_parse = 617
txt_parse:utf-8-sig = 351
excel_parse = 176
text_pdf = 76
scanned_pdf_ocr_pending = 54
scanned_pdf_text_low = 5
metadata_only = 2
```

### 问题一结果

```text
source_document_count = 2225
term_count = 2500
clusters = 10
silhouette = 0.035421
calinski_harabasz = 39.333307
davies_bouldin = 3.439216
word_graph_edges = 366841
word_graph_windows = 404135
```

主题体系：

| topic_id | 主题名称 | 样本数 |
| ---: | --- | ---: |
| 6 | 资金财政统计类 | 567 |
| 1 | 医药项目审批类 | 535 |
| 4 | 地区统计指标类 | 375 |
| 8 | 制造业产业统计类 | 256 |
| 3 | 教育教学管理类 | 174 |
| 2 | 生态环境治理类 | 136 |
| 5 | 养老服务机构类 | 59 |
| 0 | 投资价格统计类 | 49 |
| 7 | 项目案件信息类 | 39 |
| 9 | 教育基础统计类 | 35 |

### 问题二结果

```text
target_document_count = 4519
target_modelable_count = 4419
target_unclassifiable_count = 100
dataset2_TAI = 0.588393
dataset3_TAI = 0.699263
```

数据集级评价：

| 数据集 | 记录数 | 自动/辅助归档 | 清晰自动归档 | 重叠复核 | 未知专家复核 | 平均主类概率 | 平均 ARS | 平均 MII | 平均熵 | TAI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dataset2 | 1001 | 787 | 57 | 134 | 80 | 0.233601 | 0.240491 | 0.266731 | 0.912906 | 0.588393 |
| dataset3 | 3518 | 3263 | 1630 | 233 | 22 | 0.386241 | 0.418351 | 0.348885 | 0.771414 | 0.699263 |

### 问题三结果

场景对比：

| 场景 | 复核数 | 总成本指数 | 最大完工时间/小时 | 未复核风险 | 高等级覆盖率 | 自动归档数 | 未知复核 | 重叠复核 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 137 | 59.978900 | 59.979 | 1490.465329 | 0.101032 | 1200 | 102 | 34 |
| S2 | 173 | 79.929683 | 79.930 | 1363.929117 | 0.127581 | 1500 | 102 | 71 |
| S3 | 210 | 99.829683 | 99.830 | 1236.019877 | 0.154867 | 1800 | 102 | 108 |

### 解析文末五类最终交付表

输出目录：

```text
outputs/b_problem/final_results/
```

| 解析要求 | 当前输出 |
| --- | --- |
| 数据预处理统计表 | `data_preprocessing_statistics.csv` |
| 问题一分类结果表 | `problem1_classification_result_table.csv` |
| 问题二归属评价表 | `problem2_assignment_evaluation_table.csv` |
| 问题三复核优先级表 | `problem3_review_priority_table.csv` |
| 资源约束场景对比表 | `resource_scenario_comparison_table.csv` |

### 输出图与作图数据

已检查全部 PNG 均有同名 `.png.csv` 和 `_plot_data.csv`：

```text
final_results/data_preprocessing_file_type_distribution.png
problem2_transfer/problem2_topic_distribution.png
problem2_transfer/problem2_state_distribution.png
problem2_transfer/problem2_ars_mii_scatter.png
problem3_optimization/problem3_level_distribution.png
problem3_optimization/problem3_scenario_comparison.png
problem3_optimization/problem3_action_distribution.png
problem3_optimization/problem3_review_queue_topic_distribution.png
```

### TODO

- [x] 完成从清洗到三问的全流程重跑。
- [x] 修正问题一泛词牵引和重复泛化主题问题。
- [x] 修正问题二锚点增强后未知样本过多的问题。
- [x] 修正问题三专家研判优先级。
- [x] 生成五类最终交付表。
- [x] 为所有 PNG 图生成同名作图数据。
- [x] 新增问题三论文描述。

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
- [x] 跑完整 PaddleOCR 清洗：输出 `outputs/b_problem/cleaning_ocr_full/`。
- [x] 基于 `cleaning_ocr_full` 跑主链路：输出 `outputs/b_problem/run_ocr_full/`。
- [x] 检查 OCR 后问题一主题是否比 `run_cleaned_v2` 更合理，并过滤数字/模板噪声重跑。
- [x] 更新论文可用的清洗统计表和质量控制说明，当前复核数已按数据集 4 重校准。

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
2026-05-08: 本轮接手后新增资源感知复核重校准：运行 `.\.venv\Scripts\python.exe scripts\recalibrate_cleaning_review.py --cleaning-dir outputs\b_problem\cleaning_ocr_full`，将 `need_manual_check` 从旧规则的 6781 调整为 S1 基准 200，硬风险 90，自动归档 6589，元数据归档 1127。
2026-05-08: 本轮基于优化后的全量 OCR 清洗输出运行 `.\.venv\Scripts\python.exe scripts\run_b_pipeline.py --clusters 10 --cleaning-dir outputs\b_problem\cleaning_ocr_full --output-dir outputs\b_problem\run_ocr_full --max-chars 30000 --max-file-mb 25`，已生成问题一主题体系、问题二归类结果和问题三复核队列。
2026-05-08: 本轮对问题一建模文本做二次清洗：过滤数字、小数点、英文编码和 Excel 模板词，仅保留中文语义和业务关键词；同时给主题摘要增加代表文件和人工可解释主题命名规则。
```
