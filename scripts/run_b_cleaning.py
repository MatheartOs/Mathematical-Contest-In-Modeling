"""Run the document cleaning workflow described in the latest docs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.cleaning import clean_all_documents, write_cleaning_outputs
from mcm_b.paths import ensure_output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ensure_output_root() / "cleaning_v1")
    parser.add_argument("--max-chars", type=int, default=30_000)
    parser.add_argument("--max-file-mb", type=float, default=50.0)
    parser.add_argument("--dataset1-limit", type=int, default=0)
    parser.add_argument("--dataset2-limit", type=int, default=0)
    parser.add_argument("--dataset3-limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = perf_counter()
    limits = {
        "dataset1": args.dataset1_limit,
        "dataset2": args.dataset2_limit,
        "dataset3": args.dataset3_limit,
    }
    limits = {key: value for key, value in limits.items() if value}
    document_index, blocks, manifest, parse_log, errors = clean_all_documents(
        max_chars=args.max_chars,
        max_file_mb=args.max_file_mb,
        limits=limits,
    )
    write_cleaning_outputs(args.output_dir, document_index, blocks, manifest, parse_log, errors)
    summary = {
        "output_dir": str(args.output_dir),
        "elapsed_seconds": round(perf_counter() - started, 3),
        "document_count": int(len(document_index)),
        "block_count": int(len(blocks)),
        "need_manual_check": int(document_index["need_manual_check"].sum()) if not document_index.empty else 0,
        "parse_success_count": int(document_index["parse_success"].sum()) if not document_index.empty else 0,
        "deliverables": {
            "file_manifest": "processed/file_manifest.csv",
            "document_index": "processed/document_index.csv",
            "document_blocks": "processed/document_blocks.jsonl",
            "parse_log": "logs/parse_log.csv",
            "ocr_log": "logs/ocr_log.csv",
            "error_log": "logs/error_log.txt",
            "manual_check_list": "processed/manual_check_list.csv",
            "business_dictionary": "processed/business_dictionary.json",
        },
    }
    (args.output_dir / "cleaning_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
