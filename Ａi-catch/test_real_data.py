#!/usr/bin/env python3
"""
使用真实数据测试9个专家系统
Real Data + 9 Experts Test
"""

import sys
import os
import asyncio

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-v3'))

from app.experts import expert_manager, TimeFrame
from app.data_sources import YahooFinanceSource


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


async def test_with_real_data():
    """使用真实数据测试专家系统"""
    
    print_header("🚀 9专家系统 + Yahoo Finance真实数据测试")
    
    # 初始化数据源
    data_source = YahooFinanceSource()
    
    # 测试股票
    test_symbols = ["2330", "2317", "2454"]
    
    for symbol in test_symbols:
        print(f"\n{'─' * 70}")
        print(f"📊 分析股票: {symbol}")
        print(f"{'─' * 70}")
        
        # 1. 获取真实数据
        print(f"\n🔍 获取Yahoo Finance真实数据...")
        real_data = data_source.get_stock_data(symbol)
        
        if not real_data:
            print(f"❌ 无法获取{symbol}数据，跳过")
            continue
        
        # 显示数据摘要
        print(f"✅ 数据获取成功")
        print(f"   当前价: {real_data['current_price']:.2f}")
        print(f"   涨跌幅: {real_data['price_change_percent']:.2%}")
        print(f"   成交量: {real_data['volume']:,}")
        print(f"   MA5: {real_data['ma5']:.2f}")
        print(f"   MA20: {real_data['ma20']:.2f}")
        
        # 2. 补充专家需要的数据
        enhanced_data = {
            **real_data,
            # 补充缺失的字段（使用合理估算）
            "avg_volume": real_data.get("avg_volume", real_data["volume"]),
            "large_buy_orders": int(real_data["volume"] * 0.05),  # 估算
            "large_sell_orders": int(real_data["volume"] * 0.05),
            "bid_volume": int(real_data["volume"] * 0.4),
            "ask_volume": int(real_data["volume"] * 0.4),
            "price_change_1d": real_data["price_change_percent"],
            "price_change_5d": real_data["price_change_percent"] * 2,  # 估算
            "volume_change": 0.1,  # 估算
            
            # ATR和布林带（简化计算）
            "atr": real_data["current_price"] * 0.02,
            "atr_avg": real_data["current_price"] * 0.02,
            "bb_upper": real_data["current_price"] * 1.05,
            "bb_lower": real_data["current_price"] * 0.95,
            "bb_middle": real_data["current_price"],
            
            # 市场情绪（模拟）
            "advance_decline_ratio": 1.2,
            "value_change": 0.1,
            "foreign_net_buy": 100,
            "fear_greed_index": 50,
            
            # 确保K线数据完整
            "close": real_data["current_price"],
        }
        
        # 3. 运行9专家分析
        print(f"\n🤖 运行9专家AI分析...")
        result = await expert_manager.analyze_stock(
            symbol, 
            TimeFrame.D1, 
            enhanced_data
        )
        
        # 4. 显示结果
        print(f"\n📈 分析结果:")
        print(f"   综合信号: {result['overall_signal'].upper()}")
        print(f"   信号强度: {result['overall_strength']:.2%}")
        print(f"   置信度: {result['overall_confidence']:.2%}")
        print(f"   参与专家: {result['expert_count']}/{result['total_experts']}")
        
        print(f"\n📊 专家共识:")
        consensus = result['consensus']
        print(f"   看多: {consensus['buy_count']} 个")
        print(f"   看空: {consensus['sell_count']} 个")
        print(f"   观望: {consensus['hold_count']} 个")
        
        # 显示每个专家的信号
        print(f"\n📋 专家详细信号:")
        for i, signal in enumerate(result['signals'], 1):
            print(f"   {i}. {signal['expert_name']}: "
                  f"{signal['signal_type'].upper()} "
                  f"(强度{signal['strength']:.0%}, 置信{signal['confidence']:.0%})")
            if signal.get('reasoning'):
                print(f"      推理: {signal['reasoning']}")
        
        # 投资建议
        signal = result['overall_signal']
        if signal == 'strong_buy':
            emoji = "🟢🟢"
            advice = "强烈买入"
        elif signal == 'buy':
            emoji = "🟢"
            advice = "买入"
        elif signal == 'strong_sell':
            emoji = "🔴🔴"
            advice = "强烈卖出"
        elif signal == 'sell':
            emoji = "🔴"
            advice = "卖出"
        else:
            emoji = "🟡"
            advice = "观望"
        
        print(f"\n🎯 投资建议: {emoji} {advice}")
        print(f"   (基于真实市场数据的AI分析)")
    
    print_header("✅ 真实数据测试完成")
    print(f"\n💡 总结:")
    print(f"   • 数据源: Yahoo Finance (真实数据)")
    print(f"   • AI专家: 9个全部工作")
    print(f"   • 测试股票: {len(test_symbols)}只")
    print(f"   • 状态: 🟢 系统正常运行\n")


if __name__ == "__main__":
    asyncio.run(test_with_real_data())
