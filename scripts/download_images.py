#!/usr/bin/env python3
"""
从txt文件中提取下载URL，下载对应jpg图片并保存为同名jpg
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def extract_url(txt_path):
    """从txt文件中提取下载URL"""
    try:
        with open(txt_path, "r", encoding=config.TEXT_ENCODING) as f:
            content = f.read()
        match = re.search(r"下载URL[:：]\s*(https?://[^\s]+)", content)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"读取文件失败 {txt_path}: {e}")
    return None

def download_jpg(txt_filename):
    """下载对应jpg并保存为同名jpg"""
    txt_dir = os.path.join(config.DATA_DIR, "txt")
    txt_path = os.path.join(txt_dir, txt_filename)
    url = extract_url(txt_path)
    if not url:
        return None, None

    basename = os.path.splitext(txt_filename)[0]
    output_path = os.path.join(txt_dir, f"{basename}.jpg")

    if os.path.exists(output_path):
        return basename, "skipped"

    try:
        headers = {"User-Agent": config.USER_AGENT}
        response = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return basename, "success"
    except Exception as e:
        print(f"下载失败 {basename}: {e}")
        return basename, "failed"

def main():
    txt_dir = os.path.join(config.DATA_DIR, "txt")
    txt_files = [f for f in os.listdir(txt_dir) if f.endswith(".txt")]
    print(f"找到 {len(txt_files)} 个txt文件")

    success, failed, skipped = 0, 0, 0

    with ThreadPoolExecutor(max_workers=config.DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(download_jpg, f): f for f in txt_files}
        for future in tqdm(as_completed(futures), total=len(futures), desc="下载中"):
            basename, status = future.result()
            if status == "success":
                success += 1
            elif status == "failed":
                failed += 1
            elif status == "skipped":
                skipped += 1

    print(f"\n完成: 成功 {success}, 失败 {failed}, 跳过(已存在) {skipped}")

if __name__ == "__main__":
    main()
