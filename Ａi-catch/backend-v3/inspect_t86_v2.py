import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_twse_raw():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    date_str = "20260331" # Use an old but known date
    url = f'https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALLBUT0999&response=json'
    
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        data = resp.json()
        if 'data' in data and len(data['data']) > 0:
            print(f"Fields: {data['fields']}")
            # Find 2330
            for row in data['data']:
                if row[0].strip() == '2330':
                    print("Row for 2330:")
                    for i, (f, v) in enumerate(zip(data['fields'], row)):
                        print(f"{i}: {f} = {v}")
                    break
        else:
            print(f"No data: {data}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_twse_raw()
