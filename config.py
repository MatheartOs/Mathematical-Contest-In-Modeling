#!/usr/bin/env python3
"""
配置文件 - 统一管理数据集路径和参数
"""
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据集路径
DATA_DIR = os.path.join(BASE_DIR, "data1")

# 子目录配置
SUBDIRS = {
    "pdf": "pdf",
    "txt": "txt",
    "jpg": "jpg",
    "png": "jpg",
    "docx": "docx",
    "xlsx": "xlsx",
}

# 文件扩展名映射（key: 原始扩展名，value: 目标目录）
EXT_TO_DIR = SUBDIRS

# 下载线程数
DOWNLOAD_WORKERS = 16

# 请求超时时间（秒）
REQUEST_TIMEOUT = 15

# User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 文本文件编码
TEXT_ENCODING = "utf-8"
