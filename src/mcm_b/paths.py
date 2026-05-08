"""Path helpers for the B problem data layout."""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEST_ROOT = REPO_ROOT.parent

DEFAULT_DATA_ROOT = CONTEST_ROOT / "数模赛数据" / "B题数据集"
DATA_ROOT = Path(os.environ.get("MCM_B_DATA_ROOT", DEFAULT_DATA_ROOT)).resolve()

DATASET1_DIR = DATA_ROOT / "数据集1：历史真实文件数据"
DATASET2_DIR = DATA_ROOT / "数据集2：后续流入的半结构化记录数据"
DATASET3_XLSX = DATA_ROOT / "数据集3：后续流入的匿名原始文件数据.xlsx"
DATASET4_XLSX = DATA_ROOT / "数据集4：业务规则与资源约束表.xlsx"

OUTPUT_ROOT = REPO_ROOT / "outputs" / "b_problem"


def ensure_output_root() -> Path:
    """Create and return the B problem output directory."""

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    return OUTPUT_ROOT


def dataset_paths() -> dict[str, Path]:
    """Return canonical paths for the four official B problem datasets."""

    return {
        "dataset1": DATASET1_DIR,
        "dataset2": DATASET2_DIR,
        "dataset3": DATASET3_XLSX,
        "dataset4": DATASET4_XLSX,
    }
