"""
選股決策引擎測試腳本
測試券商進出分析和整合選股功能
"""

import asyncio
import sys
import os

# 添加路徑
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.broker_flow_analyzer import (
    broker_flow_analyzer,
    get_fubon_xindan_flow,
    get_fubon_xindan_top_stocks
)
from app.services.integrated_stock_selector import (
    integrated_selector,
    analyze_single_stock,
    analyze_multiple_stocks,
    get_top_recommendations
)


async def test_broker_flow_analyzer():
    """測試券商進出分析器"""
    print("=" * 80)
    print("🔍 測試券商進出分析器")
    print("=" * 80)
    
    # 測試1: 抓取富邦新店資料
    print("\n【測試1】抓取富邦新店買賣資料")
    print("-" * 80)
    
    df = broker_flow_analyzer.fetch_fubon_broker_data(
        broker_code='9600',  # 富邦新店
        start_date='2024-12-01',
        end_date='2024-12-31'
    )
    
    if not df.empty:
        print(f"✅ 成功抓取 {len(df)} 筆資料")
        print("\n前5筆資料:")
        print(df.head().to_string())
    else:
        print("⚠️ 未抓取到資料")
    
    # 測試2: 獲取富邦新店買超前20名
    print("\n【測試2】富邦新店買超前20名")
    print("-" * 80)
    
    top_stocks = get_fubon_xindan_top_stocks(top_n=20)
    
    if top_stocks:
        print(f"✅ 找到 {len(top_stocks)} 檔買超股票\n")
        
        for i, stock in enumerate(top_stocks[:10], 1):
            print(f"{i:2d}. {stock['stock_code']} {stock['stock_name']:10s} "
                  f"買: {stock['buy_count']:4d} 賣: {stock['sell_count']:4d} "
                  f"淨: {stock['net_count']:+5d}")
    else:
        print("⚠️ 未找到買超股票")
    
    # 測試3: 分析特定股票的券商進出
    print("\n【測試3】分析特定股票券商進出 (2330 台積電)")
    print("-" * 80)
    
    flow_summary = get_fubon_xindan_flow('2330', days=5)
    
    if flow_summary:
        print(f"✅ 券商進出分析:")
        print(f"   分析期間: {flow_summary['analysis_period_days']} 天")
        print(f"   總買進: {flow_summary['total_buy_count']} 張")
        print(f"   總賣出: {flow_summary['total_sell_count']} 張")
        print(f"   淨流入: {flow_summary['net_flow_count']:+d} 張")
        print(f"   趨勢: {flow_summary['flow_trend']}")
        print(f"   異常活動: {'是' if flow_summary['unusual_activity'] else '否'}")
        print(f"   法人比例: {flow_summary['institutional_ratio']:.2f}%")
        print(f"   信心分數: {flow_summary['confidence_score']:.2f}")
        
        if flow_summary['key_observations']:
            print(f"\n   關鍵觀察:")
            for obs in flow_summary['key_observations']:
                print(f"   • {obs}")
        
        if flow_summary['broker_details']:
            print(f"\n   券商明細:")
            for broker, details in flow_summary['broker_details'].items():
                print(f"   {broker:12s}: 淨 {details['net_count']:+5d} 張 ({details['trend']})")
    else:
        print("⚠️ 未獲取到券商進出資料")


async def test_integrated_selector():
    """測試整合選股引擎"""
    print("\n" + "=" * 80)
    print("📊 測試整合選股引擎")
    print("=" * 80)
    
    # 測試1: 分析單一股票
    print("\n【測試1】分析單一股票 (2330 台積電)")
    print("-" * 80)
    
    result = await analyze_single_stock('2330')
    
    if not result.get('metadata', {}).get('error'):
        print(f"✅ 分析完成\n")
        
        scores = result['scores']
        recommendation = result['recommendation']
        risk = result['risk_assessment']
        
        print(f"📈 綜合評分: {scores['weighted_score']:.2f}")
        print(f"📊 評級: {scores['final_grade']}")
        print(f"💡 建議: {scores['recommendation']}")
        print(f"🎯 信心分數: {scores['confidence']:.2f}")
        
        if scores.get('target_price'):
            print(f"🎯 目標價: {scores['target_price']}")
        if scores.get('stop_loss'):
            print(f"🛑 停損價: {scores['stop_loss']}")
        
        print(f"\n📊 各維度評分:")
        for component, score in scores['component_scores'].items():
            print(f"   {component:20s}: {score:.2f}")
        
        print(f"\n⚠️ 風險評估:")
        print(f"   風險等級: {risk['level']}")
        if risk['factors']:
            print(f"   風險因素: {', '.join(risk['factors'])}")
        
        print(f"\n💼 投資建議:")
        print(f"   動作: {recommendation['action']}")
        print(f"   評級: {recommendation['grade']}")
        print(f"   信心: {recommendation['confidence']:.2f}")
        if recommendation['key_reasons']:
            print(f"   關鍵理由:")
            for reason in recommendation['key_reasons']:
                print(f"   • {reason}")
    else:
        print("❌ 分析失敗")
    
    # 測試2: 批量分析股票
    print("\n【測試2】批量分析股票")
    print("-" * 80)
    
    test_stocks = ['2330', '2303', '2317', '2454', '2882', '3481', '2344', '0050']
    
    print(f"分析股票: {', '.join(test_stocks)}\n")
    
    df = await analyze_multiple_stocks(test_stocks)
    
    if not df.empty:
        print(f"✅ 批量分析完成，共 {len(df)} 檔股票\n")
        
        # 顯示結果
        print("分析結果:")
        print(df[['股票代碼', '綜合評分', '評級', '建議動作', '風險等級', '建議倉位(%)']].to_string(index=False))
        
        # 篩選買入建議
        buy_stocks = df[df['建議動作'].isin(['強力買入', '買入'])]
        
        if not buy_stocks.empty:
            print(f"\n✅ 買入建議 ({len(buy_stocks)} 檔):")
            print(buy_stocks[['股票代碼', '綜合評分', '評級', '建議動作', '目標價', '停損價']].to_string(index=False))
        else:
            print("\n⚠️ 本次分析無買入建議")
        
        # 匯出報告
        print("\n【匯出報告】")
        filepath = integrated_selector.export_report(df, format='csv')
        if filepath:
            print(f"✅ 報告已匯出: {filepath}")
    else:
        print("❌ 批量分析失敗")
    
    # 測試3: 獲取推薦股票
    print("\n【測試3】獲取前5名推薦股票")
    print("-" * 80)
    
    top_df = await get_top_recommendations(test_stocks, top_n=5)
    
    if not top_df.empty:
        print(f"✅ 前 {len(top_df)} 名推薦:\n")
        print(top_df[['股票代碼', '綜合評分', '評級', '建議動作', '目標價', '建議倉位(%)']].to_string(index=False))
    else:
        print("⚠️ 無推薦股票")


async def test_full_workflow():
    """測試完整工作流程"""
    print("\n" + "=" * 80)
    print("🚀 完整工作流程測試")
    print("=" * 80)
    
    # 步驟1: 從富邦新店找出買超股票
    print("\n【步驟1】從富邦新店找出買超股票")
    print("-" * 80)
    
    fubon_stocks = get_fubon_xindan_top_stocks(top_n=10)
    
    if not fubon_stocks:
        print("⚠️ 未找到富邦新店買超股票，使用預設清單")
        stock_codes = ['2330', '2303', '2317', '2454', '2882']
    else:
        stock_codes = [s['stock_code'] for s in fubon_stocks[:10]]
        print(f"✅ 找到 {len(stock_codes)} 檔買超股票: {', '.join(stock_codes)}")
    
    # 步驟2: 對這些股票進行完整分析
    print("\n【步驟2】完整分析買超股票")
    print("-" * 80)
    
    df = await analyze_multiple_stocks(stock_codes)
    
    if df.empty:
        print("❌ 分析失敗")
        return
    
    print(f"✅ 分析完成\n")
    
    # 步驟3: 篩選出高分股票
    print("【步驟3】篩選高分股票 (評分 >= 70)")
    print("-" * 80)
    
    high_score_stocks = df[df['綜合評分'] >= 70]
    
    if not high_score_stocks.empty:
        print(f"✅ 找到 {len(high_score_stocks)} 檔高分股票:\n")
        print(high_score_stocks[['股票代碼', '綜合評分', '評級', '建議動作', '目標價', '停損價', '建議倉位(%)']].to_string(index=False))
    else:
        print("⚠️ 無高分股票")
    
    # 步驟4: 顯示最終推薦
    print("\n【步驟4】最終投資建議")
    print("-" * 80)
    
    buy_recommendations = df[df['建議動作'].isin(['強力買入', '買入'])]
    
    if not buy_recommendations.empty:
        print(f"✅ 推薦買入 {len(buy_recommendations)} 檔股票:\n")
        
        for idx, row in buy_recommendations.iterrows():
            print(f"""
股票代碼: {row['股票代碼']}
綜合評分: {row['綜合評分']:.2f} ({row['評級']})
建議動作: {row['建議動作']}
目標價: {row['目標價']}
停損價: {row['停損價']}
建議倉位: {row['建議倉位(%)']}%
風險等級: {row['風險等級']}
信心分數: {row['信心分數']:.2f}
            """)
    else:
        print("⚠️ 本次無買入建議")
    
    # 步驟5: 匯出完整報告
    print("【步驟5】匯出完整報告")
    print("-" * 80)
    
    filepath = integrated_selector.export_report(df, format='csv', filename='fubon_xindan_analysis')
    if filepath:
        print(f"✅ 完整報告已匯出: {filepath}")


async def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("🎯 選股決策引擎 - 完整測試")
    print("=" * 80)
    
    try:
        # 測試券商分析
        await test_broker_flow_analyzer()
        
        # 測試整合選股
        await test_integrated_selector()
        
        # 測試完整工作流程
        await test_full_workflow()
        
        print("\n" + "=" * 80)
        print("✅ 所有測試完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 執行測試
    asyncio.run(main())
