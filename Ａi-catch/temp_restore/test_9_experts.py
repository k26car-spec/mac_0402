#!/usr/bin/env python3
"""
9专家AI系统测试脚本
直接测试专家系统功能，不依赖API
"""

import sys
import os
import asyncio
import random
from datetime import datetime

# 添加backend-v3到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-v3'))

from app.experts import (
    expert_manager,
    TimeFrame,
    MainForceExpert,
    VolumeAnalysisExpert,
    TechnicalIndicatorExpert,
    MomentumExpert,
    TrendExpert,
    SupportResistanceExpert,
    PatternRecognitionExpert,
    VolatilityExpert,
    MarketSentimentExpert
)


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text):
    """打印小节标题"""
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def generate_market_data(symbol="2330"):
    """生成模拟市场数据"""
    current_price = random.uniform(450, 550)
    open_price = current_price * random.uniform(0.98, 1.02)
    high = max(current_price, open_price) * random.uniform(1.0, 1.02)
    low = min(current_price, open_price) * random.uniform(0.98, 1.0)
    
    return {
        # 基础数据
        "volume": random.randint(10000000, 50000000),
        "avg_volume": 20000000,
        "large_buy_orders": random.randint(500, 2000),
        "large_sell_orders": random.randint(500, 2000),
        "price_change_percent": random.uniform(-0.05, 0.05),
        "bid_volume": random.randint(50000, 200000),
        "ask_volume": random.randint(50000, 200000),
        
        # 技术指标
        "current_price": current_price,
        "ma5": current_price * random.uniform(0.98, 1.02),
        "ma20": current_price * random.uniform(0.95, 1.05),
        "ma60": current_price * random.uniform(0.90, 1.10),
        "rsi": random.uniform(30, 70),
        "macd": random.uniform(-5, 5),
        "macd_signal": random.uniform(-5, 5),
        "macd_histogram": random.uniform(-2, 2),
        
        # 动量数据
        "price_change_1d": random.uniform(-0.05, 0.05),
        "price_change_5d": random.uniform(-0.10, 0.10),
        "volume_change": random.uniform(-0.5, 1.0),
        
        # 52周高低点
        "high_52w": current_price * random.uniform(1.1, 1.3),
        "low_52w": current_price * random.uniform(0.7, 0.9),
        
        # K线数据（形态识别）
        "open": open_price,
        "high": high,
        "low": low,
        "close": current_price,
        "prev_close": current_price * random.uniform(0.97, 1.03),
        "prev_high": high * random.uniform(0.98, 1.02),
        "prev_low": low * random.uniform(0.98, 1.02),
        
        # 波动率数据
        "atr": current_price * random.uniform(0.01, 0.03),
        "atr_avg": current_price * 0.02,
        "bb_upper": current_price * 1.05,
        "bb_lower": current_price * 0.95,
        "bb_middle": current_price,
        
        # 市场情绪数据
        "advance_decline_ratio": random.uniform(0.5, 2.0),
        "value_change": random.uniform(-0.3, 0.5),
        "foreign_net_buy": random.uniform(-500, 500),
        "fear_greed_index": random.uniform(20, 80),
    }


async def test_individual_experts(symbol, market_data):
    """测试单个专家"""
    print_section("📊 单个专家分析结果")
    
    experts = [
        MainForceExpert(),
        VolumeAnalysisExpert(),
        TechnicalIndicatorExpert(),
        MomentumExpert(),
        TrendExpert(),
        SupportResistanceExpert(),
        PatternRecognitionExpert(),
        VolatilityExpert(),
        MarketSentimentExpert()
    ]
    
    signals = []
    
    for i, expert in enumerate(experts, 1):
        signal = await expert.analyze(symbol, TimeFrame.D1, market_data)
        
        if signal:
            signals.append(signal)
            print(f"\n{i}. {signal.expert_name}")
            print(f"   信号类型: {signal.signal_type.value.upper()}")
            print(f"   信号强度: {signal.strength:.2%}")
            print(f"   置信度: {signal.confidence:.2%}")
            print(f"   推理: {signal.reasoning}")
        else:
            print(f"\n{i}. {expert.name}")
            print(f"   信号类型: 无信号")
    
    return signals


async def test_expert_manager(symbol, market_data):
    """测试专家管理器（综合分析）"""
    print_section("🤖 综合分析结果（9专家协同）")
    
    result = await expert_manager.analyze_stock(symbol, TimeFrame.D1, market_data)
    
    print(f"\n📈 综合信号: {result['overall_signal'].upper()}")
    print(f"💪 综合强度: {result['overall_strength']:.2%}")
    print(f"✅ 综合置信度: {result['overall_confidence']:.2%}")
    print(f"🤖 参与专家: {result['expert_count']}/{result['total_experts']}")
    
    print(f"\n📊 专家共识:")
    consensus = result['consensus']
    print(f"   看多: {consensus['buy_count']} 个")
    print(f"   看空: {consensus['sell_count']} 个")
    print(f"   观望: {consensus['hold_count']} 个")
    
    # 显示每个专家的信号
    print(f"\n📋 专家详情:")
    for i, signal in enumerate(result['signals'], 1):
        print(f"   {i}. {signal['expert_name']}: {signal['signal_type'].upper()} "
              f"(强度{signal['strength']:.0%}, 置信{signal['confidence']:.0%})")
    
    return result


def display_market_data(symbol, market_data):
    """显示市场数据摘要"""
    print_section(f"📊 {symbol} 市场数据")
    
    print(f"\n价格信息:")
    print(f"   当前价: {market_data['current_price']:.2f}")
    print(f"   开盘价: {market_data['open']:.2f}")
    print(f"   最高价: {market_data['high']:.2f}")
    print(f"   最低价: {market_data['low']:.2f}")
    print(f"   涨跌幅: {market_data['price_change_percent']:.2%}")
    
    print(f"\n成交量:")
    print(f"   当日: {market_data['volume']:,}")
    print(f"   平均: {market_data['avg_volume']:,}")
    
    print(f"\n技术指标:")
    print(f"   MA5:  {market_data['ma5']:.2f}")
    print(f"   MA20: {market_data['ma20']:.2f}")
    print(f"   MA60: {market_data['ma60']:.2f}")
    print(f"   RSI:  {market_data['rsi']:.1f}")


async def main():
    """主测试函数"""
    print_header("🤖 9专家AI系统测试")
    
    # 设置参数
    symbol = "2330"
    print(f"\n测试股票: {symbol} (台积电)")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 生成市场数据
    market_data = generate_market_data(symbol)
    
    # 显示市场数据
    display_market_data(symbol, market_data)
    
    # 1. 测试单个专家
    signals = await test_individual_experts(symbol, market_data)
    
    # 2. 测试专家管理器
    result = await test_expert_manager(symbol, market_data)
    
    # 最终总结
    print_section("📝 测试总结")
    print(f"\n✅ 已注册专家数: {result['total_experts']}")
    print(f"✅ 产生信号专家: {result['expert_count']}")
    print(f"✅ 综合分析完成")
    
    # 根据综合信号给出建议
    signal = result['overall_signal']
    strength = result['overall_strength']
    confidence = result['overall_confidence']
    
    print(f"\n🎯 投资建议:")
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
    
    print(f"   {emoji} {advice}")
    print(f"   综合评分: {strength:.0%} (置信度{confidence:.0%})")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
