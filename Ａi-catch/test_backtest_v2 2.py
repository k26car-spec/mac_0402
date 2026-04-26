#!/usr/bin/env python3
"""
增强版历史回测系统 v2.0
Enhanced Backtesting Engine with Real Historical Data

新增功能:
1. 真实历史数据逐日回测
2. 止损止盈机制
3. 仓位管理
4. 详细交易记录
5. 多股票组合回测
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-v3'))

from app.experts import expert_manager, TimeFrame


class Trade:
    """交易记录"""
    def __init__(self, symbol: str, entry_date, entry_price: float, 
                 signal: str, position_size: float):
        self.symbol = symbol
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.signal = signal  # 'buy' or 'sell' (short)
        self.position_size = position_size
        self.exit_date = None
        self.exit_price = None
        self.profit = 0.0
        self.profit_pct = 0.0
        self.exit_reason = None
    
    def close(self, exit_date, exit_price: float, reason: str):
        """平仓"""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        
        if self.signal == 'buy':
            self.profit = (exit_price - self.entry_price) * self.position_size
            self.profit_pct = (exit_price - self.entry_price) / self.entry_price
        else:  # short
            self.profit = (self.entry_price - exit_price) * self.position_size
            self.profit_pct = (self.entry_price - exit_price) / self.entry_price


class EnhancedBacktester:
    """增强版回测引擎"""
    
    def __init__(self, initial_capital: float = 100000, 
                 stop_loss_pct: float = 0.03,
                 take_profit_pct: float = 0.05,
                 max_position_pct: float = 0.3):
        """
        初始化
        
        Args:
            initial_capital: 初始资金
            stop_loss_pct: 止损百分比 (3%)
            take_profit_pct: 止盈百分比 (5%)
            max_position_pct: 最大单个仓位比例 (30%)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_position_pct = max_position_pct
        
        self.trades: List[Trade] = []
        self.open_trades: List[Trade] = []
        self.daily_capital = []
    
    async def backtest_historical(self, symbol: str, start_date: str, end_date: str):
        """
        基于真实历史数据的回测
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 "YYYY-MM-DD"
            end_date: 结束日期 "YYYY-MM-DD"
        """
        print(f"\n{'='*70}")
        print(f"🔍 {symbol} 历史回测 v2.0")
        print(f"期间: {start_date} 到 {end_date}")
        print(f"初始资金: ${self.initial_capital:,.0f}")
        print(f"{'='*70}")
        
        # 下载历史数据
        print(f"\n📊 下载历史数据...")
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            print(f"❌ 无法获取{symbol}的历史数据")
            return None
        
        print(f"✅ 成功获取{len(hist)}天数据")
        
        # 逐日回测
        print(f"\n🤖 开始逐日AI分析...")
        
        for i in range(60, len(hist)):  # 需要60天用于计算MA60
            current_date = hist.index[i]
            current_data = hist.iloc[i]
            
            # 准备市场数据
            market_data = self._prepare_market_data(hist, i)
            
            # 运行AI分析
            analysis = await expert_manager.analyze_stock(
                symbol,
                TimeFrame.D1,
                market_data
            )
            
            # 检查开仓条件
            await self._check_entry_signal(
                symbol, current_date, current_data, analysis
            )
            
            # 检查平仓条件
            await self._check_exit_conditions(
                current_date, current_data
            )
            
            # 记录每日资金
            self.daily_capital.append({
                'date': current_date,
                'capital': self.capital,
                'open_positions': len(self.open_trades)
            })
        
        # 关闭所有开仓
        for trade in self.open_trades[:]:
            trade.close(hist.index[-1], hist.iloc[-1]['Close'], 'End of period')
            self.trades.append(trade)
            self.open_trades.remove(trade)
        
        # 生成报告
        return self._generate_report(symbol, hist)
    
    def _prepare_market_data(self, hist: pd.DataFrame, index: int) -> Dict:
        """准备市场数据"""
        current = hist.iloc[index]
        prev = hist.iloc[index-1] if index > 0 else current
        
        # 计算MA
        ma5 = hist['Close'].iloc[max(0, index-5):index+1].mean()
        ma20 = hist['Close'].iloc[max(0, index-20):index+1].mean()
        ma60 = hist['Close'].iloc[max(0, index-60):index+1].mean()
        
        return {
            "current_price": float(current['Close']),
            "open": float(current['Open']),
            "high": float(current['High']),
            "low": float(current['Low']),
            "volume": int(current['Volume']),
            "prev_close": float(prev['Close']),
            "prev_high": float(prev['High']),
            "prev_low": float(prev['Low']),
            "price_change_percent": float((current['Close'] - prev['Close']) / prev['Close']),
            "avg_volume": int(hist['Volume'].iloc[max(0, index-20):index+1].mean()),
            "ma5": float(ma5),
            "ma20": float(ma20),
            "ma60": float(ma60),
            "high_52w": float(hist['High'].iloc[max(0, index-252):index+1].max()),
            "low_52w": float(hist['Low'].iloc[max(0, index-252):index+1].min()),
            # 补充其他字段
            "large_buy_orders": int(current['Volume'] * 0.05),
            "large_sell_orders": int(current['Volume'] * 0.05),
            "bid_volume": int(current['Volume'] * 0.4),
            "ask_volume": int(current['Volume'] * 0.4),
            "price_change_1d": float((current['Close'] - prev['Close']) / prev['Close']),
            "price_change_5d": float((current['Close'] - prev['Close']) / prev['Close']) * 2,
            "volume_change": 0.1,
            "atr": float(current['Close'] * 0.02),
            "atr_avg": float(current['Close'] * 0.02),
            "bb_upper": float(current['Close'] * 1.05),
            "bb_lower": float(current['Close'] * 0.95),
            "bb_middle": float(current['Close']),
            "advance_decline_ratio": 1.2,
            "value_change": 0.1,
            "foreign_net_buy": 100,
            "fear_greed_index": 50,
            "close": float(current['Close']),
        }
    
    async def _check_entry_signal(self, symbol: str, date, data, analysis):
        """检查开仓信号"""
        signal = analysis['overall_signal']
        confidence = analysis['overall_confidence']
        
        # 只有高置信度信号才开仓
        if confidence < 0.7:
            return
        
        # 计算仓位大小
        if signal in ['strong_buy', 'buy']:
            available_capital = self.capital * self.max_position_pct
            position_size = int(available_capital / data['Close'])
            
            if position_size > 0:
                trade = Trade(
                    symbol, date, data['Close'], 'buy', position_size
                )
                self.open_trades.append(trade)
                self.capital -= position_size * data['Close']
                
        elif signal in ['strong_sell', 'sell']:
            # 做空信号（简化处理）
            available_capital = self.capital * self.max_position_pct
            position_size = int(available_capital / data['Close'])
            
            if position_size > 0:
                trade = Trade(
                    symbol, date, data['Close'], 'sell', position_size
                )
                self.open_trades.append(trade)
                self.capital -= position_size * data['Close']
    
    async def _check_exit_conditions(self, date, data):
        """检查平仓条件"""
        for trade in self.open_trades[:]:
            current_price = data['Close']
            
            # 计算盈亏
            if trade.signal == 'buy':
                profit_pct = (current_price - trade.entry_price) / trade.entry_price
            else:  # short
                profit_pct = (trade.entry_price - current_price) / trade.entry_price
            
            # 止损
            if profit_pct < -self.stop_loss_pct:
                trade.close(date, current_price, 'Stop Loss')
                self.capital += trade.position_size * current_price
                self.trades.append(trade)
                self.open_trades.remove(trade)
                continue
            
            # 止盈
            if profit_pct > self.take_profit_pct:
                trade.close(date, current_price, 'Take Profit')
                self.capital += trade.position_size * current_price
                self.trades.append(trade)
                self.open_trades.remove(trade)
                continue
    
    def _generate_report(self, symbol: str, hist: pd.DataFrame) -> Dict:
        """生成回测报告"""
        if not self.trades:
            return {
                'symbol': symbol,
                'total_trades': 0,
                'message': '期间无交易'
            }
        
        # 计算指标
        winning_trades = [t for t in self.trades if t.profit > 0]
        losing_trades = [t for t in self.trades if t.profit <= 0]
        
        total_profit = sum(t.profit for t in self.trades)
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        avg_win = sum(t.profit for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.profit for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        final_capital = self.capital
        roi = (final_capital - self.initial_capital) / self.initial_capital
        
        # 打印报告
        print(f"\n{'='*70}")
        print(f"📈 {symbol} 回测报告")
        print(f"{'='*70}")
        
        print(f"\n💰 资金情况:")
        print(f"   初始资金: ${self.initial_capital:,.0f}")
        print(f"   最终资金: ${final_capital:,.0f}")
        print(f"   总盈亏: ${total_profit:,.0f}")
        print(f"   投资回报率: {roi:.2%}")
        
        print(f"\n📊 交易统计:")
        print(f"   总交易次数: {len(self.trades)}")
        print(f"   获利交易: {len(winning_trades)} ({len(winning_trades)/len(self.trades):.1%})")
        print(f"   亏损交易: {len(losing_trades)} ({len(losing_trades)/len(self.trades):.1%})")
        print(f"   胜率: {win_rate:.2%}")
        
        print(f"\n💵 盈亏分析:")
        print(f"   平均获利: ${avg_win:,.0f}")
        print(f"   平均亏损: ${avg_loss:,.0f}")
        if avg_loss != 0:
            print(f"   盈亏比: {abs(avg_win/avg_loss):.2f}")
        
        # 最佳/最差交易
        if self.trades:
            best_trade = max(self.trades, key=lambda t: t.profit)
            worst_trade = min(self.trades, key=lambda t: t.profit)
            
            print(f"\n🏆 最佳交易:")
            print(f"   日期: {best_trade.entry_date.date()}")
            print(f"   盈利: ${best_trade.profit:,.0f} ({best_trade.profit_pct:.2%})")
            
            print(f"\n📉 最差交易:")
            print(f"   日期: {worst_trade.entry_date.date()}")
            print(f"   亏损: ${worst_trade.profit:,.0f} ({worst_trade.profit_pct:.2%})")
        
        print(f"\n{'='*70}")
        
        return {
            'symbol': symbol,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'roi': roi,
            'final_capital': final_capital,
            'trades': self.trades
        }


async def main():
    """主函数"""
    
    print("\n" + "="*70)
    print("🚀 增强版历史回测系统 v2.0")
    print("="*70)
    
    # 创建回测器
    backtester = EnhancedBacktester(
        initial_capital=100000,
        stop_loss_pct=0.03,  # 3% 止损
        take_profit_pct=0.05,  # 5% 止盈
        max_position_pct=0.3  # 30% 最大仓位
    )
    
    # 回测 2330
    result = await backtester.backtest_historical(
        symbol="2330",
        start_date="2024-09-01",
        end_date="2024-12-16"
    )
    
    print("\n✅ 回测完成！")


if __name__ == "__main__":
    asyncio.run(main())
