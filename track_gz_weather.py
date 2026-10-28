"""
广州白云实时天气跟踪
数据源: Open-Meteo Forecast API (无需密钥)
坐标对齐 NOAA ISD 白云站: 23.39N, 113.30E

每次运行:
  1) 抓当前实况, 追加一行到 gz_current_log.csv (可重复运行, 自动去重)
  2) 导出今天 00:00 到现在的逐小时数据到 gz_today_hourly.csv

建议: 配合定时任务(如每小时 cron)运行, 即可连续跟踪。
"""
import csv
import datetime as dt
import os

import pandas as pd
import requests

LATITUDE = 23.39
LONGITUDE = 113.30
TIMEZONE = "Asia/Shanghai"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CURRENT_LOG = "gz_current_log.csv"
TODAY_HOURLY = "gz_today_hourly.csv"

CURRENT_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "pressure_msl",
    "weather_code",
    "wind_speed_10m",
]
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "pressure_msl",
    "weather_code",
    "wind_speed_10m",
]

# WMO 天气代码简要中文说明
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


def fetch():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ",".join(CURRENT_VARS),
        "hourly": ",".join(HOURLY_VARS),
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

    # 去重: 若同一 current time 已记录则跳过
    existing = set()
    if os.path.exists(CURRENT_LOG):
        with open(CURRENT_LOG, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                existing.add(r["time"])

    write_header = not os.path.exists(CURRENT_LOG)
    if row["time"] in existing:
        print(f"当前时刻 {row['time']} 已存在, 跳过追加。")
    else:
        with open(CURRENT_LOG, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if write_header:
                w.writeheader()
            w.writerow(row)
        print(f"已追加实况 {row['time']} -> {CURRENT_LOG}")
    return row


def export_today(data: dict):
    h = data["hourly"]
    df = pd.DataFrame(h)
    today = dt.date.today().isoformat()
    # 只保留今天、且时间不晚于当前的行
    now = data["current"]["time"]
    df = df[df["time"].str.startswith(today)]
    df = df[df["time"] <= now]
    df = df.rename(columns={
        "time": "datetime",
        "temperature_2m": "temp_C",
        "relative_humidity_2m": "humidity_%",
        "precipitation": "precip_mm",
        "surface_pressure": "surface_pressure_hPa",
        "pressure_msl": "pressure_msl_hPa",
        "weather_code": "weather_code",
        "wind_speed_10m": "wind_kmh",
    })
    df["weather"] = df["weather_code"].map(lambda c: WMO.get(c, c))
    df.to_csv(TODAY_HOURLY, index=False, encoding="utf-8-sig")
    print(f"已导出今日逐小时 {len(df)} 行 -> {TODAY_HOURLY}")
    return df


def main():
    data = fetch()
    print("=== 广州白云 当前实况 ===")
    row = append_current(data)
    for k, v in row.items():
        print(f"  {k}: {v}")
    print()
    df = export_today(data)
    if len(df):
        print("\n今日逐小时预览:")
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
