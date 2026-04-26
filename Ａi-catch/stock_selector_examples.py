"""
選股決策引擎 - 實用範例
展示如何使用整合選股系統進行實際選股
"""

import asyncio
import sys
import pandas as pd
from datetime import datetime

sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.integrated_stock_selector import (
    integrated_selector,
    analyze_single_stock,
    analyze_multiple_stocks
)


async def example_1_analyze_single_stock():
    """範例1: 分析單一股票"""
    print("\n" + "=" * 80)
    print("📊 範例1: 分析單一股票 (2330 台積電)")
    print("=" * 80)
    
    result = await analyze_single_stock('2330')
    
    if not result.get('metadata', {}).get('error'):
        scores = result['scores']
        recommendation = result['recommendation']
        
        print(f"\n✅ 分析完成")
        print(f"\n【綜合評估】")
        print(f"  評分: {scores['weighted_score']:.2f}/100")
        print(f"  評級: {scores['final_grade']}")
        print(f"  建議: {scores['recommendation']}")
        print(f"  信心: {scores['confidence']:.2f}%")
        
        if scores.get('target_price'):
            print(f"\n【價格建議】")
            print(f"  目標價: {scores['target_price']}")
            print(f"  停損價: {scores.get('stop_loss', 'N/A')}")
        
        print(f"\n【各維度評分】")
        for component, score in scores['component_scores'].items():
            print(f"  {component:20s}: {score:.2f}")
        
        print(f"\n【投資建議】")
        print(f"  動作: {recommendation['action']}")
        if recommendation.get('key_reasons'):
            print(f"  理由:")
            for reason in recommendation['key_reasons']:
                print(f"    • {reason}")
    else:
        print("❌ 分析失敗")


async def example_2_batch_analysis():
    """範例2: 批量分析股票"""
    print("\n" + "=" * 80)
    print("📊 範例2: 批量分析股票")
    print("=" * 80)
    
    # 定義觀察清單
    watchlist = ['2330', '2303', '2317', '2454', '2882', '2881', '0050', '0056']
    
    print(f"\n觀察清單: {', '.join(watchlist)}")
    print(f"開始分析...")
    
    df = await analyze_multiple_stocks(watchlist)
    
    if not df.empty:
        print(f"\n✅ 分析完成，共 {len(df)} 檔股票\n")
        
        # 顯示結果摘要
        print("【分析結果摘要】")
        print(df[['股票代碼', '綜合評分', '評級', '建議動作', '風險等級']].to_string(index=False))
        
        # 篩選買入建議
        buy_stocks = df[df['建議動作'].isin(['強力買入', '買入'])]
        
        if not buy_stocks.empty:
            print(f"\n【買入建議】({len(buy_stocks)} 檔)")
            print(buy_stocks[['股票代碼', '綜合評分', '評級', '目標價', '停損價', '建議倉位(%)']].to_string(index=False))
        
        # 匯出報告
        print(f"\n【匯出報告】")
        filepath = integrated_selector.export_report(df, format='csv', filename='example_analysis')
        if filepath:
            print(f"✅ 報告已匯出: {filepath}")
    else:
        print("❌ 批量分析失敗")


async def example_3_sector_analysis():
    """範例3: 產業分析"""
    print("\n" + "=" * 80)
    print("📊 範例3: 產業分析")
    print("=" * 80)
    
    # 定義產業股票池
    sectors = {
        '半導體': ['2330', '2303', '2454'],
        '金融': ['2882', '2881', '2891'],
        'ETF': ['0050', '0056', '00878']
    }
    
    sector_results = {}
    
    for sector_name, stocks in sectors.items():
        print(f"\n分析 {sector_name} 產業...")
        
        df = await analyze_multiple_stocks(stocks)
        
        if not df.empty:
            avg_score = df['綜合評分'].mean()
            top_stock = df.iloc[0]
            
            sector_results[sector_name] = {
                'avg_score': avg_score,
                'top_stock_code': top_stock['股票代碼'],
                'top_stock_score': top_stock['綜合評分'],
                'top_stock_action': top_stock['建議動作']
            }
            
            print(f"  平均評分: {avg_score:.2f}")
            print(f"  最佳標的: {top_stock['股票代碼']} (評分: {top_stock['綜合評分']:.2f})")
    
    # 找出最強產業
    if sector_results:
        print(f"\n【產業排名】")
        sorted_sectors = sorted(sector_results.items(), key=lambda x: x[1]['avg_score'], reverse=True)
        
        for i, (sector, data) in enumerate(sorted_sectors, 1):
            print(f"{i}. {sector:10s} 平均: {data['avg_score']:.2f} | "
                  f"推薦: {data['top_stock_code']} ({data['top_stock_action']})")


async def example_4_custom_screening():
    """範例4: 自訂篩選條件"""
    print("\n" + "=" * 80)
    print("📊 範例4: 自訂篩選條件")
    print("=" * 80)
    
    # 大範圍股票池
    stock_pool = ['2330', '2303', '2317', '2454', '2882', '2881', '2891', 
                  '2886', '0050', '0056', '00878', '00929', '2344', '3481']
    
    print(f"\n股票池: {len(stock_pool)} 檔")
    print(f"篩選條件: 評分 >= 70 且 建議動作為買入")
    
    df = await analyze_multiple_stocks(stock_pool)
    
    if not df.empty:
        # 自訂篩選
        filtered = df[
            (df['綜合評分'] >= 70) & 
            (df['建議動作'].isin(['強力買入', '買入']))
        ]
        
        if not filtered.empty:
            print(f"\n✅ 符合條件: {len(filtered)} 檔\n")
            
            # 按評分排序
            filtered = filtered.sort_values('綜合評分', ascending=False)
            
            print("【篩選結果】")
            print(filtered[['股票代碼', '綜合評分', '評級', '建議動作', 
                          '目標價', '停損價', '建議倉位(%)']].to_string(index=False))
            
            # 計算總建議倉位
            total_position = filtered['建議倉位(%)'].sum()
            print(f"\n總建議倉位: {total_position:.2f}%")
            
            if total_position > 100:
                print("⚠️ 總倉位超過100%，建議調整個別倉位比例")
        else:
            print("\n⚠️ 無股票符合篩選條件")
    else:
        print("❌ 分析失敗")


async def example_5_risk_assessment():
    """範例5: 風險評估"""
    print("\n" + "=" * 80)
    print("📊 範例5: 風險評估")
    print("=" * 80)
    
    stocks = ['2330', '3481', '2344']  # 不同風險等級的股票
    
    print(f"\n分析股票: {', '.join(stocks)}")
    
    for stock_code in stocks:
        result = await analyze_single_stock(stock_code)
        
        if not result.get('metadata', {}).get('error'):
            risk = result['risk_assessment']
            scores = result['scores']
            position = result['position_sizing']
            
            print(f"\n【{stock_code}】")
            print(f"  評分: {scores['weighted_score']:.2f}")
            print(f"  風險等級: {risk['level']}")
            print(f"  建議倉位: {position['position_pct']:.2f}%")
            
            if risk['factors']:
                print(f"  風險因素: {', '.join(risk['factors'])}")


async def main():
    """主函數"""
    print("\n" + "=" * 80)
    print("🎯 選股決策引擎 - 實用範例")
    print("=" * 80)
    
    try:
        # 執行各種範例
        await example_1_analyze_single_stock()
        await example_2_batch_analysis()
        await example_3_sector_analysis()
        await example_4_custom_screening()
        await example_5_risk_assessment()
        
        print("\n" + "=" * 80)
        print("✅ 所有範例執行完成")
        print("=" * 80)
        print("\n💡 提示:")
        print("  - 報告已匯出到 backend-v3/reports/ 目錄")
        print("  - 可根據需求調整評分權重和篩選條件")
        print("  - 建議結合個人判斷和風險承受度")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 執行過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 執行範例
    asyncio.run(main())
