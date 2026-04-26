"""
整合測試 - 券商數據 + 選股引擎
"""

import sys
import asyncio
import pandas as pd
from pathlib import Path

sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

print("=" * 80)
print("🚀 整合測試：券商數據 + 選股引擎")
print("=" * 80)

# 1. 載入券商數據
broker_data_file = 'broker_data_extracted.csv'

if not Path(broker_data_file).exists():
    print(f"❌ 券商數據文件不存在: {broker_data_file}")
    print("請先執行 analyze_fubon_html.py")
    exit(1)

print(f"\n📂 載入券商數據: {broker_data_file}")
broker_df = pd.read_csv(broker_data_file, encoding='utf-8-sig')

print(f"✅ 載入 {len(broker_df)} 筆券商數據")

# 2. 提取買超前20名的ETF/股票代碼
print("\n📊 分析買超數據...")

# 按差額排序
top_buys = broker_df.nlargest(30, '差額')

print(f"\n買超前30名:")
print(top_buys[['券商名稱', '買進張數', '賣出張數', '差額']].head(30).to_string(index=False))

# 提取股票代碼（從券商名稱中）
import re

stock_codes = []
for _, row in top_buys.iterrows():
    name = str(row['券商名稱'])
    
    # 尋找股票代碼模式（4-6位數字）
    codes = re.findall(r'\b\d{4,6}\b', name)
    
    if codes:
        code = codes[0]
        # 過濾掉明顯不是股票代碼的數字
        if len(code) in [4, 5, 6] and code not in stock_codes:
            stock_codes.append(code)

print(f"\n✅ 提取到 {len(stock_codes)} 個股票代碼: {stock_codes[:20]}")

if not stock_codes:
    print("\n⚠️ 未能從券商數據提取股票代碼")
    print("使用預設測試清單...")
    stock_codes = ['2330', '2303', '2317', '2454', '0050', '0056']

# 3. 使用選股引擎分析
print("\n" + "=" * 80)
print("🎯 啟動選股引擎分析")
print("=" * 80)

try:
    from app.services.integrated_stock_selector import analyze_multiple_stocks
    
    # 只分析前10檔（避免時間過長）
    analyze_codes = stock_codes[:10]
    
    print(f"\n分析股票: {analyze_codes}")
    print("請稍候...")
    
    async def run_analysis():
        df = await analyze_multiple_stocks(analyze_codes)
        return df
    
    # 執行分析
    result_df = asyncio.run(run_analysis())
    
    if not result_df.empty:
        print(f"\n✅ 分析完成，共 {len(result_df)} 檔股票\n")
        
        # 顯示結果
        print("【分析結果】")
        print(result_df[['股票代碼', '綜合評分', '評級', '建議動作', '風險等級', '建議倉位(%)']].to_string(index=False))
        
        # 篩選買入建議
        buy_recommendations = result_df[result_df['建議動作'].isin(['強力買入', '買入'])]
        
        if not buy_recommendations.empty:
            print(f"\n【買入建議】({len(buy_recommendations)} 檔)")
            print(buy_recommendations[['股票代碼', '綜合評分', '評級', '目標價', '停損價', '建議倉位(%)']].to_string(index=False))
        
        # 保存報告
        from app.services.integrated_stock_selector import integrated_selector
        
        filepath = integrated_selector.export_report(result_df, format='csv', filename='fubon_broker_analysis')
        if filepath:
            print(f"\n✅ 完整報告已匯出: {filepath}")
        
        # 整合券商數據到結果
        print("\n" + "=" * 80)
        print("📊 整合券商數據")
        print("=" * 80)
        
        # 合併券商數據
        for _, row in result_df.iterrows():
            code = row['股票代碼']
            
            # 查找對應的券商數據
            broker_match = broker_df[broker_df['券商名稱'].str.contains(code, na=False)]
            
            if not broker_match.empty:
                total_buy = broker_match['買進張數'].sum()
                total_sell = broker_match['賣出張數'].sum()
                net_flow = broker_match['差額'].sum()
                
                print(f"\n{code}:")
                print(f"  綜合評分: {row['綜合評分']:.2f}")
                print(f"  建議動作: {row['建議動作']}")
                print(f"  券商買進: {total_buy} 張")
                print(f"  券商賣出: {total_sell} 張")
                print(f"  淨流入: {net_flow:+d} 張")
    else:
        print("\n❌ 分析失敗")

except Exception as e:
    print(f"\n❌ 選股引擎執行失敗: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ 整合測試完成")
print("=" * 80)
