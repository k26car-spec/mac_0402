#!/usr/bin/env python3
"""
測試富邦API整合 - 獲取台股技術指標
"""

import asyncio
import sys
import os

# 添加路徑
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def test_fubon_integration():
    """測試富邦API整合"""
    print("=" * 60)
    print("🧪 測試富邦API整合")
    print("=" * 60)
    
    try:
        # 導入服務
        from app.services.real_data_service import fubon_service
        
        print("\n📡 步驟 1: 初始化富邦連接...")
        success = await fubon_service.initialize()
        
        if success:
            print("✅ 富邦API連接成功！")
        else:
            print("⚠️  富邦API連接失敗，將使用備用數據")
            print("💡 如要使用真實數據，請確保:")
            print("   1. 富邦Neo SDK已安裝")
            print("   2. fubon.env 配置正確")
            print("   3. 憑證文件存在")
            return False
        
        print("\n📈 步驟 2: 測試獲取單支股票技術指標...")
        print("   目標: 台積電 (2330)")
        
        indicators = await fubon_service.get_technical_indicators("2330")
        
        if indicators:
            print("\n✅ 成功獲取台積電技術指標:")
            print(f"   當前價格: {indicators['current_price']:.2f}")
            print(f"   MA5:  {indicators['ma5']:.2f}")
            print(f"   MA10: {indicators['ma10']:.2f}")
            print(f"   MA20: {indicators['ma20']:.2f}")
            print(f"   MA60: {indicators['ma60']:.2f}")
            print(f"   RSI:  {indicators['rsi']:.2f}")
            print(f"   MACD: {indicators['macd']:.2f}")
            print(f"   量比: {indicators['volume_ratio']:.2f}x")
            print(f"   數據來源: {indicators['data_source']}")
        else:
            print("❌ 未能獲取技術指標")
            return False
        
        print("\n📊 步驟 3: 測試批量獲取技術指標...")
        test_symbols = ["2330", "2454", "3661"]
        print(f"   目標股票: {', '.join(test_symbols)}")
        
        batch_indicators = await fubon_service.batch_get_technical_indicators(test_symbols)
        
        print(f"\n✅ 成功獲取 {len(batch_indicators)} 支股票的數據:")
        for symbol, data in batch_indicators.items():
            print(f"   {symbol}: 價格={data['current_price']:.2f}, MA5={data['ma5']:.2f}, RSI={data['rsi']:.2f}")
        
        print("\n" + "=" * 60)
        print("✅ 富邦API整合測試完成！")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"\n❌ 導入錯誤: {e}")
        print("💡 請確保 fubon_neo SDK 已安裝:")
        print("   pip install fubon-neo")
        return False
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_fubon_integration())
    sys.exit(0 if result else 1)
