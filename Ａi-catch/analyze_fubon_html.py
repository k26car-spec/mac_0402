"""
分析富邦HTML結構並提取券商數據
"""

from bs4 import BeautifulSoup
import pandas as pd
import re
from pathlib import Path

print("=" * 80)
print("📊 分析富邦HTML結構")
print("=" * 80)

html_file = 'fubon_test_20260101_101452.html'

try:
    # 嘗試不同編碼
    for encoding in ['utf-8', 'big5', 'gb18030']:
        try:
            with open(html_file, 'r', encoding=encoding, errors='ignore') as f:
                html = f.read()
            
            print(f"\n✅ 使用編碼: {encoding}")
            break
        except:
            continue
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 分析表格結構
    tables = soup.find_all('table')
    print(f'\n📋 總共找到 {len(tables)} 個表格\n')
    
    # 尋找包含券商數據的表格
    for i, table in enumerate(tables):
        table_text = table.get_text()
        
        # 檢查是否包含關鍵字
        if '買進' in table_text or '賣出' in table_text or '差額' in table_text:
            print(f'=== 表格 {i+1} (可能包含券商數據) ===')
            rows = table.find_all('tr')
            print(f'行數: {len(rows)}')
            
            # 查看前10行
            print('\n前10行內容:')
            for j, row in enumerate(rows[:10]):
                cols = row.find_all(['td', 'th'])
                
                if len(cols) > 0:
                    # 提取所有欄位文字
                    texts = [col.get_text(strip=True) for col in cols]
                    
                    # 過濾空白
                    texts = [t for t in texts if t]
                    
                    if texts:
                        print(f'  第{j+1}行 ({len(cols)}欄): {texts[:8]}')  # 只顯示前8欄
            
            print()
    
    # 嘗試提取數據
    print("\n" + "=" * 80)
    print("🔍 嘗試提取券商數據")
    print("=" * 80)
    
    data_list = []
    
    for table in tables:
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            
            # 提取文字
            texts = [col.get_text(strip=True) for col in cols]
            
            # 尋找包含數字的行（可能是數據行）
            if len(texts) >= 4:
                # 檢查是否有數字
                has_numbers = any(re.search(r'\d+', t) for t in texts)
                
                if has_numbers:
                    # 嘗試解析為券商數據
                    # 格式可能是: [券商名稱, 買進, 賣出, 差額, ...]
                    
                    # 尋找可能的券商名稱（包含中文或數字）
                    for i, text in enumerate(texts):
                        if text and len(text) > 1 and not text.isdigit():
                            # 可能是券商名稱
                            if i + 3 < len(texts):
                                try:
                                    buy = int(texts[i+1].replace(',', ''))
                                    sell = int(texts[i+2].replace(',', ''))
                                    diff = int(texts[i+3].replace(',', '').replace('-', '0'))
                                    
                                    data_list.append({
                                        '券商名稱': text,
                                        '買進張數': buy,
                                        '賣出張數': sell,
                                        '差額': diff
                                    })
                                except:
                                    pass
    
    if data_list:
        df = pd.DataFrame(data_list)
        
        # 過濾無效數據
        df = df[df['買進張數'] > 0]
        df = df[df['券商名稱'].str.len() > 2]
        
        print(f"\n✅ 成功提取 {len(df)} 筆券商數據")
        print("\n前20筆數據:")
        print(df.head(20).to_string(index=False))
        
        # 保存數據
        output_file = 'broker_data_extracted.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 數據已保存到: {output_file}")
    else:
        print("\n⚠️ 未能提取到有效數據")
        print("建議手動查看HTML文件以了解實際結構")

except Exception as e:
    print(f"\n❌ 分析失敗: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
