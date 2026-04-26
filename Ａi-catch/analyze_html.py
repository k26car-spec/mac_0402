#!/usr/bin/env python3
"""
快速分析富邦HTML結構
"""

from bs4 import BeautifulSoup
import sys

def quick_analyze_html(file_path):
    """快速分析HTML結構"""
    print("="*80)
    print(f"📊 分析 HTML 文件: {file_path}")
    print("="*80)
    
    try:
        # 嘗試不同編碼
        html_content = None
        for encoding in ['utf-8', 'big5', 'gb18030']:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    html_content = f.read()
                print(f"\n✅ 使用編碼: {encoding}")
                break
            except:
                continue
        
        if not html_content:
            print("❌ 無法讀取文件")
            return None
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 找到所有表格
        tables = soup.find_all('table')
        print(f"\n📋 總共找到 {len(tables)} 個表格\n")
        
        target_table = None
        
        for i, table in enumerate(tables[:10]):  # 只看前10個
            print(f"\n{'='*80}")
            print(f"📊 表格 {i+1}")
            print(f"{'='*80}")
            
            rows = table.find_all('tr')
            print(f"行數: {len(rows)}")
            
            # 獲取表格文本
            text = table.get_text()
            
            # 檢查是否包含關鍵字
            keywords = ['券商', '買進', '賣出', '張數', '差額', '股票']
            found_keywords = [kw for kw in keywords if kw in text]
            
            if found_keywords:
                print(f"✅ 包含關鍵字: {', '.join(found_keywords)}")
                target_table = table
                
                # 顯示前5行
                print(f"\n前5行內容:")
                for j, row in enumerate(rows[:5]):
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        texts = [cell.get_text(strip=True) for cell in cells]
                        # 過濾空白
                        texts = [t for t in texts if t]
                        if texts:
                            print(f"  第{j+1}行 ({len(cells)}欄): {texts[:10]}")  # 只顯示前10欄
                
                # 顯示HTML結構
                print(f"\n前3行的HTML結構:")
                for j, row in enumerate(rows[:3]):
                    print(f"\n  === 第{j+1}行 HTML ===")
                    print(f"  {str(row)[:500]}")  # 只顯示前500字元
                
            else:
                print(f"⚠️ 未包含關鍵字")
        
        return target_table
        
    except Exception as e:
        print(f"\n❌ 分析失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # 查找最新的HTML文件
    import glob
    import os
    
    html_files = glob.glob('fubon_test_*.html')
    
    if html_files:
        # 使用最新的文件
        latest_file = max(html_files, key=os.path.getctime)
        print(f"\n使用文件: {latest_file}\n")
        
        target = quick_analyze_html(latest_file)
        
        if target:
            print("\n" + "="*80)
            print("✅ 找到目標表格！")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("⚠️ 未找到明確的目標表格")
            print("="*80)
    else:
        print("❌ 未找到 fubon_test_*.html 文件")
        print("請先運行 test_fubon_direct.py 生成HTML文件")
