import requests
from datetime import datetime, timedelta
import json

def check_tpex_new():
    # 嘗試 2026/02/11 (週三) 這一天肯定有數據
    date_str = "115/02/11" 
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&d={date_str}&s=0,asc,0"
    
    print(f"URL: {url}")
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    data = r.json()
    
    print(f"Keys: {list(data.keys())}")
    
    if 'aaData' in data:
        print(f"Old format aaData found, count: {len(data['aaData'])}")
    else:
        print("No aaData")
        
    if 'tables' in data:
        print(f"New format tables found, count: {len(data.get('tables', []))}")
        if len(data['tables']) > 0:
            print(f"Table title: {data['tables'][0].get('title')}")
            rows = data['tables'][0].get('data', [])
            print(f"Data rows: {len(rows)}")
            if len(rows) > 0:
                print(f"First row: {rows[0]}")
    
check_tpex_new()
