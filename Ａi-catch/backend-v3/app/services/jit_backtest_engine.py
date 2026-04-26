"""
即時回測引擎 (Just-in-Time Backtest Engine)
=========================================
【Level 5.5 核心】：在任何交易執行前，先進行「閃電回測」。

這就像老手在下單前，腦海中瞬間閃過這支票過去幾次的表現。
如果這支票在這種型態下過去 1-2 年表現極差，直接放棄。
"""

import logging
import asyncio
from typing import Dict, Any, Optional
import yfinance as yf
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class JITBacktestEngine:
    """即時回測引擎：在交易前一秒學習"""

    @staticmethod
    async def run_instant_review(symbol: str, strategy: str, period: str = "1y") -> Dict:
        """
        對指定標的與策略執行閃電回測
        """
        try:
            # 1. 抓取歷史數據 (1年)
            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            ticker = yf.Ticker(f"{clean_symbol}.TW")
            hist = await asyncio.to_thread(ticker.history, period=period)
            
            if hist.empty or len(hist) < 100:
                ticker = yf.Ticker(f"{clean_symbol}.TWO")
                hist = await asyncio.to_thread(ticker.history, period=period)
                
            if hist.empty:
                return {'win_rate': 0.5, 'expectancy': 0, 'total': 0, 'confidence_adj': 0}

            # 2. 模擬策略執行 (簡化版邏輯)
            # 這裡我們模擬目標策略在過去 250 交易日的表現
            closes = hist['Close'].values
            highs = hist['High'].values
            lows = hist['Low'].values
            
            trades = []
            
            # 以簡單的 MA + Momentum 作為基準策略模擬
            # 可擴充為更精準的策略匹配
            ma20 = hist['Close'].rolling(20).mean().values
            
            for i in range(20, len(closes) - 5): # 至少留 5 天看結果
                # 簡單模擬進場條件：價格站上 MA20 且帶量
                if closes[i] > ma20[i] and closes[i] > closes[i-1]:
                    entry_price = closes[i]
                    # 模擬 3 天後的出貨 (或觸發 3% 停損)
                    exit_price = closes[i+3]
                    # 停損檢查
                    for j in range(1, 4):
                        if lows[i+j] < entry_price * 0.97:
                            exit_price = entry_price * 0.97
                            break
                    
                    pnl = (exit_price - entry_price) / entry_price * 100
                    trades.append(pnl)

            if not trades:
                return {'win_rate': 0.5, 'expectancy': 0, 'total': 0, 'confidence_adj': 0}

            win_rate = len([t for t in trades if t > 0]) / len(trades)
            expectancy = np.mean(trades)
            
            # 信心度調整：
            # 如果這支股票過去該策略表現極佳 (WR > 60%) +10
            # 如果過去表現極差 (WR < 45%) -20
            adj = 0
            if win_rate > 0.6: adj = 10
            elif win_rate < 0.45: adj = -20
            
            if expectancy < 0: adj -= 10 # 負期望值懲罰

            return {
                'symbol': symbol,
                'strategy': strategy,
                'win_rate': round(win_rate, 2),
                'expectancy': round(expectancy, 2),
                'total_trades': len(trades),
                'confidence_adj': adj,
                'message': f"📊 此標的歷史測評: {len(trades)}筆, 勝率{win_rate:.0%}, 期望值{expectancy:+.2f}%"
            }

        except Exception as e:
            logger.debug(f"即時回測失敗 {symbol}: {e}")
            return {'win_rate': 0.5, 'expectancy': 0, 'total': 0, 'confidence_adj': 0}

# 單例
jit_engine = JITBacktestEngine()
