
import requests
import certifi

def test_yahoo(stock_code):
    print(f"測試 {stock_code}相關API...")
    
    # 測試 1: Yahoo
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    params = {'symbols': f"{stock_code}.TW", 'fields': 'shortName'}
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, verify=certifi.where())
        print(f"Yahoo Status: {resp.status_code}")
        print(f"Yahoo Body: {resp.text[:100]}")
    except Exception as e:
        print(f"Yahoo Error: {e}")

    # 測試 2: 富邦 (不驗證 SSL)
    import urllib3
    urllib3.disable_warnings()
    url = f"https://www.fbs.com.tw/TradeRD/rest/api/stock/info/{stock_code}"
    try:
        resp = requests.get(url, headers=headers, verify=False)
        print(f"Fubon Status: {resp.status_code}")
        print(f"Fubon Body: {resp.text[:100]}")
    except Exception as e:
        print(f"Fubon Error: {e}")

    # 測試 3: TWSE MIS
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_code}.tw"
    try:
        resp = requests.get(url, verify=False)
        print(f"TWSE Status: {resp.status_code}")
        print(f"TWSE Body: {resp.text[:200]}")
    except Exception as e:
        print(f"TWSE Error: {e}")

if __name__ == "__main__":
    test_yahoo("2330")
    test_yahoo("5521")
