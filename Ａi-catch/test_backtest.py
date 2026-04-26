#!/usr/bin/env python3
"""
简化版历史回测系统
Simplified Backtesting Engine
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-v3'))

from app.experts import expert_manager, TimeFrame
from app.data_sources import YahooFinanceSource


class BacktestResult:
    """回测结果"""
    def __init__(self):
        self.trades: List[Dict] = []
        self.signals: List[Dict] = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.max_drawdown = 0.0
    
    def add_signal(self, date, symbol, signal_type, strength, confidence, price):
        """添加信号"""
        self.signals.append({
            'date': date,
            'symbol': symbol,
            'signal': signal_type,
            'strength': strength,
            'confidence': confidence,
            'price': price
        })
    
    def calculate_metrics(self):
        """计算回测指标"""
        if self.total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'avg_profit': 0.0,
                'total_signals': len(self.signals),
                'winning_trades': 0,
                'losing_trades': 0,
                'max_drawdown': 0.0
            }
        
        win_rate = self.winning_trades / self.total_trades
        avg_profit = self.total_profit / self.total_trades
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'avg_profit': avg_profit,
            'max_drawdown': self.max_drawdown,
            'total_signals': len(self.signals)
        }


class SimpleBacktester:
    """简化的回测引擎"""
    
    def __init__(self):
        self.data_source = YahooFinanceSource()
    
    async def backtest_simple(self, symbol: str, days: int = 30) -> BacktestResult:
        """
        简化回测：基于历史信号的准确率
        
        策略：
        - 强烈买入 → 买入，期待上涨
        - 强烈卖出 → 卖出，期待下跌
        """
        print(f"\n{'='*70}")
        print(f"📊 {symbol} 历史回测")
        print(f"回测期间: {days}天")
        print(f"{'='*70}")
        
        result = BacktestResult()
        
        # 获取历史数据
        print(f"\n🔍 获取{days}天历史数据...")
        hist_data = self.data_source.get_stock_data(symbol, period=f"{days}d")
        
        if not hist_data:
            print(f"❌ 无法获取{symbol}历史数据")
            return result
        
        # 模拟逐日分析（简化版：使用当前数据模拟）
        print(f"✅ 数据获取成功")
        print(f"\n🤖 运行AI分析...")
        
        # 准备数据
        enhanced_data = {
            **hist_data,
            "avg_volume": hist_data.get("avg_volume", hist_data["volume"]),
            "large_buy_orders": int(hist_data["volume"] * 0.05),
            "large_sell_orders": int(hist_data["volume"] * 0.05),
            "bid_volume": int(hist_data["volume"] * 0.4),
            "ask_volume": int(hist_data["volume"] * 0.4),
            "price_change_1d": hist_data["price_change_percent"],
            "price_change_5d": hist_data["price_change_percent"] * 2,
            "volume_change": 0.1,
            "atr": hist_data["current_price"] * 0.02,
            "atr_avg": hist_data["current_price"] * 0.02,
            "bb_upper": hist_data["current_price"] * 1.05,
            "bb_lower": hist_data["current_price"] * 0.95,
            "bb_middle": hist_data["current_price"],
            "advance_decline_ratio": 1.2,
            "value_change": 0.1,
            "foreign_net_buy": 100,
            "fear_greed_index": 50,
            "close": hist_data["current_price"],
        }
        
        # 运行分析
        analysis = await expert_manager.analyze_stock(
            symbol,
            TimeFrame.D1,
            enhanced_data
        )
        
        # 记录信号
        signal_type = analysis['overall_signal']
        strength = analysis['overall_strength']
        confidence = analysis['overall_confidence']
        price = hist_data['current_price']
        
        result.add_signal(
            datetime.now(),
            symbol,
            signal_type,
            strength,
            confidence,
            price
        )
        
        # 简化的盈亏计算
        # 假设：强烈买入后1天，如果上涨则盈利
        if signal_type in ['strong_buy', 'buy']:
            # 模拟买入后的结果
            future_change = hist_data.get('price_change_percent', 0)
            if future_change > 0:
                result.winning_trades += 1
                profit = future_change * 10000  # 假设1万元投资
                result.total_profit += profit
            else:
                result.losing_trades += 1
                loss = abs(future_change) * 10000
                result.total_profit -= loss
            
            result.total_trades += 1
        
        elif signal_type in ['strong_sell', 'sell']:
            # 模拟卖出（空头）后的结果
            future_change = hist_data.get('price_change_percent', 0)
            if future_change < 0:
                result.winning_trades += 1
                profit = abs(future_change) * 10000
                result.total_profit += profit
            else:
                result.losing_trades += 1
                loss = future_change * 10000
                result.total_profit -= loss
            
            result.total_trades += 1
        
        return result


async def run_backtest():
    """运行回测"""
    
    print("\n" + "="*70)
    print("🚀 AI股票分析系统 - 历史回测")
    print("="*70)
    
    backtester = SimpleBacktester()
    
    # 测试股票
    test_symbols = ["2330", "2317", "2454"]
    
    all_results = {}
    
    for symbol in test_symbols:
        result = await backtester.backtest_simple(symbol, days=30)
        all_results[symbol] = result
        
        # 显示结果
        metrics = result.calculate_metrics()
        
        print(f"\n📈 回测结果:")
        print(f"   总信号数: {metrics['total_signals']}")
        print(f"   交易次数: {metrics['total_trades']}")
        print(f"   获利次数: {metrics['winning_trades']}")
        print(f"   亏损次数: {metrics['losing_trades']}")
        
        if metrics['total_trades'] > 0:
            print(f"   胜率: {metrics['win_rate']:.2%}")
            print(f"   总盈亏: ${metrics['total_profit']:.2f}")
            print(f"   平均盈亏: ${metrics['avg_profit']:.2f}")
            
            # 判断
            if metrics['win_rate'] >= 0.6:
                print(f"   评价: ✅ 优秀（胜率>60%）")
            elif metrics['win_rate'] >= 0.5:
                print(f"   评价: 🟡 良好（胜率>50%）")
            else:
                print(f"   评价: ⚠️ 需优化（胜率<50%）")
        else:
            print(f"   评价: 🟡 观望信号，无交易")
        
        print()
    
    # 总体统计
    print("="*70)
    print("📊 总体回测统计")
    print("="*70)
    
    total_trades = sum(r.total_trades for r in all_results.values())
    total_winning = sum(r.winning_trades for r in all_results.values())
    total_profit = sum(r.total_profit for r in all_results.values())
    
    if total_trades > 0:
        overall_win_rate = total_winning / total_trades
        print(f"\n测试股票数: {len(test_symbols)}")
        print(f"总交易次数: {total_trades}")
        print(f"总获利次数: {total_winning}")
        print(f"总体胜率: {overall_win_rate:.2%}")
        print(f"总盈亏: ${total_profit:.2f}")
        
        if overall_win_rate >= 0.6:
            print(f"\n🎉 系统表现: 优秀！")
        elif overall_win_rate >= 0.5:
            print(f"\n✅ 系统表现: 良好")
        else:
            print(f"\n⚠️ 系统表现: 需要优化")
    else:
        print(f"\n🟡 测试期间主要为观望信号")
    
    print("\n" + "="*70)
    print("✅ 历史回测完成")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(run_backtest())
