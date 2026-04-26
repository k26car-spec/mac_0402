import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_tpex_raw():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    date_str = "115/03/31" # ROC Date for March 29, 2024 (a Friday)
    url = 'https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php'
    params = {'l': 'zh-tw', 'd': date_str, 'se': 'EW', 't': 'D'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, verify=False, timeout=10)
        data = resp.json()
        print(f"TPEx Header: {data.get('reportTitle', 'No Title')}")
        
        table_data = []
        if 'aaData' in data:
            table_data = data['aaData']
        elif 'tables' in data and len(data['tables']) > 0:
            table_data = data['tables'][0].get('data', [])
            
        if table_data:
            # Find 6488
            for row in table_data:
                if str(row[0]).strip() == '6488':
                    print("Row for 6488:")
                    for i, v in enumerate(row):
                        print(f"{i}: {v}")
                    break
        else:
            print(f"No table data: {data}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tpex_raw()
