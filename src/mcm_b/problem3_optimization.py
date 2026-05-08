"""Problem 3 human-in-the-loop review optimization.

The model consumes Problem 2 transfer results and turns them into a resource
aware governance plan: urgency/risk/review-necessity levels, manual-review
decisions, priority order, and S1/S2/S3 scenario comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SUBJECTIVE_WEIGHTS = {
    "urgency": 0.34,
    "misclassification_risk": 0.38,
    "review_necessity": 0.28,
}

SPECIAL_BOOST_MU = 0.18
HOURLY_COST_INDEX = 1.0
ENTROPY_BLEND = 0.35

URGENT_TERMS = (
    "截止",
    "请于",
    "前完成",
    "报名",
    "面试",
    "公示",
    "递补",
    "通知",
    "紧急",
    "限期",
    "反馈",
    "整改",
    "考试",
    "会议",
    "时间",
)

FUND_TERMS = (
    "资金",
    "经费",
    "财政",
    "预算",
    "补助",
    "扶持",
    "投资",
    "金额",
    "亿元",
    "万元",
    "价格",
    "利润",
    "收入",
    "支出",
    "金融",
)

UNCLEAR_STATES = {"B_overlap_manual_review", "C_unknown_expert_review"}


@dataclass
class Problem3Result:
    priority: pd.DataFrame
    level_summary: pd.DataFrame
    scenario_comparison: pd.DataFrame
    scenario_queues: dict[str, pd.DataFrame]
    metrics: dict[str, object]


def run_problem3_optimization(
    classification: pd.DataFrame,
    document_index: pd.DataFrame,
    scenarios: pd.DataFrame,
    output_dir: Path,
) -> Problem3Result:
    """Build risk levels and optimize review queues for resource scenarios."""

    output_dir.mkdir(parents=True, exist_ok=True)
    enriched = _merge_inputs(classification, document_index)
    scored, weights = _score_priority(enriched)
    level_summary = _level_summary(scored)
    scenario_queues, scenario_auto, scenario_comparison = _allocate_scenarios(scored, scenarios)

    metrics = {
        "model": "problem3_entropy_ahp_priority_resource_optimization",
        "record_count": int(len(scored)),
        "objective_entropy_weights": weights["objective"],
        "subjective_weights": weights["subjective"],
        "combined_weights": weights["combined"],
        "special_boost_mu": SPECIAL_BOOST_MU,
        "entropy_blend": ENTROPY_BLEND,
        "hourly_cost_index": HOURLY_COST_INDEX,
        "scenario_count": int(len(scenario_comparison)),
    }
    _write_outputs(output_dir, scored, level_summary, scenario_comparison, scenario_queues, scenario_auto, metrics)
    _write_plot_data(output_dir, scored, level_summary, scenario_comparison, scenario_queues)
    _write_charts(output_dir, scored, level_summary, scenario_comparison, scenario_queues)
    return Problem3Result(scored, level_summary, scenario_comparison, scenario_queues, metrics)


def _merge_inputs(classification: pd.DataFrame, document_index: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "file_id",
        "clean_text",
        "business_keywords",
        "date_list",
        "deadline",
        "has_deadline",
        "has_money",
        "has_urgent",
        "has_contract",
        "has_project",
        "has_notice",
        "has_meeting",
        "parse_quality",
        "missing_rate",
        "ocr_confidence",
        "file_size_kb",
        "table_count",
        "image_count",
        "page_count",
    ]
    available = [column for column in keep_cols if column in document_index.columns]
    merged = classification.merge(document_index[available], on="file_id", how="left", suffixes=("", "_idx"))
    for column in ("parse_quality", "text_length"):
        idx_column = f"{column}_idx"
        if idx_column in merged:
            merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(
                pd.to_numeric(merged[idx_column], errors="coerce")
            )
            merged = merged.drop(columns=[idx_column])
    return merged


def _score_priority(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    result = frame.copy()
    if "top1_topic_name" in result.columns:
        result["top1_topic_name"] = result["top1_topic_name"].fillna("").astype(str).replace("", "未明确主题")
    if "top1_topic_id" in result.columns:
        result["top1_topic_id"] = pd.to_numeric(result["top1_topic_id"], errors="coerce").fillna(-1).astype(int)
    text = result.get("clean_text", pd.Series("", index=result.index)).fillna("").astype(str)
    keywords = result.get("business_keywords", pd.Series("", index=result.index)).fillna("").astype(str)
    joined_text = text + " " + keywords

    urgent_hits = joined_text.map(lambda value: _term_hits(value, URGENT_TERMS))
    fund_hits = joined_text.map(lambda value: _term_hits(value, FUND_TERMS))
    has_deadline = _num(result.get("has_deadline", 0))
    has_urgent = _num(result.get("has_urgent", 0))
    has_money = _num(result.get("has_money", 0))
    has_contract = _num(result.get("has_contract", 0))
    has_project = _num(result.get("has_project", 0))

    result["timeliness_signal"] = _clip01(
        0.40 * _norm(urgent_hits)
        + 0.25 * has_deadline
        + 0.20 * has_urgent
        + 0.15 * _recency_signal(result.get("date_list", ""))
    )
    result["funding_signal"] = _clip01(0.55 * _norm(fund_hits) + 0.35 * has_money + 0.10 * has_contract)
    result["unclear_topic_signal"] = result["state"].isin(UNCLEAR_STATES).astype(float)

    result["urgency_score"] = _clip01(
        0.62 * result["timeliness_signal"] + 0.18 * result["funding_signal"] + 0.20 * has_project
    )
    result["misclassification_risk_score"] = _clip01(
        0.30 * (1.0 - _num(result.get("top1_probability", 0)))
        + 0.26 * _num(result.get("entropy", 0))
        + 0.22 * (1.0 - _num(result.get("relative_margin", 0)))
        + 0.12 * (1.0 - _num(result.get("TAI", 0)))
        + 0.10 * (1.0 - _num(result.get("parse_quality", 0)))
    )
    state_review = result["state"].map(
        {
            "A_clear_auto_archive": 0.08,
            "A_assisted_archive": 0.30,
            "B_overlap_manual_review": 0.82,
            "C_unknown_expert_review": 0.92,
        }
    ).fillna(0.65)
    result["review_necessity_score"] = _clip01(
        0.36 * state_review
        + 0.24 * result["misclassification_risk_score"]
        + 0.16 * (1.0 - _num(result.get("MII", 0)))
        + 0.14 * result["funding_signal"]
        + 0.10 * result["timeliness_signal"]
    )

    score_columns = ["urgency_score", "misclassification_risk_score", "review_necessity_score"]
    objective = _entropy_weights(result[score_columns])
    combined = _combined_weights(SUBJECTIVE_WEIGHTS, objective)
    result["base_priority_score"] = _clip01(
        combined["urgency"] * result["urgency_score"]
        + combined["misclassification_risk"] * result["misclassification_risk_score"]
        + combined["review_necessity"] * result["review_necessity_score"]
    )
    result["special_focus"] = (
        (result["unclear_topic_signal"] > 0)
        | (result["timeliness_signal"] >= 0.55)
        | (result["funding_signal"] >= 0.45)
    )
    result["special_focus_reason"] = result.apply(_special_reason, axis=1)
    result["priority_score"] = _clip01(result["base_priority_score"] * (1.0 + SPECIAL_BOOST_MU * result["special_focus"].astype(float)))

    result["urgency_level"] = _quantile_level(result["urgency_score"])
    result["risk_level"] = _quantile_level(result["misclassification_risk_score"])
    result["review_necessity_level"] = _quantile_level(result["review_necessity_score"])
    result["overall_level"] = _quantile_level(result["priority_score"])
    result["estimated_review_minutes"] = result.apply(_review_minutes, axis=1)
    result["review_value"] = _clip01(0.70 * result["priority_score"] + 0.30 * result["misclassification_risk_score"])
    result["value_density"] = result["review_value"] / result["estimated_review_minutes"].clip(lower=1)
    result["recommended_action"] = result.apply(_recommended_action, axis=1)
    result["recommended_action_zh"] = result["recommended_action"].map(_action_zh)
    result["recommended_action_en"] = result["recommended_action"].map(_action_en)
    result["needs_review"] = result["recommended_action"].isin(["expert_review", "manual_review", "priority_sampling"]).astype(int)
    result["needs_review_zh"] = result["needs_review"].map({1: "是", 0: "否"})
    return result.sort_values("priority_score", ascending=False).reset_index(drop=True), {
        "subjective": dict(SUBJECTIVE_WEIGHTS),
        "objective": objective,
        "combined": combined,
    }


def _entropy_weights(scores: pd.DataFrame) -> dict[str, float]:
    matrix = scores.fillna(0).clip(0, 1).to_numpy(dtype=float)
    if matrix.size == 0:
        return {"urgency": 1 / 3, "misclassification_risk": 1 / 3, "review_necessity": 1 / 3}
    matrix = matrix + 1e-12
    proportions = matrix / matrix.sum(axis=0, keepdims=True)
    n = max(2, matrix.shape[0])
    entropy = -(proportions * np.log(proportions)).sum(axis=0) / math.log(n)
    diversity = 1.0 - entropy
    if diversity.sum() <= 1e-12:
        weights = np.ones(3) / 3
    else:
        weights = diversity / diversity.sum()
    return {
        "urgency": round(float(weights[0]), 6),
        "misclassification_risk": round(float(weights[1]), 6),
        "review_necessity": round(float(weights[2]), 6),
    }


def _combined_weights(subjective: dict[str, float], objective: dict[str, float]) -> dict[str, float]:
    raw = {key: (1.0 - ENTROPY_BLEND) * subjective[key] + ENTROPY_BLEND * objective[key] for key in subjective}
    total = sum(raw.values()) or 1.0
    return {key: round(value / total, 6) for key, value in raw.items()}


def _allocate_scenarios(
    scored: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.DataFrame]:
    queues: dict[str, pd.DataFrame] = {}
    auto_archives: dict[str, pd.DataFrame] = {}
    comparison_rows: list[dict[str, object]] = []
    review_pool = scored[scored["recommended_action"].isin(["manual_review", "expert_review", "priority_sampling"])].copy()
    auto_pool = scored[scored["recommended_action"].isin(["auto_archive", "assisted_archive"])].copy()
    high_level_total = int((scored["overall_level"] == "高").sum())
    level_rank = {"高": 0, "中": 1, "低": 2}
    action_rank = {"expert_review": 0, "manual_review": 1, "priority_sampling": 2}
    review_pool["_level_rank"] = review_pool["overall_level"].map(level_rank).fillna(3).astype(int)
    review_pool["_action_rank"] = review_pool["recommended_action"].map(action_rank).fillna(2).astype(int)
    review_pool = review_pool.sort_values(
        ["_action_rank", "_level_rank", "priority_score", "value_density"],
        ascending=[True, True, False, False],
    )
    auto_pool["archive_score"] = _clip01(
        0.45 * _num(auto_pool.get("top1_probability", 0))
        + 0.35 * _num(auto_pool.get("ARS", 0))
        + 0.20 * _num(auto_pool.get("MII", 0))
    )
    auto_pool = auto_pool.sort_values("archive_score", ascending=False)

    for _, scenario in scenarios.iterrows():
        scenario_id = str(scenario["scenario_id"])
        manual_hour_limit = float(scenario["manual_hours_per_day"])
        manual_count_limit = int(scenario["manual_review_capacity_per_day"])
        auto_count_limit = int(scenario["auto_archive_capacity_per_day"])
        selected = _select_review_queue(review_pool, manual_hour_limit * 60, manual_count_limit)
        auto_selected = auto_pool.head(auto_count_limit).copy()
        selected["scenario_id"] = scenario_id
        auto_selected["scenario_id"] = scenario_id
        selected["review_rank"] = range(1, len(selected) + 1)
        auto_selected["archive_rank"] = range(1, len(auto_selected) + 1)
        queues[scenario_id] = selected.drop(columns=["_level_rank", "_action_rank"], errors="ignore")
        auto_archives[scenario_id] = auto_selected

        reviewed_ids = set(selected["file_id"].astype(str))
        auto_ids = set(auto_selected["file_id"].astype(str))
        residual = scored[~scored["file_id"].astype(str).isin(reviewed_ids | auto_ids)]
        selected_minutes = float(selected["estimated_review_minutes"].sum())
        review_hours = selected_minutes / 60
        estimated_cost = review_hours * HOURLY_COST_INDEX
        high_level_reviewed = int((selected["overall_level"] == "高").sum())
        comparison_rows.append(
            {
                "scenario_id": scenario_id,
                "manual_hour_limit": manual_hour_limit,
                "manual_count_limit": manual_count_limit,
                "auto_archive_capacity": auto_count_limit,
                "review_selected_count": int(len(selected)),
                "review_minutes": round(selected_minutes, 3),
                "review_hours": round(review_hours, 3),
                "max_completion_hours": round(review_hours, 3),
                "manual_utilization": round(float(selected_minutes / max(1, manual_hour_limit * 60)), 6),
                "auto_archive_count": int(len(auto_selected)),
                "deferred_count": int(len(residual)),
                "covered_review_value": round(float(selected["review_value"].sum()), 6),
                "residual_risk_value": round(float(residual["review_value"].sum()), 6),
                "unreviewed_risk_value": round(float(residual["review_value"].sum()), 6),
                "estimated_cost_index": round(float(estimated_cost), 6),
                "total_cost_index": round(float(estimated_cost), 6),
                "high_level_total": high_level_total,
                "high_level_reviewed": high_level_reviewed,
                "high_level_coverage_rate": round(high_level_reviewed / max(1, high_level_total), 6),
                "unknown_reviewed": int((selected["state"] == "C_unknown_expert_review").sum()),
                "overlap_reviewed": int((selected["state"] == "B_overlap_manual_review").sum()),
            }
        )
    return queues, auto_archives, pd.DataFrame(comparison_rows)


def _select_review_queue(pool: pd.DataFrame, minute_limit: float, count_limit: int) -> pd.DataFrame:
    selected_rows = []
    used_minutes = 0.0
    for _, row in pool.iterrows():
        minutes = float(row["estimated_review_minutes"])
        if len(selected_rows) >= count_limit:
            break
        if used_minutes + minutes > minute_limit:
            continue
        selected_rows.append(row)
        used_minutes += minutes
    return pd.DataFrame(selected_rows).reset_index(drop=True) if selected_rows else pool.head(0).copy()


def _level_summary(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dimension, column in [
        ("紧急程度", "urgency_level"),
        ("错分风险", "risk_level"),
        ("复核必要性", "review_necessity_level"),
        ("综合优先级", "overall_level"),
    ]:
        counts = scored[column].value_counts()
        total = len(scored) or 1
        for level in ["高", "中", "低"]:
            count = int(counts.get(level, 0))
            rows.append({"dimension_zh": dimension, "level_zh": level, "count": count, "share": round(count / total, 6)})
    return pd.DataFrame(rows)


def _write_outputs(
    output_dir: Path,
    scored: pd.DataFrame,
    level_summary: pd.DataFrame,
    scenario_comparison: pd.DataFrame,
    queues: dict[str, pd.DataFrame],
    auto_archives: dict[str, pd.DataFrame],
    metrics: dict[str, object],
) -> None:
    scored.to_csv(output_dir / "problem3_risk_priority.csv", index=False, encoding="utf-8-sig")
    level_summary.to_csv(output_dir / "problem3_level_summary.csv", index=False, encoding="utf-8-sig")
    scenario_comparison.to_csv(output_dir / "problem3_scenario_comparison.csv", index=False, encoding="utf-8-sig")
    special = scored[scored["special_focus"]].sort_values("priority_score", ascending=False)
    special.to_csv(output_dir / "problem3_special_focus.csv", index=False, encoding="utf-8-sig")
    for scenario_id, queue in queues.items():
        queue.to_csv(output_dir / f"problem3_review_queue_{scenario_id}.csv", index=False, encoding="utf-8-sig")
    for scenario_id, archive in auto_archives.items():
        archive.to_csv(output_dir / f"problem3_auto_archive_{scenario_id}.csv", index=False, encoding="utf-8-sig")
    (output_dir / "problem3_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "problem3_optimization_report.md").write_text(
        _markdown_report(scored, level_summary, scenario_comparison, queues, metrics),
        encoding="utf-8",
    )


def _write_plot_data(
    output_dir: Path,
    scored: pd.DataFrame,
    level_summary: pd.DataFrame,
    scenario_comparison: pd.DataFrame,
    queues: dict[str, pd.DataFrame],
) -> None:
    level_plot = level_summary.copy()
    level_plot["dimension_en"] = level_plot["dimension_zh"].map(
        {"紧急程度": "Urgency", "错分风险": "Misclassification Risk", "复核必要性": "Review Necessity", "综合优先级": "Overall Priority"}
    )
    level_plot["level_en"] = level_plot["level_zh"].map({"高": "High", "中": "Medium", "低": "Low"})
    _save_plot_data(output_dir, "problem3_level_distribution", level_plot)

    scenario_plot = scenario_comparison.copy()
    _save_plot_data(output_dir, "problem3_scenario_comparison", scenario_plot)

    action_plot = (
        scored.groupby(["dataset_id", "recommended_action"]).size().reset_index(name="count")
    )
    action_plot["action_zh"] = action_plot["recommended_action"].map(_action_zh)
    action_plot["action_en"] = action_plot["recommended_action"].map(_action_en)
    action_plot["dataset_share"] = (action_plot["count"] / action_plot.groupby("dataset_id")["count"].transform("sum")).round(6)
    _save_plot_data(output_dir, "problem3_action_distribution", action_plot)

    top_queue_rows = []
    for scenario_id, queue in queues.items():
        by_topic = queue.groupby(["top1_topic_id", "top1_topic_name"]).size().reset_index(name="count")
        by_topic["scenario_id"] = scenario_id
        top_queue_rows.append(by_topic)
    queue_plot = pd.concat(top_queue_rows, ignore_index=True) if top_queue_rows else pd.DataFrame()
    if not queue_plot.empty:
        queue_plot["topic_name_en"] = queue_plot["top1_topic_name"].map(_topic_name_en)
    _save_plot_data(output_dir, "problem3_review_queue_topic_distribution", queue_plot)


def _write_charts(
    output_dir: Path,
    scored: pd.DataFrame,
    level_summary: pd.DataFrame,
    scenario_comparison: pd.DataFrame,
    queues: dict[str, pd.DataFrame],
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    level_plot = pd.read_csv(output_dir / "problem3_level_distribution_plot_data.csv")
    if not level_plot.empty:
        pivot = level_plot.pivot_table(index="dimension_en", columns="level_en", values="count", fill_value=0)
        pivot = pivot.reindex(columns=["High", "Medium", "Low"], fill_value=0)
        fig, ax = plt.subplots(figsize=(10, 5.4))
        pivot.plot.bar(ax=ax, color=["#E45756", "#F2A541", "#54A24B"], rot=18)
        ax.set_title("Problem 3 Risk Level Distribution")
        ax.set_xlabel("")
        ax.set_ylabel("Record count")
        ax.legend(title="Level")
        fig.tight_layout()
        fig.savefig(output_dir / "problem3_level_distribution.png", dpi=220)
        plt.close(fig)

    if not scenario_comparison.empty:
        fig, ax = plt.subplots(figsize=(9.5, 5.2))
        x = np.arange(len(scenario_comparison))
        ax.bar(x - 0.22, scenario_comparison["review_selected_count"], width=0.22, label="Manual review", color="#4C78A8")
        ax.bar(x, scenario_comparison["auto_archive_count"], width=0.22, label="Auto archive", color="#54A24B")
        ax.bar(x + 0.22, scenario_comparison["deferred_count"], width=0.22, label="Deferred", color="#ECA82C")
        ax.set_xticks(x)
        ax.set_xticklabels(scenario_comparison["scenario_id"])
        ax.set_ylabel("Record count")
        ax.set_title("Scenario Processing Comparison")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / "problem3_scenario_comparison.png", dpi=220)
        plt.close(fig)

    action_plot = pd.read_csv(output_dir / "problem3_action_distribution_plot_data.csv")
    if not action_plot.empty:
        pivot = action_plot.pivot_table(index="dataset_id", columns="action_en", values="count", fill_value=0)
        fig, ax = plt.subplots(figsize=(10, 5.2))
        pivot.plot.bar(stacked=True, ax=ax, colormap="Set2", rot=0)
        ax.set_title("Recommended Action Distribution")
        ax.set_xlabel("")
        ax.set_ylabel("Record count")
        ax.legend(title="Action", loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
        fig.tight_layout()
        fig.savefig(output_dir / "problem3_action_distribution.png", dpi=220)
        plt.close(fig)

    queue_plot = pd.read_csv(output_dir / "problem3_review_queue_topic_distribution_plot_data.csv")
    if not queue_plot.empty:
        topic_index = "topic_name_en" if "topic_name_en" in queue_plot.columns else "top1_topic_name"
        pivot = queue_plot.pivot_table(index=topic_index, columns="scenario_id", values="count", fill_value=0)
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
        fig, ax = plt.subplots(figsize=(9.5, max(4.8, 0.42 * len(pivot))))
        pivot.plot.barh(ax=ax, color=["#4C78A8", "#F58518", "#72B7B2"])
        ax.set_title("Review Queue Topic Distribution")
        ax.set_xlabel("Selected records")
        ax.set_ylabel("")
        fig.tight_layout()
        fig.savefig(output_dir / "problem3_review_queue_topic_distribution.png", dpi=220)
        plt.close(fig)


def _save_plot_data(output_dir: Path, stem: str, frame: pd.DataFrame) -> None:
    frame.to_csv(output_dir / f"{stem}_plot_data.csv", index=False, encoding="utf-8-sig")
    frame.to_csv(output_dir / f"{stem}.png.csv", index=False, encoding="utf-8-sig")


def _markdown_report(
    scored: pd.DataFrame,
    level_summary: pd.DataFrame,
    scenario_comparison: pd.DataFrame,
    queues: dict[str, pd.DataFrame],
    metrics: dict[str, object],
) -> str:
    top_cols = [
        "file_id",
        "dataset_id",
        "file_name",
        "top1_topic_name",
        "state",
        "urgency_level",
        "risk_level",
        "review_necessity_level",
        "overall_level",
        "priority_score",
        "special_focus_reason",
        "recommended_action",
    ]
    lines = [
        "# 问题三复核优先级与资源约束优化报告",
        "",
        "## 模型概览",
        "",
        f"- 模型：`{metrics['model']}`",
        f"- 文件数：`{metrics['record_count']}`",
        f"- 主观权重：`{json.dumps(metrics['subjective_weights'], ensure_ascii=False)}`",
        f"- 熵权：`{json.dumps(metrics['objective_entropy_weights'], ensure_ascii=False)}`",
        f"- 综合权重：`{json.dumps(metrics['combined_weights'], ensure_ascii=False)}`",
        "",
        "## 等级分布",
        "",
        _frame_to_markdown(level_summary),
        "",
        "## 资源场景对比",
        "",
        _frame_to_markdown(scenario_comparison),
        "",
        "## Top 30 复核候选",
        "",
        _frame_to_markdown(scored[top_cols].head(30)),
        "",
    ]
    for scenario_id, queue in queues.items():
        lines.extend([
            f"## {scenario_id} 复核队列前 15",
            "",
            _frame_to_markdown(queue[top_cols + ["review_rank", "estimated_review_minutes"]].head(15) if not queue.empty else queue),
            "",
        ])
    return "\n".join(lines)


def _frame_to_markdown(frame: pd.DataFrame, max_col_width: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
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
    return "\n".join([header, sep, *rows])


def _term_hits(text: str, terms: tuple[str, ...]) -> int:
    return sum(str(text).count(term) for term in terms)


def _recency_signal(date_list: object) -> pd.Series | float:
    if isinstance(date_list, pd.Series):
        return date_list.fillna("").astype(str).map(_single_recency_signal)
    return _single_recency_signal("" if pd.isna(date_list) else str(date_list))


def _single_recency_signal(value: str) -> float:
    years = [int(year) for year in re.findall(r"20\d{2}", value)]
    if not years:
        return 0.0
    latest = max(years)
    if latest >= 2026:
        return 1.0
    if latest == 2025:
        return 0.72
    if latest == 2024:
        return 0.42
    return 0.18


def _review_minutes(row: pd.Series) -> float:
    text_length = float(row.get("text_length", 0) or 0)
    base = 10.0 + min(16.0, math.log1p(max(text_length, 0)) * 1.8)
    if row.get("state") == "C_unknown_expert_review":
        base += 7.0
    elif row.get("state") == "B_overlap_manual_review":
        base += 4.0
    if float(row.get("funding_signal", 0) or 0) >= 0.45:
        base += 3.0
    if float(row.get("timeliness_signal", 0) or 0) >= 0.55:
        base += 2.0
    return round(float(np.clip(base, 8.0, 35.0)), 3)


def _recommended_action(row: pd.Series) -> str:
    if row.get("state") == "C_unknown_expert_review":
        return "expert_review"
    if row.get("state") == "B_overlap_manual_review":
        return "manual_review"
    if row.get("overall_level") == "高" or row.get("special_focus"):
        return "priority_sampling"
    if row.get("state") == "A_clear_auto_archive":
        return "auto_archive"
    return "assisted_archive"


def _special_reason(row: pd.Series) -> str:
    reasons = []
    if row.get("unclear_topic_signal", 0) > 0:
        reasons.append("主题不明确")
    if row.get("timeliness_signal", 0) >= 0.55:
        reasons.append("高时效")
    if row.get("funding_signal", 0) >= 0.45:
        reasons.append("资金相关")
    return "、".join(reasons) if reasons else "常规样本"


def _quantile_level(series: pd.Series) -> pd.Series:
    values = series.fillna(0).astype(float)
    q30 = values.quantile(0.30)
    q70 = values.quantile(0.70)
    return values.map(lambda value: "高" if value >= q70 else ("中" if value >= q30 else "低"))


def _action_zh(action: str) -> str:
    return {
        "expert_review": "专家研判",
        "manual_review": "人工复核",
        "priority_sampling": "重点抽检",
        "auto_archive": "自动归档",
        "assisted_archive": "辅助归档",
    }.get(action, action)


def _action_en(action: str) -> str:
    return {
        "expert_review": "Expert review",
        "manual_review": "Manual review",
        "priority_sampling": "Priority sampling",
        "auto_archive": "Auto archive",
        "assisted_archive": "Assisted archive",
    }.get(action, action)


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
        "医药项目审批类": "Medical Approval",
        "地区统计指标类": "Regional Indicators",
        "投资价格统计类": "Investment Price",
        "教育基础统计类": "Basic Education",
        "未明确主题": "Unclear Topic",
    }
    text = "" if pd.isna(topic_name) else str(topic_name)
    return names.get(text, "Topic")


def _num(values: pd.Series | object) -> pd.Series:
    if isinstance(values, pd.Series):
        return pd.to_numeric(values, errors="coerce").fillna(0.0).astype(float)
    return pd.Series(values, dtype=float)


def _norm(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce").fillna(0.0).astype(float)
    maximum = values.max()
    if maximum <= 0:
        return values * 0.0
    return (values / maximum).clip(0, 1)


def _clip01(values: pd.Series | np.ndarray | float) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.fillna(0.0).astype(float).clip(0, 1)
    if isinstance(values, np.ndarray):
        return pd.Series(np.clip(values, 0, 1))
    return pd.Series([float(np.clip(values, 0, 1))])
