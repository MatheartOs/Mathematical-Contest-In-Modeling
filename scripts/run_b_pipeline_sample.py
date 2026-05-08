"""Run the initial B problem modeling pipeline on small samples only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.features import build_feature_frame
from mcm_b.modeling import classify_records, fit_topic_model, save_topic_model
from mcm_b.paths import DATASET1_DIR, DATASET2_DIR, DATASET3_XLSX, DATASET4_XLSX, ensure_output_root
from mcm_b.readers import DocumentRecord, read_document
from mcm_b.risk import allocate_reviews_by_scenario, load_resource_scenarios, score_review_priority


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-sample-size", type=int, default=60)
    parser.add_argument("--new-file-sample-size", type=int, default=30)
    parser.add_argument("--dataset3-rows", type=int, default=30)
    parser.add_argument("--clusters", type=int, default=8)
    parser.add_argument("--max-chars", type=int, default=12_000)
    parser.add_argument("--output-dir", type=Path, default=ensure_output_root())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    history_records = _read_file_sample(
        DATASET1_DIR,
        dataset="dataset1",
        sample_size=args.history_sample_size,
        max_chars=args.max_chars,
    )
    new_file_records = _read_file_sample(
        DATASET2_DIR,
        dataset="dataset2",
        sample_size=args.new_file_sample_size,
        max_chars=args.max_chars,
    )
    dataset3_records = _read_dataset3_rows(args.dataset3_rows, args.max_chars)

    result = fit_topic_model(history_records, n_clusters=args.clusters)
    history_features = build_feature_frame(history_records)
    new_records = new_file_records + dataset3_records
    new_features = build_feature_frame(new_records)
    classified = classify_records(result, new_records)
    priority = score_review_priority(classified, new_features)
    scenarios = load_resource_scenarios(DATASET4_XLSX)
    queues = allocate_reviews_by_scenario(priority, scenarios)

    result.assignments.to_csv(args.output_dir / "sample_history_topic_assignments.csv", index=False, encoding="utf-8-sig")
    history_features.to_csv(args.output_dir / "sample_history_features.csv", index=False, encoding="utf-8-sig")
    new_features.to_csv(args.output_dir / "sample_new_features.csv", index=False, encoding="utf-8-sig")
    classified.to_csv(args.output_dir / "sample_new_classification.csv", index=False, encoding="utf-8-sig")
    priority.to_csv(args.output_dir / "sample_review_priority.csv", index=False, encoding="utf-8-sig")
    for scenario_id, queue in queues.items():
        queue.to_csv(args.output_dir / f"sample_review_queue_{scenario_id}.csv", index=False, encoding="utf-8-sig")
    save_topic_model(result, args.output_dir / "sample_topic_model.joblib")

    summary = {
        "history_records": len(history_records),
        "new_records": len(new_records),
        "clusters": args.clusters,
        "silhouette": result.silhouette,
        "topic_terms": result.topic_terms,
        "manual_review_count": int(priority["needs_manual_review"].sum()) if not priority.empty else 0,
        "scenario_queue_sizes": {scenario_id: len(queue) for scenario_id, queue in queues.items()},
    }
    (args.output_dir / "sample_pipeline_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _read_file_sample(directory: Path, dataset: str, sample_size: int, max_chars: int) -> list[DocumentRecord]:
    files = sorted(path for path in directory.iterdir() if path.is_file())
    return [read_document(path, dataset=dataset, max_chars=max_chars) for path in files[:sample_size]]


def _read_dataset3_rows(row_count: int, max_chars: int) -> list[DocumentRecord]:
    frame = pd.read_excel(DATASET3_XLSX, nrows=row_count)
    records: list[DocumentRecord] = []
    for _, row in frame.iterrows():
        doc_id = str(row.get("文件编号", ""))
        text = str(row.get("正文片段", ""))[:max_chars]
        time_info = row.get("时间信息", "")
        records.append(
            DocumentRecord(
                doc_id=doc_id,
                path=f"{DATASET3_XLSX}#{doc_id}",
                dataset="dataset3",
                extension=".xlsx-row",
                size_bytes=len(text.encode("utf-8")),
                text=text,
                status="ok",
                metadata={"time_info": str(time_info)},
            )
        )
    return records


if __name__ == "__main__":
    main()
