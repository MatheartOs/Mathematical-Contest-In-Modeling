"""Build final paper-facing result tables for the B problem workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.paths import ensure_output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    root = ensure_output_root()
    parser.add_argument("--cleaning-dir", type=Path, default=root / "cleaning_ocr_full")
    parser.add_argument("--problem1-dir", type=Path, default=root / "problem1_innovative")
    parser.add_argument("--problem2-dir", type=Path, default=root / "problem2_transfer")
    parser.add_argument("--problem3-dir", type=Path, default=root / "problem3_optimization")
    parser.add_argument("--output-dir", type=Path, default=root / "final_results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    document_index = pd.read_csv(args.cleaning_dir / "processed" / "document_index.csv")
    problem1_summary = pd.read_csv(args.problem1_dir / "problem1_graph_topic_summary.csv")
    problem2_classification = pd.read_csv(args.problem2_dir / "problem2_transfer_classification.csv")
    problem3_priority = pd.read_csv(args.problem3_dir / "problem3_risk_priority.csv")
    scenario_comparison = pd.read_csv(args.problem3_dir / "problem3_scenario_comparison.csv")

    preprocessing = _preprocessing_statistics(document_index)
    problem1_table = _problem1_table(problem1_summary)
    problem2_table = _problem2_table(problem2_classification)
    problem3_table = _problem3_table(problem3_priority)
    scenario_table = _scenario_table(scenario_comparison)

    preprocessing.to_csv(args.output_dir / "data_preprocessing_statistics.csv", index=False, encoding="utf-8-sig")
    problem1_table.to_csv(args.output_dir / "problem1_classification_result_table.csv", index=False, encoding="utf-8-sig")
    problem2_table.to_csv(args.output_dir / "problem2_assignment_evaluation_table.csv", index=False, encoding="utf-8-sig")
    problem3_table.to_csv(args.output_dir / "problem3_review_priority_table.csv", index=False, encoding="utf-8-sig")
    scenario_table.to_csv(args.output_dir / "resource_scenario_comparison_table.csv", index=False, encoding="utf-8-sig")

    _write_preprocessing_chart(args.output_dir, preprocessing)
    (args.output_dir / "final_deliverables_report.md").write_text(
        _report(preprocessing, problem1_table, problem2_table, problem3_table, scenario_table),
        encoding="utf-8",
    )

    print(
        {
            "output_dir": str(args.output_dir),
            "tables": [
                "data_preprocessing_statistics.csv",
                "problem1_classification_result_table.csv",
                "problem2_assignment_evaluation_table.csv",
                "problem3_review_priority_table.csv",
                "resource_scenario_comparison_table.csv",
            ],
            "charts": ["data_preprocessing_file_type_distribution.png"],
        }
    )


def _preprocessing_statistics(document_index: pd.DataFrame) -> pd.DataFrame:
    frame = document_index.copy()
    frame = frame[frame["dataset_id"].isin(["dataset1", "dataset2", "dataset3"])].copy()
    for column in ["text_length", "missing_rate", "parse_success", "parse_quality", "need_manual_check", "file_size_kb", "ocr_used"]:
        frame[column] = pd.to_numeric(frame.get(column, 0), errors="coerce").fillna(0.0)
    grouped = (
        frame.groupby(["dataset_id", "file_type"], dropna=False)
        .agg(
            file_count=("file_id", "count"),
            avg_text_length=("text_length", "mean"),
            missing_field_rate=("missing_rate", "mean"),
            parse_success_rate=("parse_success", "mean"),
            avg_parse_quality=("parse_quality", "mean"),
            manual_check_rate=("need_manual_check", "mean"),
            avg_file_size_kb=("file_size_kb", "mean"),
            ocr_file_count=("ocr_used", "sum"),
        )
        .reset_index()
    )
    grouped["dataset_name_zh"] = grouped["dataset_id"].map(
        {
            "dataset1": "数据集1：历史真实文件",
            "dataset2": "数据集2：半结构化记录",
            "dataset3": "数据集3：匿名原始文件",
        }
    )
    grouped["file_type_zh"] = grouped["file_type"].fillna("unknown").astype(str)
    numeric_cols = [
        "avg_text_length",
        "missing_field_rate",
        "parse_success_rate",
        "avg_parse_quality",
        "manual_check_rate",
        "avg_file_size_kb",
        "ocr_file_count",
    ]
    for column in numeric_cols:
        grouped[column] = pd.to_numeric(grouped[column], errors="coerce").fillna(0.0).round(6)
    grouped["ocr_file_count"] = grouped["ocr_file_count"].astype(int)
    return grouped.sort_values(["dataset_id", "file_count"], ascending=[True, False]).reset_index(drop=True)


def _problem1_table(summary: pd.DataFrame) -> pd.DataFrame:
    table = summary.copy()
    columns = {
        "topic_id": "类别编号",
        "topic_name": "主题名称",
        "ctfidf_terms": "关键词",
        "representative_files": "代表文件",
        "representative_titles": "代表文件标题",
        "history_count": "样本数量",
        "dominant_file_types": "主要文件格式",
        "business_profile": "业务属性画像",
        "topic_explanation": "主题解释",
    }
    available = [column for column in columns if column in table.columns]
    return table[available].rename(columns=columns)


def _problem2_table(classification: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "file_id": "文件编号",
        "dataset_id": "数据集",
        "file_name": "文件名",
        "top1_topic_id": "预测类别编号",
        "top1_topic_name": "预测类别名称",
        "top1_probability": "置信度",
        "ARS": "归属合理性ARS",
        "MII": "模型解释指数MII",
        "TAI": "迁移适用性TAI",
        "state": "状态标签",
        "state_zh": "状态中文",
        "explanation_terms": "解释词",
    }
    table = classification.copy()
    if "state_zh" not in table:
        table["state_zh"] = table["state"].map(_state_zh)
    available = [column for column in columns if column in table.columns]
    return table[available].rename(columns=columns)


def _problem3_table(priority: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "file_id": "文件编号",
        "dataset_id": "数据集",
        "file_name": "文件名",
        "top1_topic_name": "预测主题",
        "urgency_score": "紧急程度得分",
        "urgency_level": "紧急程度等级",
        "misclassification_risk_score": "错分风险得分",
        "risk_level": "错分风险等级",
        "review_necessity_score": "复核必要性得分",
        "review_necessity_level": "复核必要性等级",
        "priority_score": "综合得分",
        "overall_level": "综合等级",
        "needs_review_zh": "是否复核",
        "recommended_action_zh": "建议动作",
        "special_focus_reason": "重点关注原因",
        "estimated_review_minutes": "预计复核分钟",
    }
    table = priority.copy()
    if "needs_review_zh" not in table and "recommended_action" in table:
        table["needs_review_zh"] = table["recommended_action"].isin(["expert_review", "manual_review", "priority_sampling"]).map({True: "是", False: "否"})
    available = [column for column in columns if column in table.columns]
    return table[available].rename(columns=columns)


def _scenario_table(scenario: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "scenario_id": "场景编号",
        "review_selected_count": "复核文件数量",
        "total_cost_index": "总成本指数",
        "max_completion_hours": "最大完工时间_小时",
        "unreviewed_risk_value": "未复核风险",
        "high_level_coverage_rate": "高等级文件覆盖率",
        "manual_hour_limit": "人工工时上限",
        "manual_count_limit": "人工复核数量上限",
        "auto_archive_capacity": "自动归档能力上限",
        "auto_archive_count": "自动归档数量",
        "deferred_count": "延后处理数量",
        "unknown_reviewed": "未知样本复核数",
        "overlap_reviewed": "重叠样本复核数",
        "manual_utilization": "人工资源利用率",
    }
    available = [column for column in columns if column in scenario.columns]
    return scenario[available].rename(columns=columns)


def _write_preprocessing_chart(output_dir: Path, preprocessing: pd.DataFrame) -> None:
    plot_data = preprocessing.copy()
    plot_data.to_csv(output_dir / "data_preprocessing_file_type_distribution_plot_data.csv", index=False, encoding="utf-8-sig")
    plot_data.to_csv(output_dir / "data_preprocessing_file_type_distribution.png.csv", index=False, encoding="utf-8-sig")
    pivot = plot_data.pivot_table(index="file_type", columns="dataset_id", values="file_count", aggfunc="sum", fill_value=0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9.5, max(4.8, 0.45 * len(pivot))))
    pivot.plot.barh(ax=ax, color=["#4C78A8", "#F58518", "#54A24B"])
    ax.set_title("Preprocessing File Type Distribution")
    ax.set_xlabel("File count")
    ax.set_ylabel("File type")
    fig.tight_layout()
    fig.savefig(output_dir / "data_preprocessing_file_type_distribution.png", dpi=220)
    plt.close(fig)


def _state_zh(state: str) -> str:
    return {
        "A_clear_auto_archive": "清晰自动归档",
        "A_assisted_archive": "辅助归档",
        "B_overlap_manual_review": "重叠人工复核",
        "C_unknown_expert_review": "未知专家研判",
    }.get(str(state), str(state))


def _report(
    preprocessing: pd.DataFrame,
    problem1_table: pd.DataFrame,
    problem2_table: pd.DataFrame,
    problem3_table: pd.DataFrame,
    scenario_table: pd.DataFrame,
) -> str:
    return "\n".join(
        [
            "# B题最终交付结果表清单",
            "",
            f"- 数据预处理统计表：`{len(preprocessing)}` 行，覆盖不同数据集与文件格式。",
            f"- 问题一分类结果表：`{len(problem1_table)}` 行，覆盖主题编号、主题名称、关键词、代表文件和样本数量。",
            f"- 问题二归属评价表：`{len(problem2_table)}` 行，覆盖预测类别、置信度、ARS、MII、TAI 和状态标签。",
            f"- 问题三复核优先级表：`{len(problem3_table)}` 行，覆盖紧急程度、错分风险、复核必要性、综合得分、等级和是否复核。",
            f"- 资源约束场景对比表：`{len(scenario_table)}` 行，覆盖复核文件数量、总成本、最大完工时间、未复核风险和高等级文件覆盖率。",
            "",
            "所有 PNG 图均配套同名 `.png.csv` 与 `_plot_data.csv` 作图数据。",
        ]
    )


if __name__ == "__main__":
    main()
