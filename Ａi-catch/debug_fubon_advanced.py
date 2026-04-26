
import requests
import urllib3
import json

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_fubon_advanced(stock_code):
    print(f"\n🔍 深入測試富邦 API ({stock_code})...")
    
    # 基本 URL
    url = f"https://www.fbs.com.tw/TradeRD/rest/api/stock/info/{stock_code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.fbs.com.tw/',  # 加上 Referer
        'Origin': 'https://www.fbs.com.tw',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        # 1. 嘗試直接請求 (帶完整 Headers)
        print("1️⃣  嘗試標準請求 (帶 Referer)...")
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"✅ 成功! 數據: {json.dumps(data, ensure_ascii=False)[:100]}...")
                return
            except json.JSONDecodeError:
                print(f"❌ 返回不是 JSON: {resp.text[:100]}...")
        else:
            print(f"❌ 狀態碼: {resp.status_code}")

    except Exception as e:
        print(f"❌ 錯誤: {e}")

    # 2. 嘗試先訪問主頁獲取 Cookie
    try:
        print("\n2️⃣  嘗試先訪問主頁獲取 Session/Cookie...")
        session = requests.Session()
        session.headers.update(headers)
        
        # 訪問主頁
        session.get("https://www.fbs.com.tw/", verify=False)
        
        # 再請求 API
        resp = session.get(url, verify=False)
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"✅ 成功 (使用 Session)! 數據: {json.dumps(data, ensure_ascii=False)[:100]}...")
                return
            except:
                print(f"❌ 返回不是 JSON")
        else:
            print(f"❌ 狀態碼: {resp.status_code}")

    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    test_fubon_advanced("2330")
    test_fubon_advanced("5521")
