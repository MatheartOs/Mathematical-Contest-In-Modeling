# Algorithm Sketch

## Problem 1: Historical Topic System

目标是从数据集 1 的历史真实文件中得到稳定、可解释的主题体系。

Baseline:

1. 抽取文本和文件元数据。
2. 构造字符级 TF-IDF，适合中文且不依赖分词库。
3. 用 KMeans 聚类得到主题编号。
4. 输出每簇 top n-gram，再由人工结合样本标题/正文命名主题。

后续增强方向：

1. 加入更强的中文分词和关键词抽取。
2. 对图片/PDF 扫描件引入 OCR。
3. 用层次聚类或 HDBSCAN 处理类别数不确定问题。
4. 使用人工命名后的主题作为伪标签，训练监督分类器。

## Problem 2: Transfer Classification

数据集 2 是后续流入真实/半结构化文件，数据集 3 是匿名文本片段。

Baseline:

1. 复用问题一的 TF-IDF 表示空间。
2. 计算新样本到历史主题中心的距离。
3. 最近中心为归属类别。
4. 用距离 softmax 置信度和第一/第二近距离 margin 标记模糊样本。

评价指标：

| 指标 | 含义 |
| --- | --- |
| `classification_confidence` | 归属置信度 |
| `topic_margin` | 第一候选与第二候选差异 |
| `is_ambiguous` | 多主题或低置信样本标记 |
| 主题关键词覆盖 | 分类解释是否匹配关键词组 |
| 数据源稳定性 | 数据集 2/3 在同一主题下的分布是否偏移 |

## Problem 3: Review Optimization

分数设计：

```text
priority = 0.35 * urgency + 0.35 * misclassification_risk + 0.30 * review_necessity
```

其中：

1. `urgency`：由紧急、政策、政府类关键词归一化得到。
2. `misclassification_risk`：`1 - classification_confidence`。
3. `review_necessity`：融合错分风险、模糊标记和资金相关程度。

需要重点照顾：

1. 主题归属不明确；
2. 时效要求较高；
3. 涉及资金分配、预算、采购、金融等内容。

资源约束处理：

1. 先按 `priority_score` 排序。
2. 对每个场景，根据人工工时和人工复核上限计算可复核数量。
3. 输出 S1/S2/S3 三个复核队列，比较覆盖率和被延后样本特征。
