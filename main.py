#完成需求3:找共同空闲的时间
# -*- coding: utf-8 -*-
"""
读取多份课表 CSV（如 课表.csv、课表 2.csv），算出所有人在周一~周日的
"共同空闲时段"，按时长从长到短排序后在终端打印。

用法：
    python main.py                       # 自动读取脚本同目录下的所有 .csv
    python main.py 课表.csv "课表 2.csv"  # 也可以手动指定要参与比对的文件

规则：
  1. 每天可用时间为 DAY_START ~ DAY_END
  2. 先合并每个人的上课时间：两节课挨着、或间隔不超过 GAP 分钟，就视为
     连续的一整段，避免课间十分钟被算成一段"空闲"（碎片化）
  3. 个人空闲 = 可用时间 减去 合并后的上课时间
  4. 共同空闲 = 所有人个人空闲的"交集"，同一天取大家都没课的重叠部分
"""

import csv
import glob
import os
import sys

DAY_START = "08:00"  # 每天可用时间起点
DAY_END = "22:00"    # 每天可用时间终点
GAP = 15             # 课间阈值（分钟）：间隔 ≤ 它就当作连续的一整段

WEEK_ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
RANK_ICON = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]


def find_csv_files():
    """确定要读取的课表文件：命令行指定了就用指定的，否则扫描同目录所有 .csv。"""
    base = os.path.dirname(os.path.abspath(__file__))
    args = sys.argv[1:]
    if args:
        # 命令行给的路径：既支持绝对路径，也支持相对脚本目录/当前目录
        paths = []
        for a in args:
            p = a if os.path.isabs(a) else os.path.join(base, a)
            if not os.path.exists(p) and os.path.exists(a):
                p = a
            paths.append(p)
        return paths
    return sorted(glob.glob(os.path.join(base, "*.csv")))


def read_schedule(path):
    """读取 CSV，自动兼容中文编码（先试 utf-8-sig，失败再试 gbk）。"""
    for enc in ("utf-8-sig", "gbk"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f)), enc
        except UnicodeDecodeError:
            continue  # 当前编码读不了，换下一个
    raise RuntimeError("无法识别文件编码，请确认 %s 是 utf-8 或 gbk 编码" % path)


def to_min(t):
    """'9:00' -> 540。把时间转成分钟，方便比较和计算。"""
    h, m = str(t).strip().split(":")
    return int(h) * 60 + int(m)


def to_str(m):
    """540 -> '09:00'。把分钟转回时间字符串。"""
    return "%02d:%02d" % (m // 60, m % 60)


def fmt_dur(m):
    """90 -> '1 小时 30 分钟'；不足 1 小时只显示分钟。"""
    if m >= 60:
        return "%d 小时 %d 分钟" % (m // 60, m % 60)
    return "%d 分钟" % m


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


def person_free(by_day, start, end):
    """算出某个人一周七天各自的空闲段：{"星期一": [(s, e), ...], ...}"""
    result = {}
    for day in WEEK_ORDER:
        # 合并当天的课，并把超出可用范围的课程截断
        busy = [(max(s, start), min(e, end))
                for s, e in merge(by_day.get(day, []))
                if e > start and s < end]
        result[day] = free_slots(busy, start, end)
    return result


def intersect(a, b):
    """求两段区间列表的交集（两人共同有空的部分）。"""
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if e > s:
            out.append((s, e))
        # 谁结束得早，就推进谁
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def common_free(free_list):
    """把多个人的空闲段列表依次求交集，得到所有人的共同空闲。"""
    common = free_list[0]
    for nxt in free_list[1:]:
        common = intersect(common, nxt)
        if not common:   # 已经没有交集了，没必要继续算
            break
    return common


def load_people(paths, start, end):
    """读取每个人的课表，返回包含姓名/课程数/每天空闲段的列表。"""
    people = []
    for path in paths:
        rows, enc = read_schedule(path)
        by_day = {}
        for r in rows:
            day = (r.get("星期几") or "").strip()
            if day not in WEEK_ORDER:
                continue
            try:
                s, e = to_min(r["开始时间"]), to_min(r["结束时间"])
            except (KeyError, ValueError):
                continue
            if e <= s:      # 异常数据（结束早于开始）忽略
                continue
            by_day.setdefault(day, []).append((s, e))
        people.append({
            "name": os.path.splitext(os.path.basename(path))[0],
            "count": len(rows),
            "enc": enc,
            "free": person_free(by_day, start, end),
        })
    return people


def main():
    paths = find_csv_files()
    if not paths:
        print("没有找到任何课表 CSV 文件。")
        return
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print("以下文件不存在：%s" % "、".join(missing))
        return

    start, end = to_min(DAY_START), to_min(DAY_END)
    people = load_people(paths, start, end)

    line = "=" * 58
    print(line)
    print("  多人共同空闲时间（每天可用 %s - %s）" % (DAY_START, DAY_END))
    print(line)
    print("参与比对的课表（共 %d 人）：" % len(people))
    for p in people:
        print("  · %-12s %2d 门课   （%s）" % (p["name"], p["count"], p["enc"]))
    print(line)

    if len(people) < 2:
        print("\n（提示：只找到 1 份课表，以下结果即该课表本人的空闲时间）")

    best, skipped = [], []
    for day in WEEK_ORDER:                       # 严格按 周一 → 周日 顺序
        slots = common_free([p["free"][day] for p in people])
        if not slots:
            skipped.append(day)
            continue                             # 没有共同空闲 -> 自动跳过
        slots.sort(key=lambda x: (-(x[1] - x[0]), x[0]))   # 时长降序，同长则早的在前

        print("\n▶ %s" % day)
        print("-" * 58)
        print("   %-4s %-19s %s" % ("排名", "时间段", "时长"))
        for idx, (s, e) in enumerate(slots):
            icon = RANK_ICON[idx] if idx < len(RANK_ICON) else str(idx + 1)
            print("   %-4s %s - %s     %s"
                  % (icon, to_str(s), to_str(e), fmt_dur(e - s)))
        total = sum(e - s for s, e in slots)
        print("   %s 合计共同空闲 %s" % (" " * 4, fmt_dur(total)))
        best.append((day, slots[0], total))      # 记录当天的黄金时段

    print("\n" + line)
    if skipped:
        print("无共同空闲、已跳过的日期：%s" % "、".join(skipped))
    if best:
        best.sort(key=lambda x: -(x[1][1] - x[1][0]))   # 按黄金时段时长降序
        print("本周最佳时段：")
        for day, (s, e), _ in best[:3]:
            print("  · %s  %s - %s   （%s）" % (day, to_str(s), to_str(e), fmt_dur(e - s)))
    else:
        print("本周没有任何共同空闲时间。")
    print(line)


if __name__ == "__main__":
    main()
