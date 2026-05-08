"""Problem 2 transfer classification and evaluation.

This module extends the Problem 1 graph topic system to dataset 2 and dataset 3.
It keeps the same text-word PPMI propagation idea, then adds transfer-specific
metrics required by the contest analysis: ARS, MII, MMD/TAI, overlap detection,
and unknown/unclassifiable handling.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import Normalizer, StandardScaler

from .problem1_innovative import (
    BUSINESS_COLUMNS,
    NOISE_TERMS,
    STRUCTURE_COLUMNS,
    _build_ppmi_graph,
    _history_frame,
    _modeling_text,
    _topic_summary,
    _two_hop_propagation,
)


ALPHA_ARS = 0.60
MIN_MODEL_TEXT_LEN = 40
MIN_MODEL_PARSE_QUALITY = 0.35
RANDOM_STATE = 42
META_FEATURE_WEIGHT = 1.00
LEXICAL_PROBABILITY_WEIGHT = 0.45

GENERIC_LEXICAL_TERMS = {
    "项目",
    "单位",
    "地区",
    "其他",
    "数据",
    "技术",
    "服务",
    "研究",
    "工作",
    "管理",
    "建设",
    "中心",
    "方法",
    "模型",
    "系统",
    "包括",
    "电话",
    "时间",
}

TOPIC_ANCHORS = {
    "项目案件信息类": ["项目", "企业", "科技", "创新", "合作", "政策", "政府", "文件", "规划", "审批", "产业", "开发"],
    "资金财政统计类": ["资金", "财政", "收入", "支出", "预算", "经费", "亿元", "投资", "金融", "价格", "利润", "生产资料"],
    "生态环境治理类": ["生态", "环境", "污染", "水质", "水资源", "能源", "低碳", "绿色", "气候", "排放", "清洁", "碳"],
    "文旅活动评价类": ["文化", "文博", "博物馆", "文物", "遗产", "旅游", "体育", "活动", "讲座", "论坛", "悦读", "展览"],
    "养老服务机构类": ["老年", "养老", "养老院", "老年公寓", "年公寓", "公寓", "康养", "适老", "老人", "护理院"],
    "教育教学管理类": ["教学", "教师", "学生", "课程", "教育", "学院", "学校", "大学", "本科", "人才", "培养", "毕业", "论文", "招生", "推免", "成绩"],
    "社会民生指标类": ["人口", "卫生", "汽车", "里程", "住房", "民生", "政务", "公开", "招聘", "公务员", "网站", "办事"],
    "制造业产业统计类": ["制造", "制造业", "工业", "生产", "装备", "行业", "增加值", "高技术", "企业利润", "规模以上", "器件"],
    "居民收入统计类": ["居民", "收入", "人均", "可支配", "净收入", "工资", "消费"],
    "城市月度指标类": ["城市", "成都", "重庆", "兰州", "西安", "江门", "城乡", "街区", "新区", "市政府"],
}


@dataclass
class Problem2TransferResult:
    classification: pd.DataFrame
    dataset_evaluation: pd.DataFrame
    topic_distribution: pd.DataFrame
    boundary_samples: pd.DataFrame
    metrics: dict[str, object]
    topic_summary: pd.DataFrame


def run_problem2_transfer_model(
    document_index: pd.DataFrame,
    output_dir: Path,
    n_clusters: int = 10,
    max_terms: int = 2500,
    random_state: int = RANDOM_STATE,
) -> Problem2TransferResult:
    """Fit the source topic space on dataset 1 and classify dataset 2/3."""

    output_dir.mkdir(parents=True, exist_ok=True)
    history = _history_frame(document_index)
    target_all = _target_frame(document_index)
    if history.empty:
        raise ValueError("No usable dataset1 records for Problem 2 source space.")
    if target_all.empty:
        raise ValueError("No dataset2/dataset3 records found for Problem 2.")

    source_texts = history.apply(_modeling_text, axis=1).tolist()
    target_all = target_all.copy()
    target_all["_modeling_text"] = target_all.apply(_modeling_text, axis=1)
    target_all["_is_modelable"] = target_all.apply(_is_modelable, axis=1)
    target_modelable = target_all[target_all["_is_modelable"]].reset_index(drop=True)

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        min_df=2,
        max_df=0.88,
        max_features=max_terms,
        sublinear_tf=True,
    )
    source_doc_word = vectorizer.fit_transform(source_texts).tocsr()
    terms = vectorizer.get_feature_names_out().tolist()
    word_graph, graph_stats = _build_ppmi_graph(source_texts, terms)

    source_propagated = _two_hop_propagation(source_doc_word, word_graph)
    feature_scaler, source_numeric = _fit_numeric_features(history)
    source_enhanced = sparse.hstack([source_propagated, source_numeric * META_FEATURE_WEIGHT], format="csr")
    normalizer = Normalizer(copy=False)
    source_enhanced = normalizer.fit_transform(source_enhanced)

    embedding_dim = min(80, max(2, source_enhanced.shape[1] - 1), max(2, source_enhanced.shape[0] - 1))
    reducer = TruncatedSVD(n_components=embedding_dim, random_state=random_state)
    source_embedding = reducer.fit_transform(source_enhanced)
    embedding_scaler = StandardScaler()
    source_embedding = embedding_scaler.fit_transform(source_embedding)

    n_clusters = max(2, min(n_clusters, len(history)))
    cluster_model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    source_labels = cluster_model.fit_predict(source_embedding)

    source_assignments = history[
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
    source_assignments["topic_id"] = source_labels
    topic_summary = _topic_summary(source_assignments, history, source_texts, source_labels, n_clusters)
    topic_lookup = topic_summary.set_index("topic_id").to_dict("index")

    if target_modelable.empty:
        classification = _unmodelable_rows(target_all, topic_lookup)
        target_embedding = np.empty((0, source_embedding.shape[1]))
        probabilities = np.empty((0, n_clusters))
    else:
        target_texts = target_modelable["_modeling_text"].tolist()
        target_doc_word = vectorizer.transform(target_texts).tocsr()
        target_propagated = _two_hop_propagation(target_doc_word, word_graph)
        target_numeric = _transform_numeric_features(target_modelable, feature_scaler)
        target_enhanced = sparse.hstack([target_propagated, target_numeric * META_FEATURE_WEIGHT], format="csr")
        target_enhanced = normalizer.transform(target_enhanced)
        target_embedding = embedding_scaler.transform(reducer.transform(target_enhanced))
        distances = pairwise_distances(target_embedding, cluster_model.cluster_centers_, metric="euclidean")
        source_distances = pairwise_distances(source_embedding, cluster_model.cluster_centers_, metric="euclidean")
        distance_probabilities = _distance_probabilities(distances, np.min(source_distances, axis=1))
        lexical_probabilities = _lexical_topic_probabilities(target_texts, topic_summary, n_clusters)
        probabilities = _blend_probabilities(distance_probabilities, lexical_probabilities)
        classification = _classification_rows(target_modelable, probabilities, distances, topic_lookup)
        if len(target_all) > len(target_modelable):
            classification = pd.concat(
                [classification, _unmodelable_rows(target_all[~target_all["_is_modelable"]], topic_lookup)],
                ignore_index=True,
            )

    dataset_tai = _dataset_transfer_scores(source_embedding, target_embedding, target_modelable)
    classification["TAI"] = classification["dataset_id"].map(dataset_tai).fillna(0.0)
    classification = _finalize_states(classification)
    classification = classification.sort_values(["dataset_id", "state_rank", "ARS", "file_id"], ascending=[True, True, False, True])
    classification = classification.drop(columns=["state_rank"], errors="ignore").reset_index(drop=True)

    dataset_evaluation = _dataset_evaluation(classification, dataset_tai)
    topic_distribution = _topic_distribution(classification)
    boundary_samples = _boundary_samples(classification)
    metrics = {
        "model": "problem2_graph_transfer_ars_mii_mmd",
        "source_document_count": int(len(history)),
        "target_document_count": int(len(target_all)),
        "target_modelable_count": int(len(target_modelable)),
        "target_unclassifiable_count": int(len(target_all) - len(target_modelable)),
        "clusters": int(n_clusters),
        "term_count": int(len(terms)),
        "embedding_dim": int(embedding_dim),
        "alpha_ars": ALPHA_ARS,
        "meta_feature_weight": META_FEATURE_WEIGHT,
        "lexical_probability_weight": LEXICAL_PROBABILITY_WEIGHT,
        "min_model_text_len": MIN_MODEL_TEXT_LEN,
        "min_model_parse_quality": MIN_MODEL_PARSE_QUALITY,
        "dataset_tai": dataset_tai,
        **graph_stats,
    }

    _write_outputs(output_dir, classification, dataset_evaluation, topic_distribution, boundary_samples, topic_summary, metrics)
    _write_plot_data(output_dir, classification, topic_distribution)
    _write_charts(output_dir, classification, topic_distribution)
    return Problem2TransferResult(classification, dataset_evaluation, topic_distribution, boundary_samples, metrics, topic_summary)


def _target_frame(document_index: pd.DataFrame) -> pd.DataFrame:
    frame = document_index[document_index["dataset_id"].isin(["dataset2", "dataset3"])].copy()
    return frame.reset_index(drop=True)


def _is_modelable(row: pd.Series) -> bool:
    method = "" if pd.isna(row.get("parse_method")) else str(row.get("parse_method"))
    if method.startswith("image_sidecar") or method in {"metadata_only", "scanned_pdf_ocr_pending"}:
        return False
    text = "" if pd.isna(row.get("_modeling_text")) else str(row.get("_modeling_text"))
    quality = float(pd.to_numeric(pd.Series([row.get("parse_quality", 0)]), errors="coerce").fillna(0).iloc[0])
    return len(text) >= MIN_MODEL_TEXT_LEN and quality >= MIN_MODEL_PARSE_QUALITY


def _fit_numeric_features(frame: pd.DataFrame) -> tuple[StandardScaler, sparse.csr_matrix]:
    numeric = _numeric_frame(frame)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(numeric)
    return scaler, sparse.csr_matrix(scaled)


def _transform_numeric_features(frame: pd.DataFrame, scaler: StandardScaler) -> sparse.csr_matrix:
    return sparse.csr_matrix(scaler.transform(_numeric_frame(frame)))


def _numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = pd.DataFrame(index=frame.index)
    for column in STRUCTURE_COLUMNS:
        numeric[column] = pd.to_numeric(frame.get(column, 0), errors="coerce").fillna(0.0)
    numeric["log_text_length"] = np.log1p(pd.to_numeric(frame.get("text_length", 0), errors="coerce").fillna(0.0))
    numeric["log_file_size"] = np.log1p(pd.to_numeric(frame.get("file_size_kb", 0), errors="coerce").fillna(0.0))
    for column in BUSINESS_COLUMNS:
        numeric[column] = pd.to_numeric(frame.get(column, 0), errors="coerce").fillna(0.0)
    return numeric


def _distance_probabilities(distances: np.ndarray, source_nearest_distances: np.ndarray) -> np.ndarray:
    scale = float(np.median(source_nearest_distances))
    scale = max(scale * 0.12, 1e-6)
    logits = -distances / scale
    logits -= logits.max(axis=1, keepdims=True)
    exp_logits = np.exp(logits)
    return exp_logits / exp_logits.sum(axis=1, keepdims=True)


def _lexical_topic_probabilities(texts: list[str], topic_summary: pd.DataFrame, n_clusters: int) -> np.ndarray:
    topic_terms = _topic_lexical_terms(topic_summary)
    probabilities = np.zeros((len(texts), n_clusters), dtype=float)
    for row_index, text in enumerate(texts):
        scores = np.zeros(n_clusters, dtype=float)
        for topic_id, terms in topic_terms.items():
            score = 0.0
            for term, weight in terms:
                count = text.count(term)
                if count:
                    score += count * weight
            scores[int(topic_id)] = score
        if scores.sum() <= 0:
            probabilities[row_index, :] = 1.0 / n_clusters
            continue
        # Smooth slightly so lexical evidence calibrates rather than hard-overrides
        # the graph-space distance probability.
        scores = np.log1p(scores)
        scores += 0.03
        probabilities[row_index, :] = scores / scores.sum()
    return probabilities


def _topic_lexical_terms(topic_summary: pd.DataFrame) -> dict[int, list[tuple[str, float]]]:
    topic_terms: dict[int, list[tuple[str, float]]] = {}
    for _, row in topic_summary.iterrows():
        topic_id = int(row["topic_id"])
        topic_name = str(row.get("topic_name", ""))
        terms: dict[str, float] = {}
        for term in str(row.get("ctfidf_terms", "")).split(" / "):
            term = term.strip()
            if _is_usable_lexical_term(term):
                terms[term] = max(terms.get(term, 0.0), 1.0 + min(len(term), 4) * 0.15)
        for anchor in TOPIC_ANCHORS.get(topic_name, []):
            if _is_usable_lexical_term(anchor, allow_generic=True):
                terms[anchor] = max(terms.get(anchor, 0.0), 1.60 + min(len(anchor), 4) * 0.20)
        topic_terms[topic_id] = sorted(terms.items(), key=lambda item: (-item[1], item[0]))
    return topic_terms


def _is_usable_lexical_term(term: str, allow_generic: bool = False) -> bool:
    if not term or len(term) < 2:
        return False
    if any(noise in term for noise in NOISE_TERMS):
        return False
    if not allow_generic and term in GENERIC_LEXICAL_TERMS:
        return False
    if len(set(term)) == 1:
        return False
    return True


def _blend_probabilities(distance_probabilities: np.ndarray, lexical_probabilities: np.ndarray) -> np.ndarray:
    weight = LEXICAL_PROBABILITY_WEIGHT
    blended = (1.0 - weight) * distance_probabilities + weight * lexical_probabilities
    blended_sum = blended.sum(axis=1, keepdims=True)
    blended_sum[blended_sum == 0] = 1.0
    return blended / blended_sum


def _classification_rows(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    distances: np.ndarray,
    topic_lookup: dict[int, dict[str, object]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    top_order = np.argsort(-probabilities, axis=1)
    for row_pos, (_, record) in enumerate(frame.iterrows()):
        top1 = int(top_order[row_pos, 0])
        top2 = int(top_order[row_pos, 1]) if probabilities.shape[1] > 1 else top1
        p1 = float(probabilities[row_pos, top1])
        p2 = float(probabilities[row_pos, top2]) if top2 != top1 else 0.0
        margin = p1 - p2
        relative_margin = margin / max(p1, 1e-9)
        ars = ALPHA_ARS * p1 + (1.0 - ALPHA_ARS) * relative_margin
        entropy = _normalized_entropy(probabilities[row_pos])
        explanation_terms, mii = _explanation_terms(record.get("_modeling_text", ""), topic_lookup.get(top1, {}))
        rows.append(
            {
                "file_id": record.get("file_id"),
                "original_id": record.get("original_id"),
                "dataset_id": record.get("dataset_id"),
                "file_name": record.get("file_name"),
                "file_type": record.get("file_type"),
                "parse_method": record.get("parse_method"),
                "parse_quality": _round(record.get("parse_quality")),
                "text_length": int(pd.to_numeric(pd.Series([record.get("text_length", 0)]), errors="coerce").fillna(0).iloc[0]),
                "top1_topic_id": top1,
                "top1_topic_name": topic_lookup.get(top1, {}).get("topic_name", f"Topic {top1}"),
                "top1_probability": round(p1, 6),
                "top2_topic_id": top2,
                "top2_topic_name": topic_lookup.get(top2, {}).get("topic_name", f"Topic {top2}"),
                "top2_probability": round(p2, 6),
                "probability_margin": round(margin, 6),
                "relative_margin": round(relative_margin, 6),
                "ARS": round(float(ars), 6),
                "entropy": round(entropy, 6),
                "MII": round(mii, 6),
                "nearest_center_distance": round(float(distances[row_pos, top1]), 6),
                "explanation_terms": explanation_terms,
                "state": "pending",
                "state_reason": "",
            }
        )
    return pd.DataFrame(rows)


def _unmodelable_rows(frame: pd.DataFrame, topic_lookup: dict[int, dict[str, object]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, record in frame.iterrows():
        reason = _unmodelable_reason(record)
        rows.append(
            {
                "file_id": record.get("file_id"),
                "original_id": record.get("original_id"),
                "dataset_id": record.get("dataset_id"),
                "file_name": record.get("file_name"),
                "file_type": record.get("file_type"),
                "parse_method": record.get("parse_method"),
                "parse_quality": _round(record.get("parse_quality")),
                "text_length": int(pd.to_numeric(pd.Series([record.get("text_length", 0)]), errors="coerce").fillna(0).iloc[0]),
                "top1_topic_id": np.nan,
                "top1_topic_name": "",
                "top1_probability": 0.0,
                "top2_topic_id": np.nan,
                "top2_topic_name": "",
                "top2_probability": 0.0,
                "probability_margin": 0.0,
                "relative_margin": 0.0,
                "ARS": 0.0,
                "entropy": 1.0,
                "MII": 0.0,
                "nearest_center_distance": np.nan,
                "explanation_terms": "",
                "state": "C_unknown_expert_review",
                "state_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def _unmodelable_reason(row: pd.Series) -> str:
    method = "" if pd.isna(row.get("parse_method")) else str(row.get("parse_method"))
    text = "" if pd.isna(row.get("_modeling_text")) else str(row.get("_modeling_text"))
    quality = float(pd.to_numeric(pd.Series([row.get("parse_quality", 0)]), errors="coerce").fillna(0).iloc[0])
    if method.startswith("image_sidecar"):
        return "图片侧车元数据，不作为独立主题文本"
    if method == "metadata_only":
        return "仅有元数据，正文缺失"
    if method == "scanned_pdf_ocr_pending":
        return "扫描 PDF 待转图 OCR"
    if len(text) < MIN_MODEL_TEXT_LEN:
        return "有效中文语义文本过短"
    if quality < MIN_MODEL_PARSE_QUALITY:
        return "解析质量低于迁移分类阈值"
    return "无法形成稳定迁移表征"


def _normalized_entropy(probability: np.ndarray) -> float:
    p = np.clip(probability.astype(float), 1e-12, 1.0)
    entropy = -float(np.sum(p * np.log2(p)))
    return entropy / math.log2(len(p)) if len(p) > 1 else 0.0


def _explanation_terms(text: object, topic_info: dict[str, object], top_n: int = 8) -> tuple[str, float]:
    clean_text = "" if pd.isna(text) else str(text)
    terms = str(topic_info.get("ctfidf_terms", "")).split(" / ")
    terms = [term for term in terms if term and not any(noise in term for noise in NOISE_TERMS)]
    scored = []
    for term in terms:
        count = clean_text.count(term)
        if count > 0:
            scored.append((term, count * max(1, len(term))))
    if not scored:
        return "", 0.0
    scored = sorted(scored, key=lambda item: (-item[1], item[0]))[:top_n]
    weights = np.array([score for _, score in scored], dtype=float)
    probs = weights / weights.sum()
    if len(probs) == 1:
        mii = 1.0
    else:
        mii = 1.0 - (-float(np.sum(probs * np.log2(probs))) / math.log2(len(probs)))
    return " / ".join(f"{term}:{int(score)}" for term, score in scored), float(np.clip(mii, 0.0, 1.0))


def _dataset_transfer_scores(source_embedding: np.ndarray, target_embedding: np.ndarray, target_frame: pd.DataFrame) -> dict[str, float]:
    scores: dict[str, float] = {}
    if target_frame.empty or target_embedding.size == 0:
        return {"dataset2": 0.0, "dataset3": 0.0}
    for dataset_id in ["dataset2", "dataset3"]:
        positions = np.flatnonzero(target_frame["dataset_id"].to_numpy() == dataset_id)
        if len(positions) == 0:
            scores[dataset_id] = 0.0
            continue
        target_subset = target_embedding[positions]
        mmd2 = _mmd_rbf(source_embedding, target_subset, max_samples=900)
        scores[dataset_id] = round(float(math.exp(-mmd2)), 6)
    return scores


def _mmd_rbf(source: np.ndarray, target: np.ndarray, max_samples: int = 900) -> float:
    rng = np.random.default_rng(RANDOM_STATE)
    source_sample = _sample_rows(source, max_samples, rng)
    target_sample = _sample_rows(target, max_samples, rng)
    combined = np.vstack([source_sample, target_sample])
    if len(combined) <= 1:
        return 0.0
    gamma = 1.0 / max(1, combined.shape[1])
    xx = _rbf_kernel_mean(source_sample, source_sample, gamma)
    yy = _rbf_kernel_mean(target_sample, target_sample, gamma)
    xy = _rbf_kernel_mean(source_sample, target_sample, gamma)
    return max(0.0, float(xx + yy - 2.0 * xy))


def _sample_rows(matrix: np.ndarray, max_samples: int, rng: np.random.Generator) -> np.ndarray:
    if len(matrix) <= max_samples:
        return matrix
    positions = rng.choice(len(matrix), size=max_samples, replace=False)
    return matrix[positions]


def _rbf_kernel_mean(left: np.ndarray, right: np.ndarray, gamma: float) -> float:
    distances = pairwise_distances(left, right, metric="sqeuclidean")
    return float(np.exp(-gamma * distances).mean())


def _finalize_states(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["state_rank"] = 3
    modelable = result["state"] == "pending"
    if modelable.any():
        p1 = result.loc[modelable, "top1_probability"].astype(float)
        ars = result.loc[modelable, "ARS"].astype(float)
        margin = result.loc[modelable, "relative_margin"].astype(float)
        entropy = result.loc[modelable, "entropy"].astype(float)
        mii = result.loc[modelable, "MII"].astype(float)

        clear = (
            (p1 >= 0.34)
            & (ars >= 0.36)
            & (margin >= 0.18)
            & (entropy <= 0.88)
            & (mii >= 0.03)
        )
        probability_margin = result.loc[modelable, "probability_margin"].astype(float)
        overlap = ((margin < 0.10) | ((p1 < 0.26) & (probability_margin < 0.03))) & ~clear
        unknown = ((p1 < 0.18) | (entropy > 0.92) | (result.loc[modelable, "parse_quality"].astype(float) < 0.35)) & ~clear

        modelable_index = result.index[modelable]
        result.loc[modelable_index[clear.to_numpy()], "state"] = "A_clear_auto_archive"
        result.loc[modelable_index[clear.to_numpy()], "state_reason"] = "最高概率、ARS、边际差和主题词解释均达到自动归档条件"
        result.loc[modelable_index[clear.to_numpy()], "state_rank"] = 0

        overlap_only = overlap & ~unknown
        result.loc[modelable_index[overlap_only.to_numpy()], "state"] = "B_overlap_manual_review"
        result.loc[modelable_index[overlap_only.to_numpy()], "state_reason"] = "前两类概率接近，存在多类别重叠"
        result.loc[modelable_index[overlap_only.to_numpy()], "state_rank"] = 1

        unknown_index = modelable_index[unknown.to_numpy()]
        result.loc[unknown_index, "state"] = "C_unknown_expert_review"
        result.loc[unknown_index, "state_reason"] = "概率分布分散、解析质量偏低或疑似分布外样本"
        result.loc[unknown_index, "state_rank"] = 2

        remaining = result["state"] == "pending"
        result.loc[remaining, "state"] = "A_assisted_archive"
        result.loc[remaining, "state_reason"] = "可归档但建议保留系统解释与抽检"
        result.loc[remaining, "state_rank"] = 0

    unmodelable = result["state"] == "C_unknown_expert_review"
    result.loc[unmodelable & result["state_rank"].eq(3), "state_rank"] = 2
    return result


def _dataset_evaluation(classification: pd.DataFrame, dataset_tai: dict[str, float]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for dataset_id, group in classification.groupby("dataset_id"):
        rows.append(
            {
                "dataset_id": dataset_id,
                "record_count": int(len(group)),
                "auto_archive_count": int(group["state"].isin(["A_clear_auto_archive", "A_assisted_archive"]).sum()),
                "clear_auto_archive_count": int((group["state"] == "A_clear_auto_archive").sum()),
                "overlap_review_count": int((group["state"] == "B_overlap_manual_review").sum()),
                "unknown_expert_review_count": int((group["state"] == "C_unknown_expert_review").sum()),
                "avg_top1_probability": round(float(group["top1_probability"].mean()), 6),
                "avg_ARS": round(float(group["ARS"].mean()), 6),
                "avg_MII": round(float(group["MII"].mean()), 6),
                "avg_entropy": round(float(group["entropy"].mean()), 6),
                "TAI": dataset_tai.get(dataset_id, 0.0),
            }
        )
    return pd.DataFrame(rows).sort_values("dataset_id")


def _topic_distribution(classification: pd.DataFrame) -> pd.DataFrame:
    modelable = classification[classification["top1_topic_name"].fillna("") != ""].copy()
    if modelable.empty:
        return pd.DataFrame()
    grouped = (
        modelable.groupby(["dataset_id", "top1_topic_id", "top1_topic_name", "state"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    totals = grouped.groupby("dataset_id")["count"].transform("sum")
    grouped["dataset_share"] = (grouped["count"] / totals).round(6)
    return grouped.sort_values(["dataset_id", "count"], ascending=[True, False])


def _boundary_samples(classification: pd.DataFrame, limit_per_state: int = 30) -> pd.DataFrame:
    focus = classification[classification["state"].isin(["B_overlap_manual_review", "C_unknown_expert_review"])].copy()
    if focus.empty:
        return focus
    focus["_rank_score"] = focus["entropy"].astype(float) - focus["probability_margin"].astype(float)
    return (
        focus.sort_values(["state", "_rank_score", "ARS"], ascending=[True, False, True])
        .groupby("state", as_index=False)
        .head(limit_per_state)
        .drop(columns=["_rank_score"])
    )


def _write_outputs(
    output_dir: Path,
    classification: pd.DataFrame,
    dataset_evaluation: pd.DataFrame,
    topic_distribution: pd.DataFrame,
    boundary_samples: pd.DataFrame,
    topic_summary: pd.DataFrame,
    metrics: dict[str, object],
) -> None:
    classification.to_csv(output_dir / "problem2_transfer_classification.csv", index=False, encoding="utf-8-sig")
    dataset_evaluation.to_csv(output_dir / "problem2_dataset_evaluation.csv", index=False, encoding="utf-8-sig")
    topic_distribution.to_csv(output_dir / "problem2_topic_distribution.csv", index=False, encoding="utf-8-sig")
    boundary_samples.to_csv(output_dir / "problem2_boundary_samples.csv", index=False, encoding="utf-8-sig")
    topic_summary.to_csv(output_dir / "problem2_source_topic_summary.csv", index=False, encoding="utf-8-sig")
    (output_dir / "problem2_transfer_metrics.json").write_text(_json_dumps(metrics), encoding="utf-8")
    (output_dir / "problem2_transfer_report.md").write_text(
        _markdown_report(dataset_evaluation, topic_distribution, boundary_samples, topic_summary, metrics),
        encoding="utf-8",
    )


def _write_charts(output_dir: Path, classification: pd.DataFrame, topic_distribution: pd.DataFrame) -> None:
    _setup_plot_fonts()
    plt.style.use("seaborn-v0_8-whitegrid")

    if not topic_distribution.empty:
        chart_distribution = topic_distribution.copy()
        chart_distribution["topic_label"] = chart_distribution.apply(_ascii_topic_label, axis=1)
        pivot = chart_distribution.pivot_table(
            index="topic_label", columns="dataset_id", values="count", aggfunc="sum", fill_value=0
        )
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
        fig_height = max(4.8, 0.42 * len(pivot))
        fig, ax = plt.subplots(figsize=(9.5, fig_height))
        pivot.plot.barh(ax=ax, color=["#4C78A8", "#F58518"], width=0.76)
        ax.set_xlabel("Record count")
        ax.set_ylabel("")
        ax.set_title("Problem 2 Topic Assignment Distribution")
        ax.legend(title="Dataset", loc="lower right")
        fig.tight_layout()
        fig.savefig(output_dir / "problem2_topic_distribution.png", dpi=220)
        plt.close(fig)

    state_pivot = classification.pivot_table(index="dataset_id", columns="state", values="file_id", aggfunc="count", fill_value=0)
    if not state_pivot.empty:
        order = ["A_clear_auto_archive", "A_assisted_archive", "B_overlap_manual_review", "C_unknown_expert_review"]
        state_pivot = state_pivot.reindex(columns=[column for column in order if column in state_pivot.columns], fill_value=0)
        state_pivot = state_pivot.rename(
            columns={
                "A_clear_auto_archive": "Clear auto",
                "A_assisted_archive": "Assisted archive",
                "B_overlap_manual_review": "Overlap review",
                "C_unknown_expert_review": "Unknown review",
            }
        )
        fig, ax = plt.subplots(figsize=(10.2, 4.8))
        state_pivot.plot.bar(stacked=True, ax=ax, color=["#54A24B", "#9ACD68", "#ECA82C", "#E45756"], width=0.62, rot=0)
        ax.set_xlabel("")
        ax.set_ylabel("Record count")
        ax.set_title("Archive / Review State Distribution")
        ax.legend(title="State", fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
        fig.tight_layout()
        fig.savefig(output_dir / "problem2_state_distribution.png", dpi=220)
        plt.close(fig)

    modelable = classification[classification["top1_probability"].astype(float) > 0].copy()
    if not modelable.empty:
        fig, ax = plt.subplots(figsize=(8.8, 5.4))
        colors = {
            "A_clear_auto_archive": "#54A24B",
            "A_assisted_archive": "#72B7B2",
            "B_overlap_manual_review": "#ECA82C",
            "C_unknown_expert_review": "#E45756",
        }
        for state, group in modelable.groupby("state"):
            ax.scatter(
                group["ARS"].astype(float),
                group["MII"].astype(float),
                s=18,
                alpha=0.72,
                label=state,
                color=colors.get(state, "#888888"),
                linewidths=0,
            )
        ax.set_xlabel("ARS")
        ax.set_ylabel("MII")
        ax.set_title("Reasonableness vs Interpretability")
        ax.legend(fontsize=8, loc="upper right")
        fig.tight_layout()
        fig.savefig(output_dir / "problem2_ars_mii_scatter.png", dpi=220)
        plt.close(fig)


def _write_plot_data(output_dir: Path, classification: pd.DataFrame, topic_distribution: pd.DataFrame) -> None:
    """Write bilingual CSV sidecars for every PNG chart."""

    topic_plot_data = _topic_plot_data(topic_distribution)
    topic_plot_data.to_csv(output_dir / "problem2_topic_distribution_plot_data.csv", index=False, encoding="utf-8-sig")
    topic_plot_data.to_csv(output_dir / "problem2_topic_distribution.png.csv", index=False, encoding="utf-8-sig")

    state_plot_data = _state_plot_data(classification)
    state_plot_data.to_csv(output_dir / "problem2_state_distribution_plot_data.csv", index=False, encoding="utf-8-sig")
    state_plot_data.to_csv(output_dir / "problem2_state_distribution.png.csv", index=False, encoding="utf-8-sig")

    scatter_plot_data = _scatter_plot_data(classification)
    scatter_plot_data.to_csv(output_dir / "problem2_ars_mii_scatter_plot_data.csv", index=False, encoding="utf-8-sig")
    scatter_plot_data.to_csv(output_dir / "problem2_ars_mii_scatter.png.csv", index=False, encoding="utf-8-sig")


def _topic_plot_data(topic_distribution: pd.DataFrame) -> pd.DataFrame:
    if topic_distribution.empty:
        return pd.DataFrame(
            columns=[
                "dataset_id",
                "top1_topic_id",
                "topic_name_zh",
                "topic_name_en",
                "topic_label_en",
                "state",
                "state_zh",
                "state_en",
                "count",
                "dataset_share",
            ]
        )
    frame = topic_distribution.copy()
    frame["topic_name_zh"] = frame["top1_topic_name"]
    frame["topic_name_en"] = frame["top1_topic_name"].map(_topic_name_en)
    frame["topic_label_en"] = frame.apply(_ascii_topic_label, axis=1)
    frame["state_zh"] = frame["state"].map(_state_name_zh)
    frame["state_en"] = frame["state"].map(_state_name_en)
    return frame[
        [
            "dataset_id",
            "top1_topic_id",
            "topic_name_zh",
            "topic_name_en",
            "topic_label_en",
            "state",
            "state_zh",
            "state_en",
            "count",
            "dataset_share",
        ]
    ].sort_values(["dataset_id", "count"], ascending=[True, False])


def _state_plot_data(classification: pd.DataFrame) -> pd.DataFrame:
    grouped = classification.groupby(["dataset_id", "state"], dropna=False).size().reset_index(name="count")
    totals = grouped.groupby("dataset_id")["count"].transform("sum")
    grouped["dataset_share"] = (grouped["count"] / totals).round(6)
    grouped["state_zh"] = grouped["state"].map(_state_name_zh)
    grouped["state_en"] = grouped["state"].map(_state_name_en)
    order = {
        "A_clear_auto_archive": 0,
        "A_assisted_archive": 1,
        "B_overlap_manual_review": 2,
        "C_unknown_expert_review": 3,
    }
    grouped["state_order"] = grouped["state"].map(order).fillna(99).astype(int)
    return grouped[
        ["dataset_id", "state", "state_zh", "state_en", "state_order", "count", "dataset_share"]
    ].sort_values(["dataset_id", "state_order"])


def _scatter_plot_data(classification: pd.DataFrame) -> pd.DataFrame:
    frame = classification[classification["top1_probability"].astype(float) > 0].copy()
    frame["topic_name_zh"] = frame["top1_topic_name"]
    frame["topic_name_en"] = frame["top1_topic_name"].map(_topic_name_en)
    frame["state_zh"] = frame["state"].map(_state_name_zh)
    frame["state_en"] = frame["state"].map(_state_name_en)
    columns = [
        "file_id",
        "dataset_id",
        "file_name",
        "top1_topic_id",
        "topic_name_zh",
        "topic_name_en",
        "state",
        "state_zh",
        "state_en",
        "top1_probability",
        "top2_probability",
        "probability_margin",
        "relative_margin",
        "ARS",
        "MII",
        "entropy",
        "TAI",
        "parse_quality",
        "text_length",
    ]
    return frame[[column for column in columns if column in frame.columns]].sort_values(["dataset_id", "ARS", "MII"])


def _setup_plot_fonts() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "Arial Unicode MS"]:
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def _ascii_topic_label(row: pd.Series) -> str:
    topic_id = row.get("top1_topic_id", "")
    try:
        topic_id_text = str(int(float(topic_id)))
    except (TypeError, ValueError):
        topic_id_text = str(topic_id)
    topic_name = "" if pd.isna(row.get("top1_topic_name")) else str(row.get("top1_topic_name"))
    return f"T{topic_id_text} {_topic_name_en(topic_name)}"


def _topic_name_en(topic_name: object) -> str:
    names = {
        "项目案件信息类": "Project Case",
        "资金财政统计类": "Finance",
        "生态环境治理类": "Environment",
        "文旅活动评价类": "Culture Tourism",
        "养老服务机构类": "Elderly Service",
        "教育教学管理类": "Education",
        "社会民生指标类": "Social Indicators",
        "制造业产业统计类": "Manufacturing",
        "居民收入统计类": "Income",
        "城市月度指标类": "City Monthly",
    }
    text = "" if pd.isna(topic_name) else str(topic_name)
    return names.get(text, "Topic")


def _state_name_zh(state: object) -> str:
    names = {
        "A_clear_auto_archive": "清晰自动归档",
        "A_assisted_archive": "辅助归档/抽检",
        "B_overlap_manual_review": "多类别重叠复核",
        "C_unknown_expert_review": "未知专家研判",
    }
    text = "" if pd.isna(state) else str(state)
    return names.get(text, text)


def _state_name_en(state: object) -> str:
    names = {
        "A_clear_auto_archive": "Clear auto archive",
        "A_assisted_archive": "Assisted archive",
        "B_overlap_manual_review": "Overlap manual review",
        "C_unknown_expert_review": "Unknown expert review",
    }
    text = "" if pd.isna(state) else str(state)
    return names.get(text, text)


def _markdown_report(
    dataset_evaluation: pd.DataFrame,
    topic_distribution: pd.DataFrame,
    boundary_samples: pd.DataFrame,
    topic_summary: pd.DataFrame,
    metrics: dict[str, object],
) -> str:
    lines = [
        "# 问题二迁移分类结果报告",
        "",
        "## 模型概览",
        "",
        f"- 模型：`{metrics['model']}`",
        f"- 历史源域文件数：`{metrics['source_document_count']}`",
        f"- 新流入文件数：`{metrics['target_document_count']}`",
        f"- 可迁移分类文件数：`{metrics['target_modelable_count']}`",
        f"- 不可直接分类文件数：`{metrics['target_unclassifiable_count']}`",
        f"- 类别数：`{metrics['clusters']}`；图词项数：`{metrics['term_count']}`；嵌入维度：`{metrics['embedding_dim']}`",
        "",
        "## 数据集级评价",
        "",
        _frame_to_markdown(dataset_evaluation),
        "",
        "## 源域主题体系",
        "",
        _frame_to_markdown(topic_summary[["topic_id", "history_count", "topic_name", "ctfidf_terms", "topic_explanation"]]),
        "",
        "## 新数据主题分布 Top 20",
        "",
        _frame_to_markdown(topic_distribution.head(20)),
        "",
        "## 边界/未知样本示例",
        "",
        _frame_to_markdown(
            boundary_samples[
                [
                    "file_id",
                    "dataset_id",
                    "file_name",
                    "state",
                    "top1_topic_name",
                    "top1_probability",
                    "top2_topic_name",
                    "top2_probability",
                    "ARS",
                    "MII",
                    "state_reason",
                ]
            ].head(30)
            if not boundary_samples.empty
            else boundary_samples
        ),
        "",
        "## 输出文件说明",
        "",
        "- `problem2_transfer_classification.csv`：每个新文件的类别、概率、ARS、MII、TAI、状态和解释词。",
        "- `problem2_dataset_evaluation.csv`：数据集 2/3 的分类效果、合理性、可解释性、迁移适用性汇总。",
        "- `problem2_topic_distribution.csv`：数据集-主题-状态三维分布。",
        "- `problem2_boundary_samples.csv`：多类别重叠与未知样本复核清单。",
        "- `problem2_topic_distribution.png`、`problem2_state_distribution.png`、`problem2_ars_mii_scatter.png`：论文可用可视化。",
        "- `*_plot_data.csv` 与 `*.png.csv`：每张 PNG 对应的中英文作图数据，便于论文手重新绘图。",
    ]
    return "\n".join(lines)


def _frame_to_markdown(frame: pd.DataFrame, max_col_width: int = 72) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in columns:
            text = "" if pd.isna(row[column]) else str(row[column])
            text = re.sub(r"\s+", " ", text).replace("|", "/")
            if len(text) > max_col_width:
                text = text[: max_col_width - 3] + "..."
            cells.append(text)
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows])


def _json_dumps(value: dict[str, object]) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2)


def _round(value: object, digits: int = 6) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").fillna(0.0).iloc[0]
    return round(float(parsed), digits)
