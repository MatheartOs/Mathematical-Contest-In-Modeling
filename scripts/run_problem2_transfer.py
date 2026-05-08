"""Run Problem 2 graph-transfer classification and evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.paths import ensure_output_root
from mcm_b.problem2_transfer import run_problem2_transfer_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleaning-dir", type=Path, default=ensure_output_root() / "cleaning_ocr_full")
    parser.add_argument("--output-dir", type=Path, default=ensure_output_root() / "problem2_transfer")
    parser.add_argument("--clusters", type=int, default=10)
    parser.add_argument("--max-terms", type=int, default=2500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index_path = args.cleaning_dir / "processed" / "document_index.csv"
    document_index = pd.read_csv(index_path)

    result = run_problem2_transfer_model(
        document_index=document_index,
        output_dir=args.output_dir,
        n_clusters=args.clusters,
        max_terms=args.max_terms,
    )
    summary = {
        **result.metrics,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "cleaning_dir": str(args.cleaning_dir),
        "output_dir": str(args.output_dir),
        "key_outputs": {
            "classification": "problem2_transfer_classification.csv",
            "dataset_evaluation": "problem2_dataset_evaluation.csv",
            "topic_distribution": "problem2_topic_distribution.csv",
            "boundary_samples": "problem2_boundary_samples.csv",
            "report": "problem2_transfer_report.md",
            "charts": [
                "problem2_topic_distribution.png",
                "problem2_state_distribution.png",
                "problem2_ars_mii_scatter.png",
            ],
            "chart_data": [
                "problem2_topic_distribution_plot_data.csv",
                "problem2_state_distribution_plot_data.csv",
                "problem2_ars_mii_scatter_plot_data.csv",
            ],
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
