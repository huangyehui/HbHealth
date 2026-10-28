"""
抓取广州市历史气象数据(气温、降水、气压)
数据源: Open-Meteo Historical Weather API (免费, 无需密钥)
文档: https://open-meteo.com/en/docs/historical-weather-api

默认抓取范围: 2015-01-01 ~ 昨天
输出:
  - guangzhou_weather_daily.csv   日粒度(气温均/高/低、降水量、海平面气压均值)
  - guangzhou_weather_hourly.csv  小时粒度(气温、降水、地面/海平面气压)
"""
import argparse
import datetime as dt
import sys

import pandas as pd
import requests

# 广州市中心坐标
LATITUDE = 23.13
LONGITUDE = 113.26
TIMEZONE = "Asia/Shanghai"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARS = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "pressure_msl_mean",
]

HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "pressure_msl",
    "surface_pressure",
]


def fetch(start_date: str, end_date: str) -> dict:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_VARS),
        "hourly": ",".join(HOURLY_VARS),
        "timezone": TIMEZONE,
    }
    print(f"请求 {start_date} ~ {end_date} ...", flush=True)
    r = requests.get(ARCHIVE_URL, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def to_daily_df(data: dict) -> pd.DataFrame:
    d = data.get("daily", {})
    df = pd.DataFrame(d)
    df = df.rename(
        columns={
            "time": "date",
            "temperature_2m_mean": "temp_mean_C",
            "temperature_2m_max": "temp_max_C",
            "temperature_2m_min": "temp_min_C",
            "precipitation_sum": "precip_mm",
            "pressure_msl_mean": "pressure_msl_hPa",
        }
    )
    return df


def to_hourly_df(data: dict) -> pd.DataFrame:
    h = data.get("hourly", {})
    df = pd.DataFrame(h)
    df = df.rename(
        columns={
            "time": "datetime",
            "temperature_2m": "temp_C",
            "precipitation": "precip_mm",
            "pressure_msl": "pressure_msl_hPa",
            "surface_pressure": "surface_pressure_hPa",
        }
    )
    return df


def main():
    yesterday = dt.date.today() - dt.timedelta(days=1)
    parser = argparse.ArgumentParser(description="抓取广州历史气象数据")
    parser.add_argument("--start", default="2015-01-01", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=yesterday.isoformat(), help="结束日期 YYYY-MM-DD")
    args = parser.parse_args()

    try:
        data = fetch(args.start, args.end)
    except requests.HTTPError as e:
        print(f"请求失败: {e}\n响应: {e.response.text[:500]}", file=sys.stderr)
        sys.exit(1)

    daily = to_daily_df(data)
    hourly = to_hourly_df(data)

    daily.to_csv("guangzhou_weather_daily.csv", index=False, encoding="utf-8-sig")
    hourly.to_csv("guangzhou_weather_hourly.csv", index=False, encoding="utf-8-sig")

    print(f"\n完成!")
    print(f"日粒度:  {len(daily):>6} 行 -> guangzhou_weather_daily.csv")
    print(f"小时粒度: {len(hourly):>6} 行 -> guangzhou_weather_hourly.csv")
    print("\n日粒度预览:")
    print(daily.head().to_string(index=False))
    print("\n小时粒度预览:")
    print(hourly.head().to_string(index=False))


if __name__ == "__main__":
    main()
