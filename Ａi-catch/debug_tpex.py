import requests
from datetime import datetime, timedelta

def check_tpex():
    for days_ago in range(1, 4):
        target_date = datetime.now() - timedelta(days=days_ago)
        roc_year = target_date.year - 1911
        date_str = f"{roc_year}/{target_date.month:02d}/{target_date.day:02d}"
        
        url = f"https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php?l=zh-tw&d={date_str}&se=EW&s=0,asc,0"
        
        print(f"嘗試日期: {date_str}")
        print(f"URL: {url}")
        
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            print(f"Status: {r.status_code}")
            
            data = r.json()
            keys = list(data.keys())
            print(f"Keys: {keys}")
            
            if 'aaData' in data:
                count = len(data['aaData'])
                print(f"aaData Count: {count}")
                if count > 0:
                    print(f"First Row: {data['aaData'][0]}")
                    break
            else:
                print("No aaData found")
                
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 30)

check_tpex()
