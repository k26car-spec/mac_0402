#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旺宏 (2337) 法人買賣超數據驗證工具
從台灣證交所 (TWSE) 直接抓取真實數據
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time

# 股票代碼
STOCK_CODE = "2337"  # 旺宏
STOCK_NAME = "旺宏"

def fetch_twse_institutional_data(date_str):
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALLBUT0999"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.twse.com.tw/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30, verify=False)
        if resp.status_code != 200: return None
        data = resp.json()
        if data.get("stat") != "OK" or not data.get("data"): return None
        for row in data["data"]:
            if len(row) >= 7 and row[0].strip() == STOCK_CODE:
                return {
                    "date": date_str,
                    "code": row[0],
                    "name": row[1],
                    "foreign": int(row[4].replace(",", "")) // 1000 if row[4] else 0,
                    "trust": int(row[10].replace(",", "")) // 1000 if row[10] else 0,
                    "dealer": int(row[11].replace(",", "")) // 1000 if row[11] else 0,
                    "total": int(row[18].replace(",", "")) // 1000 if row[18] else 0
                }
        return None
    except Exception as e:
        print(f"  抓取 {date_str} 錯誤: {e}")
        return None

def get_trading_days(end_date, days_count):
    dates = []
    current = end_date
    count = 0
    while count < days_count + 10:
        if current.weekday() < 5:
            dates.append(current.strftime("%Y%m%d"))
            count += 1
        current -= timedelta(days=1)
    return dates[::-1]

def aggregate_period_data(daily_data, days):
    if not daily_data or len(daily_data) < days:
        return {"foreign": 0, "trust": 0, "dealer": 0, "total": 0}
    recent = daily_data[-days:]
    foreign = sum(d["foreign"] for d in recent)
    trust = sum(d["trust"] for d in recent)
    dealer = sum(d["dealer"] for d in recent)
    total = sum(d["total"] for d in recent)
    return {"foreign": foreign, "trust": trust, "dealer": dealer, "total": total}

def main():
    end_date = datetime.now()
    trading_dates = get_trading_days(end_date, 60)
    print(f"📅 抓取區間: {trading_dates[0]} ~ {trading_dates[-1]}")
    daily_data = []
    
    # We will test against the last 5 days just to quickly verify if TWSE is blocking us.
    for i, date_str in enumerate(trading_dates[-5:]):
        print(f"  進度: {date_str}")
        data = fetch_twse_institutional_data(date_str)
        if data:
            daily_data.append(data)
        time.sleep(1)
        
    print(daily_data)

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
