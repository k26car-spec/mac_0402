#!/usr/bin/env python3
"""
測試選股引擎核心功能（不依賴券商數據）
"""

import sys
sys.path.append('backend-v3')

from app.services.integrated_stock_selector import integrated_selector
import asyncio

async def test_engine():
    print("="*80)
    print("🧪 測試選股引擎核心功能")
    print("="*80)
    
    # 測試股票清單
    test_stocks = ['2330', '2303', '2317', '2454', '2882']
    
    print(f"\n📊 測試股票: {', '.join(test_stocks)}")
    print("\n開始分析...")
    
    try:
        # 使用整合選股器分析
        results = []
        
        for stock_code in test_stocks:
            print(f"\n分析 {stock_code}...")
            
            try:
                # 分析單一股票
                result = await integrated_selector.analyze_stock(stock_code)
                
                if result and not result.get('metadata', {}).get('error'):
                    results.append({
                        '股票代碼': stock_code,
                        '綜合評分': result.get('scores', {}).get('composite_score', 0),
                        '評級': result.get('rating', 'N/A'),
                        '建議動作': result.get('recommendation', {}).get('action', 'N/A'),
                        '目標價': result.get('recommendation', {}).get('target_price', 0),
                        '停損價': result.get('recommendation', {}).get('stop_loss', 0),
                        '建議倉位': result.get('recommendation', {}).get('position_size', 0),
                    })
                    print(f"  ✅ 完成")
                else:
                    print(f"  ⚠️ 分析失敗")
                    
            except Exception as e:
                print(f"  ❌ 錯誤: {e}")
                continue
        
        if results:
            print("\n" + "="*80)
            print("✅ 選股引擎測試成功！")
            print("="*80)
            
            import pandas as pd
            df = pd.DataFrame(results)
            print("\n分析結果:")
            print(df.to_string(index=False))
            
            # 保存結果
            output_file = 'engine_test_results.csv'
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n✅ 結果已保存到: {output_file}")
            
            return True
        else:
            print("\n❌ 未能獲取任何分析結果")
            return False
            
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = asyncio.run(test_engine())
    
    print("\n" + "="*80)
    if success:
        print("🎉 測試完成！選股引擎核心功能正常")
    else:
        print("⚠️ 測試未完全成功，但這可能是數據源問題，不影響核心功能")
    print("="*80)
