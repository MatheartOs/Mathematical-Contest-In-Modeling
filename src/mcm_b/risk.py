"""Human-review priority model for Problem 3."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_WEIGHTS = {
    "urgency": 0.35,
    "misclassification_risk": 0.35,
    "review_necessity": 0.30,
}


def load_resource_scenarios(path: Path) -> pd.DataFrame:
    """Load dataset 4 resource constraints."""

    frame = pd.read_excel(path)
    rename = {
        "场景编号": "scenario_id",
        "每日可用人工工时（小时）": "manual_hours_per_day",
        "自动归档能力上限（份/天）": "auto_archive_capacity_per_day",
        "人工复核能力上限（份/天）": "manual_review_capacity_per_day",
    }
    return frame.rename(columns=rename)


def score_review_priority(
    classified: pd.DataFrame,
    features: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Compute urgency, risk, review need, and final priority for files."""

    weights = weights or DEFAULT_WEIGHTS
    merged = classified.merge(
        features.drop(columns=["text", "metadata", "warnings"], errors="ignore"),
        on=["doc_id", "dataset", "path", "extension"],
        how="left",
    )
    if merged.empty:
        return merged

    merged["urgency_score"] = _normalize(
        merged.get("kw_urgency", 0)
        + 0.7 * merged.get("kw_policy", 0)
        + 0.4 * merged.get("kw_government", 0)
    )
    merged["funding_score"] = _normalize(merged.get("kw_finance", 0))
    merged["misclassification_risk"] = (
        1.0 - merged["classification_confidence"].fillna(0.0)
    ).clip(0, 1)
    merged["ambiguity_score"] = merged["is_ambiguous"].fillna(False).astype(float)
    merged["review_necessity_score"] = (
        0.45 * merged["misclassification_risk"]
        + 0.30 * merged["ambiguity_score"]
        + 0.25 * merged["funding_score"]
    ).clip(0, 1)
    merged["priority_score"] = (
        weights["urgency"] * merged["urgency_score"]
        + weights["misclassification_risk"] * merged["misclassification_risk"]
        + weights["review_necessity"] * merged["review_necessity_score"]
    ).clip(0, 1)
    merged["urgency_level"] = merged["urgency_score"].map(_level)
    merged["risk_level"] = merged["misclassification_risk"].map(_level)
    merged["review_level"] = merged["review_necessity_score"].map(_level)
    merged["needs_manual_review"] = (
        (merged["priority_score"] >= 0.55)
        | (merged["funding_score"] >= 0.55)
        | merged["is_ambiguous"].fillna(False)
    )
    return merged.sort_values("priority_score", ascending=False).reset_index(drop=True)


def allocate_reviews_by_scenario(
    priority_frame: pd.DataFrame,
    scenarios: pd.DataFrame,
    minutes_per_review: int = 18,
) -> dict[str, pd.DataFrame]:
    """Select review queues under each dataset 4 resource scenario."""

    queues: dict[str, pd.DataFrame] = {}
    review_pool = priority_frame[priority_frame["needs_manual_review"]].copy()
    review_pool = review_pool.sort_values("priority_score", ascending=False)
    for _, scenario in scenarios.iterrows():
        hour_limit = int(scenario["manual_hours_per_day"] * 60 // minutes_per_review)
        count_limit = int(scenario["manual_review_capacity_per_day"])
        limit = min(hour_limit, count_limit)
        scenario_id = str(scenario["scenario_id"])
        queues[scenario_id] = review_pool.head(limit).copy()
    return queues


def _normalize(values: pd.Series | int | float) -> pd.Series:
    series = values if isinstance(values, pd.Series) else pd.Series(values)
    series = series.fillna(0).astype(float)
    max_value = series.max()
    if max_value <= 0:
        return series * 0.0
    return (series / max_value).clip(0, 1)


def _level(value: float) -> str:
    if value >= 0.66:
        return "high"
    if value >= 0.33:
        return "medium"
    return "low"
