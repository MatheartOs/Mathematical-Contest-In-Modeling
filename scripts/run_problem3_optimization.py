"""Run Problem 3 review priority and resource optimization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.paths import DATASET4_XLSX, ensure_output_root
from mcm_b.risk import load_resource_scenarios
from mcm_b.problem3_optimization import run_problem3_optimization


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleaning-dir", type=Path, default=ensure_output_root() / "cleaning_ocr_full")
    parser.add_argument("--problem2-dir", type=Path, default=ensure_output_root() / "problem2_transfer")
    parser.add_argument("--output-dir", type=Path, default=ensure_output_root() / "problem3_optimization")
    parser.add_argument("--dataset4", type=Path, default=DATASET4_XLSX)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    classification = pd.read_csv(args.problem2_dir / "problem2_transfer_classification.csv")
    document_index = pd.read_csv(args.cleaning_dir / "processed" / "document_index.csv")
    scenarios = load_resource_scenarios(args.dataset4)
    result = run_problem3_optimization(classification, document_index, scenarios, args.output_dir)
    summary = {
        **result.metrics,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "cleaning_dir": str(args.cleaning_dir),
        "problem2_dir": str(args.problem2_dir),
        "output_dir": str(args.output_dir),
        "key_outputs": {
            "priority": "problem3_risk_priority.csv",
            "level_summary": "problem3_level_summary.csv",
            "scenario_comparison": "problem3_scenario_comparison.csv",
            "special_focus": "problem3_special_focus.csv",
            "report": "problem3_optimization_report.md",
            "queues": [f"problem3_review_queue_{scenario_id}.csv" for scenario_id in result.scenario_queues],
            "charts": [
                "problem3_level_distribution.png",
                "problem3_scenario_comparison.png",
                "problem3_action_distribution.png",
                "problem3_review_queue_topic_distribution.png",
            ],
            "chart_data": [
                "problem3_level_distribution_plot_data.csv",
                "problem3_scenario_comparison_plot_data.csv",
                "problem3_action_distribution_plot_data.csv",
                "problem3_review_queue_topic_distribution_plot_data.csv",
            ],
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
