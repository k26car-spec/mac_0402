"""
歷史回測模組
Backtesting Module

功能：
1. 使用歷史價格資料模擬交易
2. 計算策略勝率和報酬率
3. 分析最佳進出場條件
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class BacktestEngine:
    """歷史回測引擎"""
    
    def __init__(self):
        self.results = []
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0
    
    async def run_backtest(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        min_confidence: int = 60
    ) -> Dict:
        """
        執行歷史回測
        
        Args:
            symbols: 股票代碼列表
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            min_confidence: 最低信心度門檻
        """
        logger.info(f"🔄 開始回測: {len(symbols)} 檔股票, {start_date} ~ {end_date}")
        
        self.results = []
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0
        
        for symbol in symbols:
            try:
                await self._backtest_symbol(symbol, start_date, end_date, min_confidence)
            except Exception as e:
                logger.debug(f"回測 {symbol} 失敗: {e}")
        
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        avg_profit = (self.total_profit / self.total_trades) if self.total_trades > 0 else 0
        
        summary = {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.total_trades - self.winning_trades,
            "win_rate": round(win_rate, 2),
            "total_profit_pct": round(self.total_profit, 2),
            "avg_profit_pct": round(avg_profit, 2),
            "start_date": start_date,
            "end_date": end_date,
            "symbols_tested": len(symbols)
        }
        
        logger.info(f"✅ 回測完成: {self.total_trades} 筆交易, 勝率 {win_rate:.1f}%")
        
        return {
            "summary": summary,
            "trades": self.results[-50:]  # 最近50筆
        }
    
    async def _backtest_symbol(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        min_confidence: int
    ):
        """回測單一股票"""
        
        # 取得歷史資料
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty or len(hist) < 20:
            return
        
        # 計算技術指標
        hist['MA5'] = hist['Close'].rolling(5).mean()
        hist['MA10'] = hist['Close'].rolling(10).mean()
        hist['MA20'] = hist['Close'].rolling(20).mean()
        
        # KD 計算
        low_min = hist['Low'].rolling(9).min()
        high_max = hist['High'].rolling(9).max()
        rsv = 100 * (hist['Close'] - low_min) / (high_max - low_min)
        hist['K'] = rsv.ewm(span=3).mean()
        hist['D'] = hist['K'].ewm(span=3).mean()
        
        # 模擬交易
        position = None
        
        for i in range(25, len(hist) - 1):
            row = hist.iloc[i]
            next_row = hist.iloc[i + 1]
            
            price = row['Close']
            ma5 = row['MA5']
            ma10 = row['MA10']
            ma20 = row['MA20']
            k = row['K']
            d = row['D']
            
            # 計算信心度
            confidence = 0
            
            # 均線多頭
            if price > ma5 > ma10 > ma20:
                confidence += 35
            elif price > ma5 > ma10:
                confidence += 20
            
            # KD 向上
            if k > d and k > 20:
                confidence += 25
            
            # 成交量增加
            if row['Volume'] > hist['Volume'].iloc[i-5:i].mean() * 1.2:
                confidence += 15
            
            # 進場條件
            if position is None and confidence >= min_confidence:
                position = {
                    'entry_price': price,
                    'entry_date': row.name,
                    'confidence': confidence,
                    'stop_loss': price * 0.97,
                    'take_profit': price * 1.03
                }
            
            # 出場條件
            elif position is not None:
                # 停損
                if price <= position['stop_loss']:
                    profit_pct = (price - position['entry_price']) / position['entry_price'] * 100
                    self._record_trade(symbol, position, price, profit_pct, 'stop_loss')
                    position = None
                # 停利
                elif price >= position['take_profit']:
                    profit_pct = (price - position['entry_price']) / position['entry_price'] * 100
                    self._record_trade(symbol, position, price, profit_pct, 'take_profit')
                    position = None
                # 持倉超過 5 天強制出場
                elif (row.name - position['entry_date']).days >= 5:
                    profit_pct = (price - position['entry_price']) / position['entry_price'] * 100
                    self._record_trade(symbol, position, price, profit_pct, 'timeout')
                    position = None
    
    def _record_trade(self, symbol: str, position: Dict, exit_price: float, profit_pct: float, reason: str):
        """記錄交易"""
        self.total_trades += 1
        self.total_profit += profit_pct
        
        if profit_pct > 0:
            self.winning_trades += 1
        
        self.results.append({
            'symbol': symbol,
            'entry_price': round(position['entry_price'], 2),
            'exit_price': round(exit_price, 2),
            'profit_pct': round(profit_pct, 2),
            'confidence': position['confidence'],
            'reason': reason,
            'is_win': profit_pct > 0
        })


# 全域實例
backtest_engine = BacktestEngine()


async def run_quick_backtest(days: int = 30) -> Dict:
    """快速回測最近 N 天"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    # 使用監控清單的股票
    import json
    try:
        with open('/Users/Mac/Documents/ETF/AI/Ａi-catch/data/orb_watchlist.json', 'r') as f:
            data = json.load(f)
            symbols = data.get('watchlist', [])[:20]  # 只測前20檔
    except:
        symbols = ['2330', '2317', '2454', '3037', '2313']
    
    return await backtest_engine.run_backtest(symbols, start_date, end_date)
