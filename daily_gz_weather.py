"""
每天定时抓取广州天气, 按日期保存到 data/ 目录。

抓取逻辑复用 track_gz_weather.py (Open-Meteo 实时实况 + 今日逐小时)。
每天在指定时间抓一次, 输出:
  data/gz_weather_YYYY-MM-DD.csv        当日逐小时数据
  data/gz_current_log.csv               每次实况追加(累计, 自动去重)

用法:
  python daily_gz_weather.py --at 08:00        # 每天 08:00 抓取(默认)
  python daily_gz_weather.py --at 20:30        # 自定义时间
  python daily_gz_weather.py --once            # 立即抓一次后退出(用于手动/外部cron)
"""
import argparse
import csv
import datetime as dt
import os
import sys
import time

import requests

LATITUDE = 23.39
LONGITUDE = 113.30
TIMEZONE = "Asia/Shanghai"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DATA_DIR = "data"
CURRENT_LOG = os.path.join(DATA_DIR, "gz_current_log.csv")

VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "pressure_msl",
    "weather_code",
    "wind_speed_10m",
]

WMO = {
    0: "晴", 1: "多云转晴", 2: "局部多云", 3: "阴",
    45: "雾", 48: "凇雾",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨(小)", 67: "冻雨(大)",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "小阵雨", 81: "中阵雨", 82: "强阵雨",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


def fetch() -> dict:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ",".join(VARS),
        "hourly": ",".join(VARS),
        "timezone": TIMEZONE,
        "forecast_days": 1,
        "past_days": 0,
    }
    r = requests.get(FORECAST_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def append_current(data: dict):
    cur = data["current"]
    row = {
        "time": cur["time"],
        "fetched_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "temp_C": cur.get("temperature_2m"),
        "humidity_%": cur.get("relative_humidity_2m"),
        "precip_mm": cur.get("precipitation"),
        "surface_pressure_hPa": cur.get("surface_pressure"),
        "pressure_msl_hPa": cur.get("pressure_msl"),
        "weather": WMO.get(cur.get("weather_code"), cur.get("weather_code")),
        "wind_kmh": cur.get("wind_speed_10m"),
    }
    existing = set()
    if os.path.exists(CURRENT_LOG):
        with open(CURRENT_LOG, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                existing.add(r["time"])
    write_header = not os.path.exists(CURRENT_LOG)
    if row["time"] in existing:
        print(f"实况 {row['time']} 已存在, 跳过追加。")
    else:
        with open(CURRENT_LOG, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if write_header:
                w.writeheader()
            w.writerow(row)
        print(f"已追加实况 {row['time']} -> {CURRENT_LOG}")
    return row


def save_today(data: dict):
    h = data["hourly"]
    today = dt.date.today().isoformat()
    now = data["current"]["time"]
    rows = []
    n = len(h["time"])
    for i in range(n):
        t = h["time"][i]
        if not t.startswith(today) or t > now:
            continue
        rec = {"time": t}
        for v in VARS:
            rec[v] = h[v][i]
        rec["weather"] = WMO.get(rec.get("weather_code"), rec.get("weather_code"))
        rows.append(rec)

    out_path = os.path.join(DATA_DIR, f"gz_weather_{today}.csv")
    fieldnames = ["time"] + VARS + ["weather"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"已保存当日逐小时 {len(rows)} 行 -> {out_path}")
    return out_path


def run_once():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] 开始抓取广州天气 ...")
    try:
        data = fetch()
    except requests.RequestException as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        return False
    append_current(data)
    save_today(data)
    print("完成。\n")
    return True


def seconds_until(hour: int, minute: int) -> float:
    now = dt.datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += dt.timedelta(days=1)
    return (target - now).total_seconds()


def parse_at(value: str):
    try:
        hh, mm = value.split(":")
        hour, minute = int(hh), int(mm)
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
        return hour, minute
    except ValueError:
        raise argparse.ArgumentTypeError("时间格式应为 HH:MM, 例如 08:00")


def main():
    parser = argparse.ArgumentParser(description="每天定时抓取广州天气")
    parser.add_argument("--at", type=parse_at, default="08:00",
                        help="每天抓取时间 HH:MM, 默认 08:00")
    parser.add_argument("--once", action="store_true",
                        help="立即抓取一次后退出(配合外部 cron 使用)")
    args = parser.parse_args()

    if args.once:
        ok = run_once()
        sys.exit(0 if ok else 1)

    hour, minute = args.at
    print(f"已启动: 每天 {hour:02d}:{minute:02d} 抓取广州天气, 保存到 {DATA_DIR}/")
    print("按 Ctrl+C 停止。\n")
    while True:
        wait = seconds_until(hour, minute)
        nxt = dt.datetime.now() + dt.timedelta(seconds=wait)
        print(f"下次抓取: {nxt:%Y-%m-%d %H:%M:%S} (等待 {wait/3600:.2f} 小时)")
        try:
            time.sleep(wait)
        except KeyboardInterrupt:
            print("\n已停止。")
            break
        run_once()


if __name__ == "__main__":
    main()
