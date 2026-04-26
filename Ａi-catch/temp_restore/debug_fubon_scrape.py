
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_fubon(stock_code):
    print(f"\n🕷️ 爬取富邦頁面 ({stock_code})...")
    
    urls = [
        f"https://www.fbs.com.tw/stock/{stock_code}",
        f"https://www.fubon.com/stock/{stock_code}", # 可能是另一個域名
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    for url in urls:
        print(f"嘗試 URL: {url}")
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=10)
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 嘗試 1: Title (如 "2330 台積電 - 個股資訊 | 富邦證券")
                title = soup.title.string if soup.title else ""
                print(f"Title: {title}")
                
                # 嘗試 2: 查找可能的 h1 或特定 class
                h1 = soup.find('h1')
                print(f"H1: {h1.text.strip() if h1 else 'None'}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    scrape_fubon("2330")
    scrape_fubon("5521")
