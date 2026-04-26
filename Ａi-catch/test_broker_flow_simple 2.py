"""
簡化測試腳本 - 測試券商進出分析
"""

import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

print("=" * 80)
print("🔍 測試券商進出分析器")
print("=" * 80)

try:
    from app.services.broker_flow_analyzer import broker_flow_analyzer
    
    print("\n【測試1】抓取富邦新店資料")
    print("-" * 80)
    
    # 測試抓取資料
    df = broker_flow_analyzer.fetch_fubon_broker_data(
        broker_code='9600',
        start_date='2024-12-25',
        end_date='2024-12-31'
    )
    
    if not df.empty:
        print(f"✅ 成功抓取 {len(df)} 筆資料")
        print("\n前10筆資料:")
        print(df.head(10).to_string())
    else:
        print("⚠️ 未抓取到資料（可能是網站限制或日期問題）")
    
    print("\n【測試2】獲取富邦新店買超前20名")
    print("-" * 80)
    
    top_stocks = broker_flow_analyzer.get_top_stocks_by_broker(
        broker_name='富邦-新店',
        top_n=20,
        min_net_count=50
    )
    
    if top_stocks:
        print(f"✅ 找到 {len(top_stocks)} 檔買超股票\n")
        
        for i, stock in enumerate(top_stocks[:10], 1):
            print(f"{i:2d}. {stock['stock_code']} {stock['stock_name']:10s} "
                  f"買: {stock['buy_count']:4d} 賣: {stock['sell_count']:4d} "
                  f"淨: {stock['net_count']:+5d}")
    else:
        print("⚠️ 未找到買超股票（可能需要調整參數或日期）")
    
    print("\n" + "=" * 80)
    print("✅ 券商分析器測試完成")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ 測試失敗: {e}")
    import traceback
    traceback.print_exc()
