"""预先按天生成心情记录空 CSV (仅含表头), 便于页面上每天都能直接填写。

已有数据的文件不会被覆盖。

用法:
  python init_mood_files.py                      # 从今天起 6 个月(默认)
  python init_mood_files.py --months 3           # 从今天起 3 个月
  python init_mood_files.py --start 2026-10-28 --end 2027-04-28
"""
import argparse
import calendar
import datetime as dt
import os

DATA_DIR = "data"
FIELDS = ["datetime", "mood", "note"]


def add_months(d: dt.date, months: int) -> dt.date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def gen(start: dt.date, end: dt.date) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    created = skipped = 0
    d = start
    while d <= end:
        path = os.path.join(DATA_DIR, f"mood_{d.isoformat()}.csv")
        if os.path.exists(path):
            skipped += 1
        else:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(",".join(FIELDS) + "\n")
            created += 1
        d += dt.timedelta(days=1)
    print(f"新建 {created} 个 / 跳过(已存在) {skipped} 个, 目录 {DATA_DIR}/")


def main() -> None:
    today = dt.date.today()
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=6, help="从今天起几个月(默认 6)")
    ap.add_argument("--start", help="开始日期 YYYY-MM-DD, 默认今天")
    ap.add_argument("--end", help="结束日期 YYYY-MM-DD, 默认 今天+months")
    a = ap.parse_args()

    start = dt.date.fromisoformat(a.start) if a.start else today
    end = dt.date.fromisoformat(a.end) if a.end else add_months(today, a.months)
    if end < start:
        raise SystemExit("结束日期早于开始日期")

    print(f"生成范围: {start} ~ {end} (共 {(end - start).days + 1} 天)")
    gen(start, end)


if __name__ == "__main__":
    main()
