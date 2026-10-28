"""
抓取广州白云站 (NOAA ISD, USAF 592870 / 站号 59287099999) 的逐小时实测数据
数据源: NCEI global-hourly 数据访问服务
解析: 气温(TMP) / 降水(AA1) / 海平面气压(SLP) / 站压(可选)
输出: gz_baiyun_isd.csv
"""
import argparse
import datetime as dt
import io
import sys

import pandas as pd
import requests

STATION = "59287099999"  # 广州白云
BASE = "https://www.ncei.noaa.gov/access/services/data/v1"


def fetch(start: str, end: str) -> pd.DataFrame:
    params = {
        "dataset": "global-hourly",
        "stations": STATION,
        "startDate": start,
        "endDate": end,
        "format": "csv",
        # 只取需要的字段, 减小体积
        "dataTypes": "TMP,SLP,AA1,DEW",
        "units": "metric",
    }
    print(f"请求白云站 {start} ~ {end} ...", flush=True)
    r = requests.get(BASE, params=params, timeout=180)
    r.raise_for_status()
    if not r.text.strip():
        print("返回为空,可能该时段暂无数据。", file=sys.stderr)
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(r.text), dtype=str)


def parse_tmp(v):
    # 格式 "+0230,1" => 23.0 ℃ (已按 metric 返回, 仍是 0.1℃ scaled? NCEI metric 直接给℃)
    if not isinstance(v, str) or v == "":
        return None
    val = v.split(",")[0]
    try:
        x = float(val)
    except ValueError:
        return None
    if abs(x) >= 999:
        return None
    # ISD 原始 TMP 以 0.1℃ 存储; metric 模式下服务已转换为℃, 但部分仍为 scaled, 统一判断
    return x if abs(x) < 100 else x / 10.0


def parse_slp(v):
    # 海平面气压, hPa (scaled 0.1), 99999=缺测
    if not isinstance(v, str) or v == "":
        return None
    val = v.split(",")[0]
    try:
        x = float(val)
    except ValueError:
        return None
    if x >= 9999:
        return None
    return x if x > 800 else x / 10.0


def parse_precip(v):
    # AA1: 周期(小时),降水量(mm scaled 0.1),条件,质量
    if not isinstance(v, str) or v == "":
        return (None, None)
    parts = v.split(",")
    if len(parts) < 2:
        return (None, None)
    try:
        period = float(parts[0])
        depth = float(parts[1])
    except ValueError:
        return (None, None)
    if depth >= 9999:
        return (period, None)
    return (period, depth / 10.0)


def main():
    today = dt.date.today()
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-10-19")
    parser.add_argument("--end", default=today.isoformat())
    args = parser.parse_args()

    raw = fetch(args.start, args.end)
    if raw.empty:
        sys.exit(0)

    out = pd.DataFrame()
    out["datetime_utc"] = raw["DATE"]
    out["temp_C"] = raw.get("TMP").map(parse_tmp) if "TMP" in raw else None
    out["pressure_msl_hPa"] = raw.get("SLP").map(parse_slp) if "SLP" in raw else None
    if "AA1" in raw:
        pp = raw["AA1"].map(parse_precip)
        out["precip_period_h"] = [p[0] for p in pp]
        out["precip_mm"] = [p[1] for p in pp]
    out["dew_C"] = raw.get("DEW").map(parse_tmp) if "DEW" in raw else None

    out.to_csv("gz_baiyun_isd.csv", index=False, encoding="utf-8-sig")
    print(f"\n完成! {len(out)} 行 -> gz_baiyun_isd.csv")
    print("\n预览:")
    print(out.head(15).to_string(index=False))
    print(f"\n时间范围(UTC): {out['datetime_utc'].min()}  ~  {out['datetime_utc'].max()}")


if __name__ == "__main__":
    main()
