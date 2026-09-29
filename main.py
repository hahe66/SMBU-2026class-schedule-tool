# 要求2：算空闲时段完成
# -*- coding: utf-8 -*-
"""
读取 课表.csv，按周一~周日的顺序，打印每天的空闲时间段。

规则：
  1. 每天可用时间为 DAY_START ~ DAY_END
  2. 先把上课时间"合并"成整段：两节课只要挨着、或间隔不超过 GAP 分钟，
     就视为连续的一整段，避免课间十分钟被算成一段"空闲"（碎片化）
  3. 空闲 = 可用时间 减去 合并后的上课时间
"""

import csv
import os

CSV_FILE = "课表.csv"
DAY_START = "08:00"  # 每天可用时间起点
DAY_END = "22:00"    # 每天可用时间终点
GAP = 15             # 课间阈值（分钟）：间隔 ≤ 它就当作连续的一整段

WEEK_ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def read_schedule(path):
    """读取 CSV，自动兼容中文编码（先试 utf-8-sig，失败再试 gbk）。"""
    for enc in ("utf-8-sig", "gbk"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f)), enc
        except UnicodeDecodeError:
            continue  # 当前编码读不了，换下一个
    raise RuntimeError("无法识别文件编码，请确认文件是 utf-8 或 gbk 编码")


def to_min(t):
    """'9:00' -> 540。把时间转成分钟，方便比较和计算。"""
    h, m = t.strip().split(":")
    return int(h) * 60 + int(m)


def to_str(m):
    """540 -> '09:00'。把分钟转回时间字符串。"""
    return "%02d:%02d" % (m // 60, m % 60)


def merge(busy):
    """合并上课区间：重叠的、或间隔不超过 GAP 分钟的，都接成一段。"""
    out = []
    for s, e in sorted(busy):
        if out and s <= out[-1][1] + GAP:   # 和上一段挨着或间隔很小 -> 接上
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def free_slots(busy, start, end):
    """在 [start, end] 里挖掉 busy，返回剩下的空闲段。"""
    res, cur = [], start
    for s, e in busy:
        if s > cur:
            res.append((cur, s))   # 上课前的一段空档
        cur = max(cur, e)          # 跳过已占用时间
    if cur < end:
        res.append((cur, end))     # 最后一节课之后的空档
    return res


def main():
    # 让脚本在任何目录下运行都能找到同目录的 CSV
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CSV_FILE)
    rows, enc = read_schedule(path)
    print("（已按 %s 编码读取，共 %d 条课程）\n" % (enc, len(rows)))

    # 按星期分组：{ "星期一": [(开始分钟, 结束分钟), ...], ... }
    by_day = {}
    for r in rows:
        day = r["星期几"].strip()
        by_day.setdefault(day, []).append((to_min(r["开始时间"]), to_min(r["结束时间"])))

    start, end = to_min(DAY_START), to_min(DAY_END)

    print("=" * 46)
    print("  本周空闲时间（每天可用 %s - %s）" % (DAY_START, DAY_END))
    print("=" * 46)

    for day in WEEK_ORDER:  # 严格按 周一 → 周日 顺序
        # 合并当天的课，并把超出可用范围的课程截断
        busy = [(max(s, start), min(e, end))
                for s, e in merge(by_day.get(day, []))
                if e > start and s < end]

        print("\n▶ %s" % day)
        print("-" * 46)
        slots = free_slots(busy, start, end)
        if not slots:
            print("  全天满课，没有空闲")
        for s, e in slots:
            print("  %s - %s  （%d 分钟）" % (to_str(s), to_str(e), e - s))
        total = sum(e - s for s, e in slots)
        print("  合计空闲 %d 小时 %d 分钟" % (total // 60, total % 60))

    print("\n" + "=" * 46)


if __name__ == "__main__":
    main()

