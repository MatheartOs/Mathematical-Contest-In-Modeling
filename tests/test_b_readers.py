from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcm_b.features import build_feature_frame
from mcm_b.readers import DocumentRecord, read_document
from mcm_b.cleaning import business_flags, extract_amounts, extract_dates, normalize_text


class BReaderTests(unittest.TestCase):
    def test_txt_reader_handles_utf8(self) -> None:
        path = Path("outputs") / "b_problem" / "unit_sample.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("科技金融扶持资金实施细则", encoding="utf-8")

        record = read_document(path, dataset="unit", max_chars=100)

        self.assertEqual(record.status, "ok")
        self.assertIn("科技金融", record.text)

    def test_feature_frame_has_keyword_groups(self) -> None:
        records = [
            DocumentRecord(
                doc_id="T1",
                path="memory",
                dataset="unit",
                extension=".txt",
                size_bytes=10,
                text="紧急通知：财政资金项目需要复核。",
                status="ok",
            )
        ]

        frame = build_feature_frame(records)

        self.assertGreater(frame.loc[0, "kw_urgency"], 0)
        self.assertGreater(frame.loc[0, "kw_finance"], 0)

    def test_cleaning_extracts_business_fields(self) -> None:
        text = normalize_text("请于2026年5月20日前提交项目经费预算3.5万元。")
        flags, _ = business_flags(text)

        self.assertIn("2026-05-20", extract_dates(text))
        self.assertIn(35000.0, extract_amounts(text))
        self.assertEqual(flags["has_deadline"], 1)
        self.assertEqual(flags["has_money"], 1)


if __name__ == "__main__":
    unittest.main()
