"""Lightweight B problem data inspection.

This script intentionally samples a tiny subset by default. Use it to validate
paths and readers before running any larger experiment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.features import build_feature_frame, summarize_topics_by_keywords
from mcm_b.paths import DATASET1_DIR, DATASET2_DIR, DATASET3_XLSX, DATASET4_XLSX, ensure_output_root
from mcm_b.readers import read_document
from mcm_b.risk import load_resource_scenarios


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-per-dataset", type=int, default=8)
    parser.add_argument("--dataset3-rows", type=int, default=12)
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--output-dir", type=Path, default=ensure_output_root())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for dataset, directory in [("dataset1", DATASET1_DIR), ("dataset2", DATASET2_DIR)]:
        files = sorted(path for path in directory.iterdir() if path.is_file())
        for path in files[: args.sample_per_dataset]:
            records.append(read_document(path, dataset=dataset, max_chars=args.max_chars))

    features = build_feature_frame(records)
    profile_csv = args.output_dir / "sample_profile.csv"
    features.to_csv(profile_csv, index=False, encoding="utf-8-sig")

    dataset3 = pd.read_excel(DATASET3_XLSX, nrows=args.dataset3_rows)
    dataset3_csv = args.output_dir / "dataset3_head.csv"
    dataset3.to_csv(dataset3_csv, index=False, encoding="utf-8-sig")

    scenarios = load_resource_scenarios(DATASET4_XLSX)
    scenarios_csv = args.output_dir / "resource_scenarios.csv"
    scenarios.to_csv(scenarios_csv, index=False, encoding="utf-8-sig")

    summary = {
        "sample_per_dataset": args.sample_per_dataset,
        "records_read": len(records),
        "status_counts": features["status"].value_counts().to_dict() if not features.empty else {},
        "extension_counts": features["extension"].value_counts().to_dict() if not features.empty else {},
        "keyword_summary": summarize_topics_by_keywords(records, top_n=20),
        "outputs": {
            "sample_profile": str(profile_csv),
            "dataset3_head": str(dataset3_csv),
            "resource_scenarios": str(scenarios_csv),
        },
    }
    summary_json = args.output_dir / "inspection_summary.json"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
