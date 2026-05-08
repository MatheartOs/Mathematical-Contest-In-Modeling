"""Innovative Problem 1 model: heterogeneous graph propagation + c-TF-IDF.

"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math
import re

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import Normalizer, StandardScaler


BUSINESS_COLUMNS = [
    "has_notice",
    "has_meeting",
    "has_project",
    "has_money",
    "has_contract",
    "has_personnel",
    "has_deadline",
    "has_urgent",
]

STRUCTURE_COLUMNS = [
    "page_count",
    "paragraph_count",
    "table_count",
    "image_count",
    "heading_count",
    "parse_quality",
    "ocr_confidence",
    "missing_rate",
]

NOISE_TERMS = (
    "工作表名称",
    "表头字段",
    "主要关键词",
    "样例内容",
    "图片名称",
    "图片编号",
    "下载",
    "关键词",
)

GENERIC_TOPIC_TERMS = {
    "地区",
    "其他",
    "单位",
    "数据",
    "服务",
    "研究",
    "工作",
    "管理",
    "技术",
    "中心",
    "包括",
    "数字",
    "年份",
    "合计",
    "相关",
    "主要",
    "模型",
}

TOPIC_ANCHORS = {
    "文旅活动评价类": ("文化", "文博", "博物馆", "文物", "遗产", "旅游", "体育", "活动", "讲座", "论坛", "展览", "冰雪", "滑雪"),
    "资金财政统计类": ("资金", "财政", "预算", "经费", "补助", "亿元", "万元", "投资", "金融", "利润", "价格", "支出"),
    "生态环境治理类": ("生态", "环境", "污染", "水质", "水资源", "能源", "低碳", "绿色", "气候", "排放", "废物", "固体废物"),
    "教育教学管理类": ("教学", "教师", "学生", "课程", "教育", "学院", "学校", "本科", "人才", "培养", "毕业", "招生"),
    "养老服务机构类": ("老年", "养老", "老年公寓", "公寓", "康养", "适老", "老人", "护理院", "养老院"),
    "制造业产业统计类": ("制造", "制造业", "工业", "生产", "装备", "行业", "增加值", "高技术", "规模以上", "器件", "制品业"),
    "居民收入统计类": ("居民", "收入", "人均", "可支配", "净收入", "工资", "消费"),
    "社会民生指标类": ("人口", "卫生", "汽车", "里程", "住房", "民生", "政务", "公开", "招聘", "公务员"),
    "城市月度指标类": ("城市", "成都", "重庆", "兰州", "西安", "江门", "城乡", "街区", "新区"),
    "项目案件信息类": ("项目", "案件", "企业", "科技", "创新", "合作", "政策", "政府", "规划", "审批", "开发", "合同", "协议"),
}

ANCHOR_EMBEDDING_WEIGHT = 3.0


@dataclass
class Problem1GraphResult:
    assignments: pd.DataFrame
    topic_summary: pd.DataFrame
    metrics: dict[str, object]
    enhanced_matrix: sparse.csr_matrix


def run_problem1_graph_model(
    document_index: pd.DataFrame,
    n_clusters: int = 10,
    max_terms: int = 2500,
    random_state: int = 42,
) -> Problem1GraphResult:
    """Build the graph-enhanced topic system for dataset 1."""

    history = _history_frame(document_index)
    if history.empty:
        raise ValueError("No usable dataset1 records for Problem 1.")

    texts = history.apply(_modeling_text, axis=1).tolist()
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        min_df=2,
        max_df=0.88,
        max_features=max_terms,
        sublinear_tf=True,
    )
    doc_word = vectorizer.fit_transform(texts).tocsr()
    terms = vectorizer.get_feature_names_out().tolist()
    word_graph, graph_stats = _build_ppmi_graph(texts, terms)
    propagated = _two_hop_propagation(doc_word, word_graph)
    structure = _structure_business_matrix(history)
    anchor_features = _anchor_feature_matrix(texts, history)
    enhanced = sparse.hstack([propagated, structure, sparse.csr_matrix(anchor_features * ANCHOR_EMBEDDING_WEIGHT)], format="csr")
    enhanced = Normalizer(copy=False).fit_transform(enhanced)

    embedding_dim = min(80, max(2, enhanced.shape[1] - 1), max(2, enhanced.shape[0] - 1))
    embedding = TruncatedSVD(n_components=embedding_dim, random_state=random_state).fit_transform(enhanced)
    anchor_embedding = StandardScaler().fit_transform(anchor_features)
    embedding = np.hstack([embedding, anchor_embedding * ANCHOR_EMBEDDING_WEIGHT])
    embedding = StandardScaler().fit_transform(embedding)
    n_clusters = max(2, min(n_clusters, len(history)))
    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    labels = model.fit_predict(embedding)

    assignments = history[
        [
            "file_id",
            "original_id",
            "dataset_id",
            "file_name",
            "file_type",
            "parse_method",
            "parse_quality",
            "text_length",
            *BUSINESS_COLUMNS,
        ]
    ].copy()
    assignments["topic_id"] = labels

    topic_summary = _topic_summary(assignments, history, texts, labels, n_clusters)
    metrics = _cluster_metrics(embedding, labels)
    metrics.update(
        {
            "model": "heterogeneous_graph_ppmi_ctfidf",
            "document_count": int(len(history)),
            "term_count": int(len(terms)),
            "clusters": int(n_clusters),
            **graph_stats,
        }
    )
    return Problem1GraphResult(assignments, topic_summary, metrics, enhanced)


def _history_frame(document_index: pd.DataFrame) -> pd.DataFrame:
    frame = document_index.copy()
    frame = frame[frame["dataset_id"] == "dataset1"].copy()
    method = frame["parse_method"].fillna("").astype(str)
    frame = frame[~method.str.startswith("image_sidecar")].copy()
    frame = frame[(frame["parse_quality"].fillna(0) >= 0.45) & (frame["clean_text"].fillna("").str.len() >= 40)].copy()
    return frame.reset_index(drop=True)


def _modeling_text(row: pd.Series) -> str:
    title = "" if pd.isna(row.get("title")) else str(row.get("title"))
    body = "" if pd.isna(row.get("clean_text")) else str(row.get("clean_text"))
    keywords = "" if pd.isna(row.get("business_keywords")) else str(row.get("business_keywords"))
    text = "\n".join([title, body, keywords])
    text = re.sub(r"[A-Za-z0-9]+(?:[./:_-][A-Za-z0-9]+)*", " ", text)
    text = re.sub(r"[^\u4e00-\u9fff]+", "", text)
    for noise in NOISE_TERMS:
        text = text.replace(noise, "")
    return text


def _build_ppmi_graph(texts: list[str], terms: list[str], window_size: int = 18) -> tuple[sparse.csr_matrix, dict[str, object]]:
    term_to_index = {term: index for index, term in enumerate(terms)}
    unigram_windows: Counter[int] = Counter()
    pair_windows: Counter[tuple[int, int]] = Counter()
    total_windows = 0

    for text in texts:
        tokens = _tokens_for_graph(text, term_to_index)
        if not tokens:
            continue
        for start in range(max(1, len(tokens) - window_size + 1)):
            window = tokens[start : start + window_size]
            unique = sorted(set(window))
            if not unique:
                continue
            total_windows += 1
            for item in unique:
                unigram_windows[item] += 1
            for left_pos, left in enumerate(unique):
                for right in unique[left_pos + 1 :]:
                    pair_windows[(left, right)] += 1

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    if total_windows:
        for (left, right), count in pair_windows.items():
            denominator = unigram_windows[left] * unigram_windows[right]
            if denominator <= 0:
                continue
            pmi = math.log((count * total_windows) / denominator)
            if pmi <= 0:
                continue
            value = min(pmi, 8.0)
            rows.extend([left, right])
            cols.extend([right, left])
            data.extend([value, value])

    graph = sparse.csr_matrix((data, (rows, cols)), shape=(len(terms), len(terms)))
    graph = _row_normalize(graph)
    return graph, {"word_graph_edges": int(len(data) // 2), "word_graph_windows": int(total_windows)}


def _tokens_for_graph(text: str, term_to_index: dict[str, int]) -> list[int]:
    tokens: list[int] = []
    for length in (2, 3, 4):
        for index in range(0, max(0, len(text) - length + 1)):
            token = text[index : index + length]
            term_index = term_to_index.get(token)
            if term_index is not None:
                tokens.append(term_index)
    return tokens[:2000]


def _two_hop_propagation(doc_word: sparse.csr_matrix, word_graph: sparse.csr_matrix) -> sparse.csr_matrix:
    if word_graph.nnz == 0:
        return doc_word
    hop1 = doc_word @ word_graph
    hop2 = hop1 @ word_graph
    return (doc_word + 0.60 * hop1 + 0.30 * hop2).tocsr()


def _row_normalize(matrix: sparse.csr_matrix) -> sparse.csr_matrix:
    row_sum = np.asarray(matrix.sum(axis=1)).ravel()
    row_sum[row_sum == 0] = 1.0
    inv = sparse.diags(1.0 / row_sum)
    return inv @ matrix


def _structure_business_matrix(frame: pd.DataFrame) -> sparse.csr_matrix:
    numeric = pd.DataFrame(index=frame.index)
    for column in STRUCTURE_COLUMNS:
        numeric[column] = pd.to_numeric(frame.get(column, 0), errors="coerce").fillna(0.0)
    numeric["log_text_length"] = np.log1p(pd.to_numeric(frame.get("text_length", 0), errors="coerce").fillna(0.0))
    numeric["log_file_size"] = np.log1p(pd.to_numeric(frame.get("file_size_kb", 0), errors="coerce").fillna(0.0))
    for column in BUSINESS_COLUMNS:
        numeric[column] = pd.to_numeric(frame.get(column, 0), errors="coerce").fillna(0.0)
    scaled = StandardScaler().fit_transform(numeric)
    return sparse.csr_matrix(scaled)


def _anchor_feature_matrix(texts: list[str], frame: pd.DataFrame) -> np.ndarray:
    """Weak business anchors keep broad office terms from dominating clusters."""

    rows: list[list[float]] = []
    for text, (_, row) in zip(texts, frame.iterrows()):
        text = "" if pd.isna(text) else str(text)
        row_features: list[float] = []
        for topic_name, anchors in TOPIC_ANCHORS.items():
            hits = sum(text.count(anchor) for anchor in anchors)
            score = math.log1p(hits)
            if topic_name == "资金财政统计类" and int(row.get("has_money", 0) or 0):
                score += 0.75
            if topic_name == "项目案件信息类" and int(row.get("has_project", 0) or 0):
                score += 0.55
            if topic_name == "项目案件信息类" and int(row.get("has_contract", 0) or 0):
                score += 0.65
            if topic_name == "教育教学管理类" and any(term in text for term in ("教学", "教师", "学生", "课程", "学院")):
                score += 0.35
            if topic_name == "养老服务机构类" and any(term in text for term in ("老年", "养老", "公寓")):
                score += 0.35
            row_features.append(score)
        rows.append(row_features)
    matrix = np.asarray(rows, dtype=float)
    if matrix.size == 0:
        return np.zeros((len(frame), len(TOPIC_ANCHORS)), dtype=float)
    maximum = matrix.max(axis=1, keepdims=True)
    maximum[maximum <= 0] = 1.0
    return matrix / maximum


def _topic_summary(
    assignments: pd.DataFrame,
    history: pd.DataFrame,
    texts: list[str],
    labels: np.ndarray,
    n_clusters: int,
) -> pd.DataFrame:
    tokens_by_doc = [_ctfidf_tokens(text) for text in texts]
    class_term_counts: list[Counter[str]] = [Counter() for _ in range(n_clusters)]
    term_class_frequency: Counter[str] = Counter()
    for topic_id in range(n_clusters):
        seen_in_class: set[str] = set()
        for doc_tokens, label in zip(tokens_by_doc, labels):
            if label != topic_id:
                continue
            class_term_counts[topic_id].update(doc_tokens)
            seen_in_class.update(doc_tokens)
        for token in seen_in_class:
            term_class_frequency[token] += 1

    rows: list[dict[str, object]] = []
    merged = assignments.join(history[["title", "clean_text", "business_keywords"]])
    avg_class_len = np.mean([sum(counter.values()) for counter in class_term_counts]) or 1.0
    for topic_id, group in merged.groupby("topic_id"):
        counter = class_term_counts[int(topic_id)]
        scored_terms = []
        for term, tf in counter.items():
            idf = math.log(1.0 + avg_class_len / max(1, term_class_frequency[term]))
            scored_terms.append((term, tf * idf))
        top_terms = [term for term, _ in sorted(scored_terms, key=lambda item: (-item[1], item[0]))[:12]]
        representative = _representatives(group, top_terms)
        rows.append(
            {
                "topic_id": int(topic_id),
                "history_count": int(len(group)),
                "topic_name": _name_topic(top_terms, group),
                "ctfidf_terms": " / ".join(top_terms),
                "dominant_file_types": _value_counts(group["file_type"], top_n=4),
                "business_profile": _business_profile(group),
                "representative_files": "; ".join(representative["file_id"].astype(str).tolist()),
                "representative_titles": "; ".join(representative["title"].fillna("").astype(str).str[:36].tolist()),
                "topic_explanation": _topic_explanation(top_terms, group),
            }
        )
    return pd.DataFrame(rows).sort_values(["history_count", "topic_id"], ascending=[False, True])


def _ctfidf_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for length in (2, 3, 4):
        tokens.extend(text[index : index + length] for index in range(max(0, len(text) - length + 1)))
    return [token for token in tokens if not _is_bad_token(token)]


def _is_bad_token(token: str) -> bool:
    if len(set(token)) == 1:
        return True
    if token in GENERIC_TOPIC_TERMS:
        return True
    return any(noise in token for noise in NOISE_TERMS)


def _representatives(group: pd.DataFrame, top_terms: list[str], top_n: int = 4) -> pd.DataFrame:
    def score(row: pd.Series) -> float:
        text = "" if pd.isna(row.get("clean_text")) else str(row.get("clean_text"))
        return sum(text.count(term) for term in top_terms[:6]) + float(row.get("parse_quality", 0))

    ranked = group.copy()
    ranked["_representative_score"] = ranked.apply(score, axis=1)
    return ranked.sort_values(["_representative_score", "parse_quality"], ascending=[False, False]).head(top_n)


def _name_topic(terms: list[str], group: pd.DataFrame) -> str:
    joined = "".join(terms)
    if any(term in joined for term in ("药品", "试验", "申请", "标准")):
        return "医药项目审批类"
    if any(term in joined for term in ("固定资产", "固定资", "价格指数", "价格指", "资产投资")):
        return "投资价格统计类"
    if any(term in joined for term in ("冰雪", "滑雪", "长春")):
        return "文旅活动评价类"
    if any(term in joined for term in ("合同", "协议", "工程", "审批", "案件")):
        return "项目案件信息类"
    if any(term in joined for term in ("老年公寓", "老年", "养老", "公寓")):
        return "养老服务机构类"
    if any(term in joined for term in ("普通高中", "普通高", "初中", "高中", "小学", "职业", "专科")):
        return "教育基础统计类"
    if any(term in joined for term in ("教学", "教师", "学生", "课程", "学院", "学校", "普通高中", "初中", "小学")):
        return "教育教学管理类"
    if any(term in joined for term in ("污染", "环境", "水资源", "水质", "固体废物", "废物")):
        return "生态环境治理类"
    if any(term in joined for term in ("居民", "可支配", "支配收入", "人均")):
        return "居民收入统计类"
    if any(term in joined for term in ("资金", "收入", "支出", "亿元", "预算", "经费")) or group.get("has_money", pd.Series(dtype=int)).sum() >= max(8, len(group) * 0.15):
        return "资金财政统计类"
    if any(term in joined for term in ("制造业", "制品业", "设备制造", "金属", "生产总值", "国内生产", "总值")):
        return "制造业产业统计类"
    if any(term in joined for term in ("服务业", "批发", "零售", "仓储")):
        return "服务业经营统计类"
    if "企业" in joined and any(term in joined for term in ("投资", "外商", "股份", "有限")):
        return "企业投资主体类"
    if any(term in joined for term in ("项目", "案件", "机构")):
        return "项目案件信息类"
    if any(term in joined for term in ("人口", "卫生", "里程", "汽车", "公里")):
        return "社会民生指标类"
    if any(term in joined for term in ("地区", "黑龙江", "天津", "河北", "内蒙古")):
        return "地区统计指标类"
    if any(term in joined for term in ("城市", "成都", "西宁", "济南", "兰州")):
        return "城市月度指标类"
    if group.get("has_contract", pd.Series(dtype=int)).sum() > 0:
        return "合同协议类"
    if group.get("has_meeting", pd.Series(dtype=int)).sum() > 0:
        return "会议通知类"
    return "综合办公统计类"


def _topic_explanation(terms: list[str], group: pd.DataFrame) -> str:
    signals = []
    if group.get("has_money", pd.Series(dtype=int)).sum() >= max(5, len(group) * 0.10):
        signals.append("含资金/金额线索")
    if group.get("has_deadline", pd.Series(dtype=int)).sum() >= max(5, len(group) * 0.10):
        signals.append("含截止时间线索")
    if group.get("image_count", pd.Series(dtype=int)).sum() >= len(group) * 0.50:
        signals.append("以图片/OCR 文件为主")
    if group.get("table_count", pd.Series(dtype=int)).sum() >= max(5, len(group) * 0.10):
        signals.append("含表格结构")
    prefix = "、".join(signals) if signals else "按文本共现与结构特征聚合"
    return f"{prefix}；代表词为{'、'.join(terms[:5])}。"


def _business_profile(group: pd.DataFrame) -> str:
    items = []
    for column in BUSINESS_COLUMNS:
        if column in group:
            count = int(group[column].fillna(0).astype(int).sum())
            if count:
                items.append(f"{column}:{count}")
    return "; ".join(items) if items else "none"


def _value_counts(series: pd.Series, top_n: int) -> str:
    return "; ".join(f"{key}:{value}" for key, value in series.value_counts().head(top_n).items())


def _cluster_metrics(embedding: np.ndarray, labels: np.ndarray) -> dict[str, object]:
    metrics: dict[str, object] = {}
    if len(set(labels)) > 1 and len(labels) > len(set(labels)):
        metrics["silhouette"] = round(float(silhouette_score(embedding, labels)), 6)
        metrics["calinski_harabasz"] = round(float(calinski_harabasz_score(embedding, labels)), 6)
        metrics["davies_bouldin"] = round(float(davies_bouldin_score(embedding, labels)), 6)
    return metrics
