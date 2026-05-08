"""Feature engineering for B problem documents."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import math
import re

import pandas as pd

from .readers import DocumentRecord, text_quality_score


KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    "finance": ("资金", "经费", "预算", "财政", "金融", "贷款", "收入", "支出", "采购", "招标"),
    "urgency": ("紧急", "立即", "尽快", "限期", "截止", "时效", "通知", "公示", "公告"),
    "policy": ("办法", "条例", "细则", "规定", "方案", "意见", "规划", "标准"),
    "education": ("课程", "教学", "学生", "学校", "教师", "培养", "毕业", "学科"),
    "technology": ("科技", "创新", "研发", "实验", "项目", "专利", "技术", "数据"),
    "government": ("人民政府", "部门", "委员会", "会议", "工作报告", "政务", "行政"),
    "health": ("卫生", "医疗", "医院", "健康", "疾病", "医保", "诊疗"),
    "environment": ("生态", "环境", "污染", "绿色", "低碳", "能源", "碳"),
    "personnel": ("招聘", "岗位", "人员", "干部", "任免", "考核", "培训"),
    "legal": ("合同", "协议", "法律", "责任", "权利", "义务", "诉讼"),
}


def build_feature_row(record: DocumentRecord) -> dict[str, object]:
    """Build interpretable metadata/text features for one document."""

    text = record.text or ""
    length = len(text)
    chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    digit_chars = sum(1 for char in text if char.isdigit())
    punctuation = sum(1 for char in text if re.match(r"\W", char, flags=re.UNICODE))

    row: dict[str, object] = {
        **asdict(record),
        "text_length": length,
        "text_quality": text_quality_score(text),
        "chinese_ratio": _safe_ratio(chinese_chars, length),
        "digit_ratio": _safe_ratio(digit_chars, length),
        "punctuation_ratio": _safe_ratio(punctuation, length),
        "log_size_bytes": math.log1p(record.size_bytes),
        "line_count": text.count("\n") + 1 if text else 0,
    }
    for group, keywords in KEYWORD_GROUPS.items():
        row[f"kw_{group}"] = sum(text.count(keyword) for keyword in keywords)
    return row


def build_feature_frame(records: list[DocumentRecord]) -> pd.DataFrame:
    """Convert document records into a modeling table."""

    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(build_feature_row(record) for record in records)
    frame["keyword_total"] = frame[[f"kw_{key}" for key in KEYWORD_GROUPS]].sum(axis=1)
    frame["dominant_keyword_group"] = frame.apply(_dominant_keyword_group, axis=1)
    return frame


def summarize_topics_by_keywords(records: list[DocumentRecord], top_n: int = 20) -> list[tuple[str, int]]:
    """Return a simple high-signal keyword list for exploratory reporting."""

    counter: Counter[str] = Counter()
    for record in records:
        text = record.text or ""
        for group, keywords in KEYWORD_GROUPS.items():
            for keyword in keywords:
                count = text.count(keyword)
                if count:
                    counter[f"{group}:{keyword}"] += count
    return counter.most_common(top_n)


def _dominant_keyword_group(row: pd.Series) -> str:
    scores = {group: row.get(f"kw_{group}", 0) for group in KEYWORD_GROUPS}
    group, score = max(scores.items(), key=lambda item: item[1])
    return group if score else "unknown"


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0
