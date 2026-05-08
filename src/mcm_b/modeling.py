"""Baseline topic discovery and transfer classification models."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import euclidean_distances

from .readers import DocumentRecord


@dataclass
class TopicModelResult:
    """Fitted unsupervised topic model plus interpretable summaries."""

    vectorizer: TfidfVectorizer
    model: KMeans
    assignments: pd.DataFrame
    topic_terms: dict[int, list[str]]
    silhouette: float | None


def choose_cluster_count(texts: list[str], candidates: range = range(4, 13)) -> int:
    """Choose a small KMeans topic count with silhouette on available samples."""

    usable = [text for text in texts if text.strip()]
    if len(usable) < 8:
        return max(2, min(4, len(usable)))

    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), max_features=6000)
    matrix = vectorizer.fit_transform(usable)
    best_k = 6
    best_score = -1.0
    max_k = min(max(candidates), len(usable) - 1)
    for k in candidates:
        if k > max_k:
            continue
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = model.fit_predict(matrix)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(matrix, labels, metric="cosine")
        if score > best_score:
            best_k = k
            best_score = score
    return best_k


def fit_topic_model(records: list[DocumentRecord], n_clusters: int | None = None) -> TopicModelResult:
    """Fit the initial Problem 1 classification system on sampled history data."""

    usable = [record for record in records if (record.text or "").strip()]
    if not usable:
        raise ValueError("No textual records available for topic modeling.")

    texts = [record.text for record in usable]
    if n_clusters is None:
        n_clusters = choose_cluster_count(texts)
    n_clusters = max(1, min(n_clusters, len(usable)))

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        min_df=2,
        max_df=0.85,
        max_features=10_000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(matrix)
    silhouette = None
    if n_clusters > 1 and len(set(labels)) > 1 and len(usable) > n_clusters:
        silhouette = float(silhouette_score(matrix, labels, metric="cosine"))

    assignments = pd.DataFrame(
        {
            "doc_id": [record.doc_id for record in usable],
            "dataset": [record.dataset for record in usable],
            "path": [record.path for record in usable],
            "extension": [record.extension for record in usable],
            "topic_id": labels,
        }
    )
    terms = _top_terms(vectorizer, model, top_n=12)
    return TopicModelResult(
        vectorizer=vectorizer,
        model=model,
        assignments=assignments,
        topic_terms=terms,
        silhouette=silhouette,
    )


def classify_records(result: TopicModelResult, records: list[DocumentRecord]) -> pd.DataFrame:
    """Assign new records to discovered topics and estimate ambiguity."""

    rows: list[dict[str, object]] = []
    usable_records = [record for record in records if (record.text or "").strip()]
    if not usable_records:
        return pd.DataFrame()

    matrix = result.vectorizer.transform([record.text for record in usable_records])
    distances = euclidean_distances(matrix, result.model.cluster_centers_)
    labels = np.argmin(distances, axis=1)
    sorted_distances = np.sort(distances, axis=1)
    margins = (
        sorted_distances[:, 1] - sorted_distances[:, 0]
        if distances.shape[1] > 1
        else np.ones(distances.shape[0])
    )
    margin_confidence = margins / (sorted_distances[:, 1] + 1e-9) if distances.shape[1] > 1 else margins
    confidence = _distance_confidence(distances, margin_confidence)

    for index, record in enumerate(usable_records):
        rows.append(
            {
                "doc_id": record.doc_id,
                "dataset": record.dataset,
                "path": record.path,
                "extension": record.extension,
                "predicted_topic_id": int(labels[index]),
                "classification_confidence": round(float(confidence[index]), 6),
                "topic_margin": round(float(margin_confidence[index]), 6),
                "is_ambiguous": bool(confidence[index] < 0.35 or margin_confidence[index] < 0.015),
            }
        )
    return pd.DataFrame(rows)


def save_topic_model(result: TopicModelResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "vectorizer": result.vectorizer,
            "model": result.model,
            "topic_terms": result.topic_terms,
            "silhouette": result.silhouette,
        },
        path,
    )


def _top_terms(vectorizer: TfidfVectorizer, model: KMeans, top_n: int) -> dict[int, list[str]]:
    feature_names = np.array(vectorizer.get_feature_names_out())
    topic_terms: dict[int, list[str]] = {}
    for topic_id, center in enumerate(model.cluster_centers_):
        top_indices = np.argsort(center)[::-1][:top_n]
        topic_terms[topic_id] = [str(term) for term in feature_names[top_indices]]
    return topic_terms


def _distance_confidence(distances: np.ndarray, margin_confidence: np.ndarray) -> np.ndarray:
    if distances.shape[1] == 1:
        return np.ones(distances.shape[0])
    confidence = np.sqrt(np.clip(margin_confidence / 0.12, 0.0, 1.0))
    return np.array([0.0 if math.isnan(value) else value for value in confidence])
