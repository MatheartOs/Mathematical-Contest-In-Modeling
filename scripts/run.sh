#!/bin/bash
# 一键运行数据预处理脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

echo "=== 1. 按类型分类文件 ==="
python3 scripts/split_by_type.py

echo ""
echo "=== 2. 下载txt中的jpg图片 ==="
python3 scripts/download_images.py

echo ""
echo "全部完成。"