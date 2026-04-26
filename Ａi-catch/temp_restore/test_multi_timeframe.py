#!/usr/bin/env python3
"""
多周期分析测试
Multi-Timeframe Analysis
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-v3'))

from app.experts import expert_manager, TimeFrame
from app.data_sources import YahooFinanceSource


def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


async def multi_timeframe_analysis(symbol: str):
    """
    多周期分析
    在多个时间框架上分析同一股票
    """
    
    print_header(f"🔍 {symbol} 多周期分析")
    
    # 获取真实数据
    data_source = YahooFinanceSource()
    real_data = data_source.get_stock_data(symbol)
    
    if not real_data:
        print(f"❌ 无法获取{symbol}数据")
        return
    
    # 显示基础信息
    print(f"\n📊 {symbol} 基础数据:")
    print(f"   当前价: {real_data['current_price']:.2f}")
    print(f"   涨跌幅: {real_data['price_change_percent']:.2%}")
    print(f"   成交量: {real_data['volume']:,}")
    
    # 补充数据
    enhanced_data = {
        **real_data,
        "avg_volume": real_data.get("avg_volume", real_data["volume"]),
        "large_buy_orders": int(real_data["volume"] * 0.05),
        "large_sell_orders": int(real_data["volume"] * 0.05),
        "bid_volume": int(real_data["volume"] * 0.4),
        "ask_volume": int(real_data["volume"] * 0.4),
        "price_change_1d": real_data["price_change_percent"],
        "price_change_5d": real_data["price_change_percent"] * 2,
        "volume_change": 0.1,
        "atr": real_data["current_price"] * 0.02,
        "atr_avg": real_data["current_price"] * 0.02,
        "bb_upper": real_data["current_price"] * 1.05,
        "bb_lower": real_data["current_price"] * 0.95,
        "bb_middle": real_data["current_price"],
        "advance_decline_ratio": 1.2,
        "value_change": 0.1,
        "foreign_net_buy": 100,
        "fear_greed_index": 50,
        "close": real_data["current_price"],
    }
    
    # 要分析的时间框架
    timeframes = [
        (TimeFrame.M5, "5分钟"),
        (TimeFrame.M15, "15分钟"),
        (TimeFrame.H1, "1小时"),
        (TimeFrame.D1, "日线"),
    ]
    
    results = {}
    
    print(f"\n{'─' * 80}")
    print(f"开始多周期分析...")
    print(f"{'─' * 80}")
    
    # 在每个时间框架上分析
    for tf, tf_name in timeframes:
        print(f"\n⏱️  {tf_name} 分析...")
        
        result = await expert_manager.analyze_stock(symbol, tf, enhanced_data)
        results[tf.value] = result
        
        # 显示结果摘要
        signal = result['overall_signal']
        strength = result['overall_strength']
        confidence = result['overall_confidence']
        consensus = result['consensus']
        
        # 信号emoji
        if signal == 'strong_buy':
            emoji = "🟢🟢"
        elif signal == 'buy':
            emoji = "🟢"
        elif signal == 'strong_sell':
            emoji = "🔴🔴"
        elif signal == 'sell':
            emoji = "🔴"
        else:
            emoji = "🟡"
        
        print(f"   {emoji} {signal.upper()}")
        print(f"   强度: {strength:.2%}, 置信: {confidence:.2%}")
        print(f"   共识: 买{consensus['buy_count']} / 卖{consensus['sell_count']} / 持{consensus['hold_count']}")
    
    # 多周期综合分析
    print_header("📈 多周期综合分析")
    
    # 统计各周期的信号
    buy_signals = sum(1 for r in results.values() if r['overall_signal'] in ['buy', 'strong_buy'])
    sell_signals = sum(1 for r in results.values() if r['overall_signal'] in ['sell', 'strong_sell'])
    hold_signals = sum(1 for r in results.values() if r['overall_signal'] == 'hold')
    
    print(f"\n周期信号分布:")
    print(f"   看多周期: {buy_signals}/{len(timeframes)}")
    print(f"   看空周期: {sell_signals}/{len(timeframes)}")
    print(f"   观望周期: {hold_signals}/{len(timeframes)}")
    
    # 趋势一致性
    if buy_signals >= 3:
        trend = "🟢 多头趋势"
        consistency = "高度一致"
    elif sell_signals >= 3:
        trend = "🔴 空头趋势"
        consistency = "高度一致"
    elif buy_signals > sell_signals:
        trend = "🟢 偏多"
        consistency = "部分一致"
    elif sell_signals > buy_signals:
        trend = "🔴 偏空"
        consistency = "部分一致"
    else:
        trend = "🟡 震荡"
        consistency = "信号分歧"
    
    print(f"\n趋势判断: {trend}")
    print(f"一致性: {consistency}")
    
    # 时间框架共振
    all_buy = buy_signals == len(timeframes)
    all_sell = sell_signals == len(timeframes)
    
    if all_buy:
        print(f"\n⚡ 多周期共振: 所有时间框架均看多！")
        print(f"   建议: 🟢🟢 强烈买入信号")
    elif all_sell:
        print(f"\n⚡ 多周期共振: 所有时间框架均看空！")
        print(f"   建议: 🔴🔴 强烈卖出信号")
    else:
        avg_strength = sum(r['overall_strength'] for r in results.values()) / len(results)
        avg_confidence = sum(r['overall_confidence'] for r in results.values()) / len(results)
        
        print(f"\n平均强度: {avg_strength:.2%}")
        print(f"平均置信: {avg_confidence:.2%}")
        
        if buy_signals > sell_signals and avg_confidence > 0.7:
            print(f"   建议: 🟢 考虑买入")
        elif sell_signals > buy_signals and avg_confidence > 0.7:
            print(f"   建议: 🔴 考虑卖出")
        else:
            print(f"   建议: 🟡 观望等待")
    
    print("\n" + "=" * 80)


async def test_multiple_stocks():
    """测试多只股票的多周期分析"""
    
    print_header("🚀 多周期分析系统测试")
    
    test_symbols = ["2330", "2317"]
    
    for symbol in test_symbols:
        await multi_timeframe_analysis(symbol)
        print("\n")
    
    print_header("✅ 多周期分析测试完成")


if __name__ == "__main__":
    asyncio.run(test_multiple_stocks())
