# -*- coding: utf-8 -*-
"""
读取 课表.csv，按“周一 ~ 周日”的顺序在终端打印本周课表视图。

CSV 表头：课程名,星期几,开始时间,结束时间
"""

import csv
import os

CSV_FILE = "课表.csv"

# 一周的显示顺序（用来给课程排序）
WEEK_ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def read_schedule(path):
    """读取 CSV 文件，自动兼容中文编码（先试 utf-8-sig，失败再试 gbk）。"""
    for enc in ("utf-8-sig", "gbk"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                # DictReader 会把每一行变成字典：{"课程名": ..., "星期几": ...}
                return list(csv.DictReader(f)), enc
        except UnicodeDecodeError:
            continue  # 用当前编码读失败，换下一个编码重试
    raise RuntimeError("无法识别文件编码，请确认文件是 utf-8 或 gbk 编码")


def to_minutes(t):
    """把 '9:00' 这种时间转成分钟数，方便排序。"""
    h, m = t.strip().split(":")
    return int(h) * 60 + int(m)


def main():
    # 让脚本无论从哪个目录运行，都能找到同目录下的 CSV
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CSV_FILE)

    rows, enc = read_schedule(path)
    print("（已按 %s 编码读取，共 %d 条课程）\n" % (enc, len(rows)))

    # 按星期分组：{ "星期一": [课程1, 课程2, ...], ... }
    by_day = {}
    for r in rows:
        day = r["星期几"].strip()
        by_day.setdefault(day, []).append(r)

    print("=" * 46)
    print("              本  周  课  表")
    print("=" * 46)

    for day in WEEK_ORDER:  # 严格按 周一 → 周日 顺序输出
        if day not in by_day:
            continue  # 这天没课就跳过

        print("\n▶ %s" % day)
        print("-" * 46)
        # 同一天内按开始时间从早到晚排序
        courses = sorted(by_day[day], key=lambda r: to_minutes(r["开始时间"]))
        for c in courses:
            time_range = "%s - %s" % (c["开始时间"].strip(), c["结束时间"].strip())
            print("  %-14s  %s" % (time_range, c["课程名"].strip()))

    print("\n" + "=" * 46)


if __name__ == "__main__":
    main()
