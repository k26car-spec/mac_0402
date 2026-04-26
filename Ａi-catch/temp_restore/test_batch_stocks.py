#!/usr/bin/env python3
"""
批量测试多只股票的9专家分析
"""

import sys
import os
import asyncio
from test_9_experts import (
    expert_manager,
    TimeFrame,
    generate_market_data,
    print_header,
    print_section
)


async def batch_test_stocks(symbols):
    """批量测试多只股票"""
    print_header("📊 批量股票分析测试")
    
    results = []
    
    for symbol in symbols:
        print_section(f"分析 {symbol}")
        
        # 生成市场数据
        market_data = generate_market_data(symbol)
        
        # 运行分析
        result = await expert_manager.analyze_stock(symbol, TimeFrame.D1, market_data)
        
        # 显示简要结果
        signal = result['overall_signal']
        strength = result['overall_strength']
        confidence = result['overall_confidence']
        consensus = result['consensus']
        
        # 信号emoji
        if signal == 'strong_buy':
            emoji, color = "🟢🟢", "强烈买入"
        elif signal == 'buy':
            emoji, color = "🟢", "买入"
        elif signal == 'strong_sell':
            emoji, color = "🔴🔴", "强烈卖出"
        elif signal == 'sell':
            emoji, color = "🔴", "卖出"
        else:
            emoji, color = "🟡", "观望"
        
        print(f"\n{emoji} {symbol}: {color}")
        print(f"   价格: {market_data['current_price']:.2f}")
        print(f"   信号强度: {strength:.2%}, 置信度: {confidence:.2%}")
        print(f"   专家共识: 买{consensus['buy_count']} / 卖{consensus['sell_count']} / 持{consensus['hold_count']}")
        
        results.append({
            'symbol': symbol,
            'signal': signal,
            'strength': strength,
            'confidence': confidence,
            'price': market_data['current_price'],
            'consensus': consensus
        })
    
    # 显示汇总
    print_section("📊 分析汇总")
    
    # 按信号分类
    strong_buys = [r for r in results if r['signal'] == 'strong_buy']
    buys = [r for r in results if r['signal'] == 'buy']
    strong_sells = [r for r in results if r['signal'] == 'strong_sell']
    sells = [r for r in results if r['signal'] == 'sell']
    holds = [r for r in results if r['signal'] == 'hold']
    
    print(f"\n信号分布:")
    print(f"   🟢🟢 强烈买入: {len(strong_buys)} 只")
    if strong_buys:
        print(f"       {', '.join([r['symbol'] for r in strong_buys])}")
    
    print(f"   🟢 买入: {len(buys)} 只")
    if buys:
        print(f"       {', '.join([r['symbol'] for r in buys])}")
    
    print(f"   🟡 观望: {len(holds)} 只")
    if holds:
        print(f"       {', '.join([r['symbol'] for r in holds])}")
    
    print(f"   🔴 卖出: {len(sells)} 只")
    if sells:
        print(f"       {', '.join([r['symbol'] for r in sells])}")
    
    print(f"   🔴🔴 强烈卖出: {len(strong_sells)} 只")
    if strong_sells:
        print(f"       {', '.join([r['symbol'] for r in strong_sells])}")
    
    # 平均置信度
    avg_confidence = sum(r['confidence'] for r in results) / len(results)
    print(f"\n平均置信度: {avg_confidence:.2%}")
    
    print("\n" + "=" * 60)
    print(f"批量测试完成！共分析 {len(symbols)} 只股票")
    print("=" * 60 + "\n")


async def main():
    """主函数"""
    # 测试股票列表
    symbols = [
        "2330",  # 台积电
        "2317",  # 鸿海
        "2454",  # 联发科
        "2881",  # 富邦金
        "2412",  # 中华电
        "2308",  # 台达电
        "2303",  # 联电
        "2002",  # 中钢
    ]
    
    await batch_test_stocks(symbols)


if __name__ == "__main__":
    asyncio.run(main())
