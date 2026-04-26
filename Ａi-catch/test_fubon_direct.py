"""
簡單測試 - 直接查看富邦網頁內容
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime

print("=" * 80)
print("🔍 測試富邦證券網頁訪問")
print("=" * 80)

# 測試URL
url = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"

# 使用當天日期（重要！）
today = datetime.now().strftime('%Y-%m-%d')

params = {
    'a': '9600',  # 富邦新店
    'b': '9600',
    'c': 'E',
    'e': today,   # 開始日期：今天
    'f': today    # 結束日期：今天
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
}

print(f"\n📊 請求URL: {url}")
print(f"📊 參數: {params}")
print(f"📅 使用日期: {today}")

try:
    response = requests.get(url, params=params, headers=headers, timeout=15)
    
    print(f"\n✅ 狀態碼: {response.status_code}")
    print(f"✅ 編碼: {response.encoding}")
    print(f"✅ 內容長度: {len(response.text)} 字元")
    
    # 嘗試不同編碼
    for encoding in ['big5', 'utf-8', 'gb2312']:
        try:
            response.encoding = encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找表格
            tables = soup.find_all('table')
            
            print(f"\n【編碼: {encoding}】")
            print(f"  找到 {len(tables)} 個表格")
            
            if tables:
                # 顯示第一個表格的結構
                first_table = tables[0]
                rows = first_table.find_all('tr')
                print(f"  第一個表格有 {len(rows)} 行")
                
                if rows:
                    print(f"\n  前3行內容:")
                    for i, row in enumerate(rows[:3]):
                        cols = row.find_all(['td', 'th'])
                        print(f"    第{i+1}行: {len(cols)} 欄")
                        if cols:
                            texts = [col.get_text(strip=True)[:20] for col in cols[:5]]
                            print(f"      內容: {texts}")
        except Exception as e:
            print(f"  ❌ {encoding} 編碼失敗: {e}")
    
    # 保存HTML
    filename = f'fubon_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print(f"\n✅ HTML已保存到: {filename}")
    print(f"   請手動檢查此文件以了解實際的HTML結構")
    
    # 顯示HTML片段
    print(f"\n📄 HTML前500字元:")
    print("-" * 80)
    print(response.text[:500])
    print("-" * 80)
    
except Exception as e:
    print(f"\n❌ 請求失敗: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("測試完成")
print("=" * 80)
