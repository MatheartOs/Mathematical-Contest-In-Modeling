"""Recalibrate cleaning quality and manual-review allocation without rerunning OCR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.cleaning import (
    QUALITY_WEIGHTS,
    _write_resource_review_allocations,
    apply_resource_aware_review_policy,
    manual_review_priority,
)
from mcm_b.paths import ensure_output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleaning-dir", type=Path, default=ensure_output_root() / "cleaning_ocr_full")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    processed = args.cleaning_dir / "processed"
    index_path = processed / "document_index.csv"
    if not index_path.exists():
        raise FileNotFoundError(index_path)

    document_index = pd.read_csv(index_path)
    document_index = _recompute_quality(document_index)
    document_index = apply_resource_aware_review_policy(document_index)
    document_index.to_csv(index_path, index=False, encoding="utf-8-sig")
    _write_manual_lists(processed, document_index)
    _update_summary(args.cleaning_dir, document_index)
    print(
        json.dumps(
            {
                "cleaning_dir": str(args.cleaning_dir),
                "document_count": int(len(document_index)),
                "need_manual_check": int(document_index["need_manual_check"].sum()),
                "hard_manual_check": int(document_index["hard_manual_check"].sum()),
                "auto_archive": int((document_index["archive_decision"] == "auto_archive").sum()),
                "metadata_archive": int((document_index["archive_decision"] == "metadata_archive").sum()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _recompute_quality(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    scores: list[float] = []
    missing_rates: list[float] = []
    hard_flags: list[int] = []
    priorities: list[float] = []
    reasons: list[str] = []

    for _, row in output.iterrows():
        text = "" if pd.isna(row.get("clean_text")) else str(row.get("clean_text"))
        title = "" if pd.isna(row.get("title")) else str(row.get("title"))
        parse_method = "" if pd.isna(row.get("parse_method")) else str(row.get("parse_method"))
        parse_success = int(row.get("parse_success", 0) or 0)
        ocr_used = int(row.get("ocr_used", 0) or 0)
        ocr_confidence = float(row.get("ocr_confidence", 0) or 0)
        dataset_id = str(row.get("dataset_id", ""))
        flags = _business_flags_from_row(row)

        text_length = len(text)
        q_text = min(text_length / _expected_text_length(dataset_id, parse_method, ocr_used), 1.0) if text else 0.0
        q_ocr = 1.0 if not ocr_used and parse_success else ocr_confidence
        q_layout = _layout_score(parse_method)
        business_signal = any(flags.values())
        q_business = (
            0.45 * float(bool(title))
            + 0.35 * float(text_length >= _short_text_limit(dataset_id))
            + 0.20 * float(business_signal or _has_json_list(row.get("date_list")) or _has_json_list(row.get("amount_list")))
        )
        if parse_method.startswith("image_sidecar"):
            q_business = 0.40
        q_format = 1.0 if parse_success else 0.0
        score = round(
            QUALITY_WEIGHTS["text"] * q_text
            + QUALITY_WEIGHTS["ocr"] * q_ocr
            + QUALITY_WEIGHTS["layout"] * q_layout
            + QUALITY_WEIGHTS["business"] * q_business
            + QUALITY_WEIGHTS["format"] * q_format,
            4,
        )

        key_fields = [
            bool(text),
            bool(title),
            bool(business_signal),
            _has_json_list(row.get("date_list")) if flags.get("has_deadline", 0) else True,
            _has_json_list(row.get("amount_list")) if flags.get("has_money", 0) else True,
        ]
        reason_parts = _manual_reasons(row, score, text_length, dataset_id, parse_method, parse_success, ocr_used, ocr_confidence)
        hard = int(bool(reason_parts) and not parse_method.startswith("image_sidecar"))
        priority = manual_review_priority(
            parse_quality=score,
            ocr_used=ocr_used,
            ocr_confidence=ocr_confidence,
            parse_success=parse_success,
            text_length=text_length,
            flags=flags,
        )

        scores.append(score)
        missing_rates.append(round(key_fields.count(False) / len(key_fields), 4))
        hard_flags.append(hard)
        priorities.append(priority)
        reasons.append("; ".join(dict.fromkeys(reason_parts)))

    output["parse_quality"] = scores
    output["missing_rate"] = missing_rates
    output["hard_manual_check"] = hard_flags
    output["manual_review_priority"] = priorities
    output["manual_check_reason"] = reasons
    output["archive_decision"] = "pending_review_policy"
    output["resource_scenario"] = ""
    return output


def _business_flags_from_row(row: pd.Series) -> dict[str, int]:
    keys = [
        "has_notice",
        "has_meeting",
        "has_project",
        "has_money",
        "has_contract",
        "has_personnel",
        "has_deadline",
        "has_urgent",
    ]
    return {key: int(row.get(key, 0) or 0) for key in keys}


def _expected_text_length(dataset_id: str, parse_method: str, ocr_used: int) -> int:
    if dataset_id == "dataset3":
        return 120
    if ocr_used:
        return 300
    if parse_method == "excel_parse":
        return 250
    if parse_method.startswith("image_sidecar"):
        return 80
    return 600


def _short_text_limit(dataset_id: str) -> int:
    return 40 if dataset_id == "dataset3" else 80


def _layout_score(parse_method: str) -> float:
    if parse_method == "docx_parse":
        return 0.85
    if parse_method == "excel_parse":
        return 0.90
    if parse_method == "text_pdf":
        return 0.65
    if parse_method == "dataset3_row_parse":
        return 0.60
    if parse_method == "image_paddleocr":
        return 0.70
    if parse_method.startswith("txt_parse"):
        return 0.70
    if parse_method == "scanned_pdf_text_low":
        return 0.40
    return 0.20


def _manual_reasons(
    row: pd.Series,
    score: float,
    text_length: int,
    dataset_id: str,
    parse_method: str,
    parse_success: int,
    ocr_used: int,
    ocr_confidence: float,
) -> list[str]:
    reasons: list[str] = []
    sidecar = parse_method.startswith("image_sidecar")
    error = "" if pd.isna(row.get("error_message")) else str(row.get("error_message"))
    if parse_method in {"scanned_pdf_ocr_pending", "metadata_only"}:
        reasons.append(error or parse_method)
    if parse_success == 0 and not sidecar:
        reasons.append("parse_failed")
    if text_length < _short_text_limit(dataset_id) and not sidecar:
        reasons.append("text_too_short")
    if ocr_used and ocr_confidence < 0.75:
        reasons.append("ocr_confidence_below_0.75")
    if score < 0.45 and not sidecar:
        reasons.append("parse_quality_below_0.45")
    if sidecar:
        reasons.append("image_sidecar_metadata_only")
    return reasons


def _has_json_list(value: object) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip()
    return text not in {"", "[]", "null", "None"}


def _write_manual_lists(processed: Path, document_index: pd.DataFrame) -> None:
    columns = [
        "file_id",
        "dataset_id",
        "file_name",
        "file_type",
        "parse_method",
        "parse_quality",
        "manual_review_priority",
        "hard_manual_check",
        "archive_decision",
        "resource_scenario",
        "manual_check_reason",
        "file_path",
    ]
    columns = [column for column in columns if column in document_index.columns]
    document_index[document_index["need_manual_check"] == 1][columns].to_csv(
        processed / "manual_check_list.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _write_resource_review_allocations(processed, document_index)


def _update_summary(cleaning_dir: Path, document_index: pd.DataFrame) -> None:
    summary_path = cleaning_dir / "cleaning_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    summary["document_count"] = int(len(document_index))
    summary["need_manual_check"] = int(document_index["need_manual_check"].sum())
    summary["hard_manual_check"] = int(document_index["hard_manual_check"].sum())
    summary["auto_archive_count"] = int((document_index["archive_decision"] == "auto_archive").sum())
    summary["metadata_archive_count"] = int((document_index["archive_decision"] == "metadata_archive").sum())
    scenario_sizes = {}
    for scenario in ("S1", "S2", "S3"):
        path = cleaning_dir / "processed" / f"manual_check_list_{scenario}.csv"
        if path.exists():
            scenario_sizes[scenario] = int(len(pd.read_csv(path)))
    summary["resource_aware_manual_review"] = {
        "baseline_scenario": "S1",
        "minutes_per_review": 18,
        "scenario_queue_sizes": scenario_sizes,
        "policy": "hard quality failures first; remaining capacity filled by manual_review_priority",
    }
    summary.setdefault("deliverables", {})
    summary["deliverables"].update(
        {
            "manual_check_list_S1": "processed/manual_check_list_S1.csv",
            "manual_check_list_S2": "processed/manual_check_list_S2.csv",
            "manual_check_list_S3": "processed/manual_check_list_S3.csv",
        }
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
