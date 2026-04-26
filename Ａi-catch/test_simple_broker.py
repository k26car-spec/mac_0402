#!/usr/bin/env python3
"""
簡單測試：直接使用 analyze_fubon_html.py 的邏輯測試富邦數據
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime, timedelta

# 測試日期：前天
test_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

print(f"🔍 測試日期: {test_date}")
print("="*80)

# 構建URL
url = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"
params = {
    'a': '9600',  # 富邦新店
    'b': '9600',
    'c': 'E',
    'e': test_date,
    'f': test_date
}

# 發送請求
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    response = requests.get(url, params=params, headers=headers, timeout=15)
    response.encoding = 'big5'
    
    print(f"✅ 狀態碼: {response.status_code}")
    
    # 解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    
    print(f"📋 找到 {len(tables)} 個表格")
    
    # 提取數據
    data_list = []
    
    for table in tables:
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            texts = [col.get_text(strip=True) for col in cols]
            
            if len(texts) >= 4:
                has_numbers = any(re.search(r'\d+', t) for t in texts)
                
                if has_numbers:
                    for i, text in enumerate(texts):
                        code_match = re.search(r'\b(\d{4,6})\b', text)
                        if code_match:
                            stock_code = code_match.group(1)
                            stock_name = text.replace(stock_code, '').strip()
                            
                            if i + 3 < len(texts):
                                try:
                                    buy = int(texts[i+1].replace(',', '').replace('-', '0'))
                                    sell = int(texts[i+2].replace(',', '').replace('-', '0'))
                                    net = int(texts[i+3].replace(',', '').replace('-', '0'))
                                    
                                    if buy > 0 or sell > 0 or net != 0:
                                        data_list.append({
                                            'stock_code': stock_code,
                                            'stock_name': stock_name or stock_code,
                                            'buy_count': buy,
                                            'sell_count': sell,
                                            'net_count': net
                                        })
                                        break
                                except:
                                    pass
    
    if data_list:
        df = pd.DataFrame(data_list)
        df = df[df['stock_code'].str.len() >= 4]
        df = df[(df['buy_count'] > 0) | (df['sell_count'] > 0)]
        df = df.drop_duplicates(subset=['stock_code'], keep='first')
        df = df.sort_values('net_count', ascending=False)
        
        print(f"\n✅ 成功提取 {len(df)} 筆數據")
        print("\n前20名買超股票:")
        print(df.head(20).to_string(index=False))
        
        # 保存
        output_file = f'test_broker_data_{test_date}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 數據已保存到: {output_file}")
        
    else:
        print("\n❌ 未能提取到數據")
        
except Exception as e:
    print(f"\n❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("測試完成")
