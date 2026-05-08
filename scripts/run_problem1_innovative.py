"""Run Problem 1 with heterogeneous graph propagation and c-TF-IDF labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.paths import ensure_output_root
from mcm_b.problem1_innovative import run_problem1_graph_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleaning-dir", type=Path, default=ensure_output_root() / "cleaning_ocr_full")
    parser.add_argument("--output-dir", type=Path, default=ensure_output_root() / "problem1_innovative")
    parser.add_argument("--clusters", type=int, default=10)
    parser.add_argument("--max-terms", type=int, default=2500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index_path = args.cleaning_dir / "processed" / "document_index.csv"
    document_index = pd.read_csv(index_path)

    result = run_problem1_graph_model(document_index, n_clusters=args.clusters, max_terms=args.max_terms)
    result.assignments.to_csv(args.output_dir / "problem1_graph_topic_assignments.csv", index=False, encoding="utf-8-sig")
    result.topic_summary.to_csv(args.output_dir / "problem1_graph_topic_summary.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "problem1_graph_topic_summary.md").write_text(
        _frame_to_markdown(result.topic_summary),
        encoding="utf-8",
    )
    metrics = {
        **result.metrics,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "cleaning_dir": str(args.cleaning_dir),
        "output_dir": str(args.output_dir),
        "key_outputs": {
            "assignments": "problem1_graph_topic_assignments.csv",
            "topic_summary": "problem1_graph_topic_summary.csv",
            "topic_summary_md": "problem1_graph_topic_summary.md",
        },
    }
    (args.output_dir / "problem1_graph_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def _frame_to_markdown(frame: pd.DataFrame, max_col_width: int = 90) -> str:
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
            text = text.replace("\n", " ").replace("|", "/")
            if len(text) > max_col_width:
                text = text[: max_col_width - 3] + "..."
            cells.append(text)
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows])


if __name__ == "__main__":
    main()
