#!/usr/bin/env python3
"""
将data目录下的文件按类型分到不同子目录
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def main():
    data_dir = config.DATA_DIR

    for ext, target in config.EXT_TO_DIR.items():
        target_dir = os.path.join(data_dir, target)
        os.makedirs(target_dir, exist_ok=True)

    moved_count = 0
    for filename in os.listdir(data_dir):
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext in config.EXT_TO_DIR:
            target_dir = os.path.join(data_dir, config.EXT_TO_DIR[ext])
            shutil.move(filepath, os.path.join(target_dir, filename))
            print(f"Moved: {filename} -> {config.EXT_TO_DIR[ext]}/")
            moved_count += 1

    print(f"\n完成，共移动 {moved_count} 个文件。")

if __name__ == "__main__":
    main()
