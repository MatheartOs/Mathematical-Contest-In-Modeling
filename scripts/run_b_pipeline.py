"""Run the B problem implementation chain and produce compact results.

The script is intended as the main reproducible pipeline:

1. extract/cache bounded text and metadata from datasets 1 and 2;
2. load all dataset 3 text fragments;
3. build the historical topic system from dataset 1;
4. transfer-classify datasets 2 and 3;
5. score manual-review priority under dataset 4 scenarios;
6. write CSV/Markdown summaries and PNG charts.

Large files are included as metadata-only records by default. This protects the
contest machine from accidental multi-hour parsing while keeping the file IDs
visible in result tables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.features import KEYWORD_GROUPS, build_feature_frame
from mcm_b.modeling import classify_records, fit_topic_model, save_topic_model
from mcm_b.paths import DATASET1_DIR, DATASET2_DIR, DATASET3_XLSX, DATASET4_XLSX, DATA_ROOT, ensure_output_root
from mcm_b.readers import (
    DocumentRecord,
    load_records_jsonl,
    make_metadata_only_record,
    read_document,
    save_records_jsonl,
)
from mcm_b.risk import allocate_reviews_by_scenario, load_resource_scenarios, score_review_priority


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ensure_output_root() / "run_full")
    parser.add_argument("--max-chars", type=int, default=12_000)
    parser.add_argument("--max-file-mb", type=float, default=25.0)
    parser.add_argument("--clusters", type=int, default=10)
    parser.add_argument("--history-limit", type=int, default=0, help="0 means no limit.")
    parser.add_argument("--new-file-limit", type=int, default=0, help="0 means no limit.")
    parser.add_argument("--dataset3-limit", type=int, default=0, help="0 means no limit.")
    parser.add_argument("--force-cache", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    history_records = _load_or_extract_file_dataset(
        DATASET1_DIR,
        dataset="dataset1",
        cache_path=args.output_dir / "cache_dataset1.jsonl",
        limit=args.history_limit,
        max_chars=args.max_chars,
        max_file_mb=args.max_file_mb,
        force_cache=args.force_cache,
    )
    new_file_records = _load_or_extract_file_dataset(
        DATASET2_DIR,
        dataset="dataset2",
        cache_path=args.output_dir / "cache_dataset2.jsonl",
        limit=args.new_file_limit,
        max_chars=args.max_chars,
        max_file_mb=args.max_file_mb,
        force_cache=args.force_cache,
    )
    dataset3_records = _load_dataset3_records(args.dataset3_limit, args.max_chars)

    history_features = build_feature_frame(history_records)
    new_records = new_file_records + dataset3_records
    new_features = build_feature_frame(new_records)

    usable_history = _usable_text_records(history_records)
    if len(usable_history) < args.clusters:
        raise RuntimeError(f"Only {len(usable_history)} usable history records; cannot fit {args.clusters} clusters.")

    topic_model = fit_topic_model(usable_history, n_clusters=args.clusters)
    classified = classify_records(topic_model, _usable_text_records(new_records))
    priority = score_review_priority(classified, new_features)
    scenarios = load_resource_scenarios(DATASET4_XLSX)
    queues = allocate_reviews_by_scenario(priority, scenarios)

    _write_tables(args.output_dir, history_features, new_features, topic_model.assignments, classified, priority, queues)
    _write_keyword_theme_tables(args.output_dir, history_features, new_features)
    topic_summary = _build_topic_summary(topic_model.assignments, topic_model.topic_terms, history_features)
    topic_summary.to_csv(args.output_dir / "problem1_topic_summary.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "problem1_topic_summary.md").write_text(
        _frame_to_markdown(topic_summary),
        encoding="utf-8",
    )

    run_summary = _build_run_summary(
        args=args,
        history_records=history_records,
        new_file_records=new_file_records,
        dataset3_records=dataset3_records,
        topic_summary=topic_summary,
        classified=classified,
        priority=priority,
        queues=queues,
        elapsed_seconds=perf_counter() - started,
    )
    (args.output_dir / "run_summary.json").write_text(
        json.dumps(run_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_markdown_report(args.output_dir, run_summary, topic_summary, priority)
    _write_charts(args.output_dir, topic_summary, classified, priority)

    save_topic_model(topic_model, args.output_dir / "topic_model.joblib")
    print(json.dumps(run_summary, ensure_ascii=False, indent=2))


def _load_or_extract_file_dataset(
    directory: Path,
    dataset: str,
    cache_path: Path,
    limit: int,
    max_chars: int,
    max_file_mb: float,
    force_cache: bool,
) -> list[DocumentRecord]:
    if cache_path.exists() and not force_cache:
        return load_records_jsonl(cache_path)

    files = sorted(path for path in directory.iterdir() if path.is_file())
    if limit:
        files = files[:limit]

    records: list[DocumentRecord] = []
    max_bytes = int(max_file_mb * 1024 * 1024)
    for index, path in enumerate(files, start=1):
        size = path.stat().st_size
        if size > max_bytes:
            record = make_metadata_only_record(
                path,
                dataset=dataset,
                status="skipped_large",
                warning=f"Skipped text extraction because file exceeds {max_file_mb} MB.",
            )
        else:
            record = read_document(path, dataset=dataset, max_chars=max_chars)
        records.append(record)
        if index % 250 == 0:
            print(f"[{dataset}] extracted {index}/{len(files)}")

    save_records_jsonl(records, cache_path)
    return records


def _load_dataset3_records(limit: int, max_chars: int) -> list[DocumentRecord]:
    nrows = limit if limit else None
    frame = pd.read_excel(DATASET3_XLSX, nrows=nrows)
    records: list[DocumentRecord] = []
    for _, row in frame.iterrows():
        doc_id = str(row.get("文件编号", ""))
        text = "" if pd.isna(row.get("正文片段", "")) else str(row.get("正文片段", ""))[:max_chars]
        time_info = "" if pd.isna(row.get("时间信息", "")) else str(row.get("时间信息", ""))
        records.append(
            DocumentRecord(
                doc_id=doc_id,
                path=f"{DATASET3_XLSX}#{doc_id}",
                dataset="dataset3",
                extension=".xlsx-row",
                size_bytes=len(text.encode("utf-8")),
                text=text,
                status="ok",
                metadata={"time_info": time_info},
            )
        )
    return records


def _usable_text_records(records: list[DocumentRecord]) -> list[DocumentRecord]:
    return [
        record
        for record in records
        if record.status in {"ok", "pdf_no_text"} and len((record.text or "").strip()) >= 40
        and not _is_low_content_metadata(record)
    ]


def _is_low_content_metadata(record: DocumentRecord) -> bool:
    text = (record.text or "").lstrip()
    image_name = "\u56fe\u7247\u540d\u79f0:"
    download_url = "\u4e0b\u8f7dURL:"
    if text.startswith(image_name) and download_url in text[:500]:
        return True
    if record.extension in {".jpg", ".jpeg", ".png"}:
        return True
    return False


def _write_tables(
    output_dir: Path,
    history_features: pd.DataFrame,
    new_features: pd.DataFrame,
    history_assignments: pd.DataFrame,
    classified: pd.DataFrame,
    priority: pd.DataFrame,
    queues: dict[str, pd.DataFrame],
) -> None:
    history_features.to_csv(output_dir / "problem1_history_features.csv", index=False, encoding="utf-8-sig")
    new_features.to_csv(output_dir / "problem2_new_features.csv", index=False, encoding="utf-8-sig")
    history_assignments.to_csv(output_dir / "problem1_history_topic_assignments.csv", index=False, encoding="utf-8-sig")
    classified.to_csv(output_dir / "problem2_new_classification.csv", index=False, encoding="utf-8-sig")
    priority.to_csv(output_dir / "problem3_review_priority.csv", index=False, encoding="utf-8-sig")
    for scenario_id, queue in queues.items():
        queue.to_csv(output_dir / f"problem3_review_queue_{scenario_id}.csv", index=False, encoding="utf-8-sig")


def _write_keyword_theme_tables(output_dir: Path, history_features: pd.DataFrame, new_features: pd.DataFrame) -> None:
    history_theme = _theme_distribution(history_features, "history_count")
    new_theme = _theme_distribution(new_features, "new_count")
    theme = history_theme.merge(new_theme, on="dominant_keyword_group", how="outer").fillna(0)
    theme["history_count"] = theme["history_count"].astype(int)
    theme["new_count"] = theme["new_count"].astype(int)
    theme = theme.sort_values("new_count", ascending=False)
    theme.to_csv(output_dir / "problem2_keyword_theme_distribution.csv", index=False, encoding="utf-8-sig")


def _theme_distribution(features: pd.DataFrame, count_name: str) -> pd.DataFrame:
    if features.empty or "dominant_keyword_group" not in features:
        return pd.DataFrame(columns=["dominant_keyword_group", count_name])
    return features.groupby("dominant_keyword_group").size().reset_index(name=count_name)


def _build_topic_summary(assignments: pd.DataFrame, topic_terms: dict[int, list[str]], features: pd.DataFrame) -> pd.DataFrame:
    merged = assignments.merge(
        features[["doc_id", "dataset", "extension", "dominant_keyword_group", *[f"kw_{key}" for key in KEYWORD_GROUPS]]],
        on=["doc_id", "dataset", "extension"],
        how="left",
    )
    rows: list[dict[str, object]] = []
    keyword_columns = [f"kw_{key}" for key in KEYWORD_GROUPS]
    for topic_id, group in merged.groupby("topic_id"):
        keyword_scores = group[keyword_columns].sum().sort_values(ascending=False)
        extension_counts = group["extension"].value_counts().head(4)
        rows.append(
            {
                "topic_id": int(topic_id),
                "history_count": int(len(group)),
                "suggested_label": _suggest_label(keyword_scores.index[0].replace("kw_", ""), topic_terms.get(int(topic_id), [])),
                "top_terms": " / ".join(topic_terms.get(int(topic_id), [])[:10]),
                "dominant_keyword_group": keyword_scores.index[0].replace("kw_", ""),
                "dominant_extensions": "; ".join(f"{ext}:{count}" for ext, count in extension_counts.items()),
            }
        )
    return pd.DataFrame(rows).sort_values("history_count", ascending=False)


def _suggest_label(keyword_group: str, terms: list[str]) -> str:
    labels = {
        "finance": "资金财政类",
        "urgency": "通知时效类",
        "policy": "政策制度类",
        "education": "教育教学类",
        "technology": "科技项目类",
        "government": "政务报告类",
        "health": "医疗卫生类",
        "environment": "生态环境类",
        "personnel": "人事管理类",
        "legal": "合同法务类",
    }
    return labels.get(keyword_group, "综合办公类") if terms else "低文本信息类"


def _build_run_summary(
    args: argparse.Namespace,
    history_records: list[DocumentRecord],
    new_file_records: list[DocumentRecord],
    dataset3_records: list[DocumentRecord],
    topic_summary: pd.DataFrame,
    classified: pd.DataFrame,
    priority: pd.DataFrame,
    queues: dict[str, pd.DataFrame],
    elapsed_seconds: float,
) -> dict[str, object]:
    return {
        "data_root": str(DATA_ROOT),
        "parameters": {
            "max_chars": args.max_chars,
            "max_file_mb": args.max_file_mb,
            "clusters": args.clusters,
        },
        "elapsed_seconds": round(elapsed_seconds, 3),
        "dataset_counts": {
            "dataset1_records": len(history_records),
            "dataset1_usable_text": len(_usable_text_records(history_records)),
            "dataset2_records": len(new_file_records),
            "dataset2_usable_text": len(_usable_text_records(new_file_records)),
            "dataset3_records": len(dataset3_records),
        },
        "status_counts": {
            "dataset1": _status_counts(history_records),
            "dataset2": _status_counts(new_file_records),
            "dataset3": _status_counts(dataset3_records),
        },
        "problem1_topics": len(topic_summary),
        "problem2_classified_records": len(classified),
        "problem2_ambiguous_records": int(classified["is_ambiguous"].sum()) if not classified.empty else 0,
        "problem3_manual_review_records": int(priority["needs_manual_review"].sum()) if not priority.empty else 0,
        "scenario_queue_sizes": {scenario_id: len(queue) for scenario_id, queue in queues.items()},
        "key_outputs": {
            "topic_summary": "problem1_topic_summary.csv",
            "new_classification": "problem2_new_classification.csv",
            "review_priority": "problem3_review_priority.csv",
            "markdown_report": "RESULT_SUMMARY.md",
            "charts": [
                "problem1_topic_distribution.png",
                "problem2_classification_distribution.png",
                "problem2_keyword_theme_distribution.png",
                "problem3_priority_distribution.png",
            ],
        },
    }


def _status_counts(records: list[DocumentRecord]) -> dict[str, int]:
    frame = pd.DataFrame({"status": [record.status for record in records]})
    return frame["status"].value_counts().to_dict()


def _write_markdown_report(output_dir: Path, summary: dict[str, object], topic_summary: pd.DataFrame, priority: pd.DataFrame) -> None:
    top_review_cols = [
        "doc_id",
        "dataset",
        "predicted_topic_id",
        "priority_score",
        "urgency_level",
        "risk_level",
        "review_level",
        "needs_manual_review",
    ]
    top_review = priority[top_review_cols].head(20) if not priority.empty else pd.DataFrame(columns=top_review_cols)
    lines = [
        "# B Problem Result Summary",
        "",
        "## Run Summary",
        "",
        f"- Data root: `{summary['data_root']}`",
        f"- Dataset counts: `{json.dumps(summary['dataset_counts'], ensure_ascii=False)}`",
        f"- Status counts: `{json.dumps(summary['status_counts'], ensure_ascii=False)}`",
        f"- Classified new records: `{summary['problem2_classified_records']}`",
        f"- Ambiguous records: `{summary['problem2_ambiguous_records']}`",
        f"- Manual-review candidates: `{summary['problem3_manual_review_records']}`",
        f"- Scenario queue sizes: `{json.dumps(summary['scenario_queue_sizes'], ensure_ascii=False)}`",
        "",
        "## Problem 1 Topics",
        "",
        _frame_to_markdown(topic_summary),
        "",
        "## Problem 3 Top Review Candidates",
        "",
        _frame_to_markdown(top_review),
        "",
    ]
    (output_dir / "RESULT_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def _frame_to_markdown(frame: pd.DataFrame, max_col_width: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    rows = []
    for _, row in frame.iterrows():
        rows.append([_markdown_cell(row[column], max_col_width=max_col_width) for column in columns])
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _markdown_cell(value: object, max_col_width: int) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.replace("\n", " ").replace("|", "/")
    if len(text) > max_col_width:
        text = text[: max_col_width - 3] + "..."
    return text


def _write_charts(output_dir: Path, topic_summary: pd.DataFrame, classified: pd.DataFrame, priority: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(10, 5))
    topic_summary.sort_values("topic_id").plot.bar(x="topic_id", y="history_count", ax=ax, legend=False, color="#4477AA")
    ax.set_title("Problem 1 Historical Topic Distribution")
    ax.set_xlabel("Topic ID")
    ax.set_ylabel("Historical records")
    fig.tight_layout()
    fig.savefig(output_dir / "problem1_topic_distribution.png", dpi=180)
    plt.close(fig)

    if not classified.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        classified["predicted_topic_id"].value_counts().sort_index().plot.bar(ax=ax, color="#66AA55")
        ax.set_title("Problem 2 New Data Classification Distribution")
        ax.set_xlabel("Predicted topic ID")
        ax.set_ylabel("New records")
        fig.tight_layout()
        fig.savefig(output_dir / "problem2_classification_distribution.png", dpi=180)
        plt.close(fig)

    theme_path = output_dir / "problem2_keyword_theme_distribution.csv"
    if theme_path.exists():
        theme = pd.read_csv(theme_path)
        fig, ax = plt.subplots(figsize=(11, 5))
        theme.sort_values("new_count", ascending=True).plot.barh(
            x="dominant_keyword_group",
            y="new_count",
            ax=ax,
            legend=False,
            color="#AA7744",
        )
        ax.set_title("Problem 2 New Data Keyword Theme Distribution")
        ax.set_xlabel("New records")
        ax.set_ylabel("Keyword theme")
        fig.tight_layout()
        fig.savefig(output_dir / "problem2_keyword_theme_distribution.png", dpi=180)
        plt.close(fig)

    if not priority.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(priority["priority_score"], bins=20, color="#CC6677", edgecolor="white")
        ax.set_title("Problem 3 Manual Review Priority Score Distribution")
        ax.set_xlabel("Priority score")
        ax.set_ylabel("Records")
        fig.tight_layout()
        fig.savefig(output_dir / "problem3_priority_distribution.png", dpi=180)
        plt.close(fig)


if __name__ == "__main__":
    main()
