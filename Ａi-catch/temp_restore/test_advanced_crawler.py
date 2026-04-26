"""
測試進階券商爬蟲
"""

import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from datetime import datetime, timedelta

print("=" * 80)
print("🔍 測試進階券商爬蟲")
print("=" * 80)

try:
    from app.services.advanced_broker_crawler import (
        advanced_broker_crawler,
        get_fubon_xindan_data,
        get_fubon_xindan_top_stocks_advanced
    )
    
    # 測試1: 抓取富邦新店最近5天數據
    print("\n【測試1】抓取富邦新店最近5天數據")
    print("-" * 80)
    
    df = get_fubon_xindan_data(days=5)
    
    if not df.empty:
        print(f"✅ 成功抓取 {len(df)} 筆數據")
        print("\n前10筆數據:")
        print(df.head(10)[['stock_code', 'stock_name', 'buy_count', 'sell_count', 'net_count']].to_string())
        
        # 保存數據
        filename = advanced_broker_crawler.save_to_csv(df, 'fubon_xindan_test.csv')
        if filename:
            print(f"\n數據已保存: {filename}")
    else:
        print("⚠️ 未抓取到數據")
    
    # 測試2: 獲取買超前20名
    print("\n【測試2】獲取富邦新店買超前20名")
    print("-" * 80)
    
    top_stocks = get_fubon_xindan_top_stocks_advanced(top_n=20)
    
    if top_stocks:
        print(f"✅ 找到 {len(top_stocks)} 檔買超股票\n")
        
        for i, stock in enumerate(top_stocks[:10], 1):
            print(f"{i:2d}. {stock['stock_code']} {stock['stock_name']:10s} "
                  f"買: {stock['buy_count']:4d} 賣: {stock['sell_count']:4d} "
                  f"淨: {stock['net_count']:+5d}")
    else:
        print("⚠️ 未找到買超股票")
    
    # 測試3: 抓取特定日期數據
    print("\n【測試3】抓取特定日期數據 (2024-12-31)")
    print("-" * 80)
    
    df_specific = advanced_broker_crawler.get_broker_flow_by_date(
        broker_code='9600',
        start_date='2024-12-31',
        end_date='2024-12-31'
    )
    
    if not df_specific.empty:
        print(f"✅ 成功抓取 {len(df_specific)} 筆數據")
        print(f"數據摘要:")
        print(f"  股票數量: {df_specific['stock_code'].nunique()}")
        print(f"  總買進: {df_specific['buy_count'].sum()}")
        print(f"  總賣出: {df_specific['sell_count'].sum()}")
        print(f"  淨流入: {df_specific['net_count'].sum()}")
    else:
        print("⚠️ 未抓取到數據")
    
    # 測試4: 測試請求頻率控制
    print("\n【測試4】測試請求頻率控制（連續請求）")
    print("-" * 80)
    
    print("連續請求3次...")
    for i in range(3):
        print(f"\n第 {i+1} 次請求:")
        df_test = advanced_broker_crawler.get_broker_flow_by_date(
            broker_code='9600',
            start_date='2024-12-30',
            end_date='2024-12-30'
        )
        
        if not df_test.empty:
            print(f"  ✅ 成功，{len(df_test)} 筆數據")
        else:
            print(f"  ⚠️ 失敗或無數據")
    
    print("\n" + "=" * 80)
    print("✅ 測試完成")
    print("=" * 80)
    
    # 顯示統計
    print(f"\n📊 統計資訊:")
    print(f"  總請求次數: {advanced_broker_crawler.request_count}")
    print(f"  批次大小: {advanced_broker_crawler.batch_size}")
    
except Exception as e:
    print(f"\n❌ 測試失敗: {e}")
    import traceback
    traceback.print_exc()
finally:
    # 清理資源
    try:
        advanced_broker_crawler.close()
        print("\n✅ 資源已清理")
    except:
        pass
