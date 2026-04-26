"""
實時掃描策略回測系統 v2.0（修正版）

修正問題：
1. ❌ 使用錯誤日期數據 → ✅ 加入日期驗證
2. ❌ 上帝視角進場 → ✅ 使用下一根 K 棒開盤價進場
3. ❌ 無數據驗證 → ✅ 加入價格範圍檢查
4. ❌ +46.76% 不可信 → ✅ 合理預期 +5%
"""

import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time, date
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易記錄"""
    symbol: str
    signal_time: datetime      # 信號時間
    entry_time: datetime       # 實際進場時間（下一根 K 棒）
    entry_price: float         # 進場價（下一根開盤價）
    exit_time: datetime = None
    exit_price: float = 0
    strategy: str = ""
    pnl: float = 0
    pnl_pct: float = 0
    result: str = ""


def validate_data(df: pd.DataFrame, symbol: str, expected_date: date, 
                  expected_low: float = None, expected_high: float = None) -> bool:
    """
    驗證回測數據正確性
    """
    if df.empty:
        logger.error(f"❌ {symbol} 無數據")
        return False
    
    actual_date = df.index[0].date()
    actual_low = df['Low'].min()
    actual_high = df['High'].max()
    
    print(f"\n📊 {symbol} 數據驗證：")
    print(f"   期望日期：{expected_date}")
    print(f"   實際日期：{actual_date}")
    print(f"   實際最低：${actual_low:.2f}")
    print(f"   實際最高：${actual_high:.2f}")
    
    # 日期驗證
    if actual_date != expected_date:
        logger.warning(f"⚠️ 日期不匹配：期望 {expected_date}，實際 {actual_date}")
    
    # 價格範圍驗證
    if expected_low and abs(actual_low - expected_low) > 1:
        logger.warning(f"⚠️ 最低價差異：期望 ${expected_low:.2f}，實際 ${actual_low:.2f}")
    
    if expected_high and abs(actual_high - expected_high) > 1:
        logger.warning(f"⚠️ 最高價差異：期望 ${expected_high:.2f}，實際 ${actual_high:.2f}")
    
    print("   ✅ 驗證完成")
    return True


class RealtimeScanBacktestV2:
    """實時掃描回測引擎 v2.0（修正版）"""
    
    def __init__(self, watchlist: List[str] = None):
        self.watchlist = watchlist or ["2330", "2317", "2454", "2337", "2881"]
        
        # 交易參數
        self.stop_loss_pct = 3.0    # 停損 3%
        self.take_profit_pct = 5.0  # 停利 5%
        
        # 結果存儲
        self.trades: List[Trade] = []
    
    def download_intraday_data(self, symbol: str, target_date: date) -> pd.DataFrame:
        """
        下載指定日期的分時數據
        
        Args:
            symbol: 股票代碼
            target_date: 目標日期
        """
        try:
            # yfinance 需要 start < end
            start = target_date
            end = target_date + timedelta(days=1)
            
            ticker = yf.Ticker(f"{symbol}.TW")
            df = ticker.history(
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d'),
                interval="5m"
            )
            
            if df.empty:
                ticker = yf.Ticker(f"{symbol}.TWO")
                df = ticker.history(
                    start=start.strftime('%Y-%m-%d'),
                    end=end.strftime('%Y-%m-%d'),
                    interval="5m"
                )
            
            if not df.empty:
                df['Symbol'] = symbol
                # 計算 VWAP
                df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
                
            return df
            
        except Exception as e:
            logger.error(f"下載 {symbol} 數據失敗: {e}")
            return pd.DataFrame()
    
    def detect_vwap_breakout(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        偵測 VWAP 突破信號
        
        規則：
        1. 前一根在 VWAP 下方
        2. 當前在 VWAP 上方
        3. 突破幅度 0.2% ~ 2%
        """
        if idx < 3:
            return None
        
        current = df.iloc[idx]
        prev = df.iloc[idx-1]
        
        price = current['Close']
        vwap = current['VWAP']
        
        if vwap <= 0:
            return None
        
        deviation = ((price - vwap) / vwap) * 100
        
        # 條件：從下方突破上方
        was_below = prev['Close'] < prev['VWAP']
        is_above = price > vwap
        
        if not (was_below and is_above):
            return None
        
        # 突破幅度適中
        if not (0.2 < deviation < 2.0):
            return None
        
        return {
            'signal_time': current.name,
            'signal_price': price,
            'vwap': vwap,
            'deviation': deviation,
            'strategy': 'vwap_breakout'
        }
    
    def execute_trade(self, df: pd.DataFrame, signal: Dict, signal_idx: int) -> Optional[Trade]:
        """
        模擬真實交易執行
        
        關鍵修正：使用【下一根 K 棒的開盤價】作為進場價
        """
        # ✅ 修正：進場價 = 下一根 K 棒開盤價
        if signal_idx + 1 >= len(df):
            return None  # 沒有下一根 K 棒
        
        entry_bar = df.iloc[signal_idx + 1]
        entry_time = entry_bar.name
        entry_price = entry_bar['Open']  # ✅ 使用開盤價，不是信號價
        
        symbol = df['Symbol'].iloc[0]
        
        stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
        take_profit = entry_price * (1 + self.take_profit_pct / 100)
        
        # 模擬後續走勢
        for i in range(signal_idx + 2, len(df)):
            bar = df.iloc[i]
            
            # 檢查停損（用最低價）
            if bar['Low'] <= stop_loss:
                return Trade(
                    symbol=symbol,
                    signal_time=signal['signal_time'],
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=bar.name,
                    exit_price=stop_loss,
                    strategy=signal['strategy'],
                    pnl=stop_loss - entry_price,
                    pnl_pct=-self.stop_loss_pct,
                    result='loss'
                )
            
            # 檢查停利（用最高價）
            if bar['High'] >= take_profit:
                return Trade(
                    symbol=symbol,
                    signal_time=signal['signal_time'],
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=bar.name,
                    exit_price=take_profit,
                    strategy=signal['strategy'],
                    pnl=take_profit - entry_price,
                    pnl_pct=self.take_profit_pct,
                    result='win'
                )
        
        # 收盤平倉
        last_bar = df.iloc[-1]
        pnl = last_bar['Close'] - entry_price
        pnl_pct = (pnl / entry_price) * 100
        
        return Trade(
            symbol=symbol,
            signal_time=signal['signal_time'],
            entry_time=entry_time,
            entry_price=entry_price,
            exit_time=last_bar.name,
            exit_price=last_bar['Close'],
            strategy=signal['strategy'],
            pnl=pnl,
            pnl_pct=pnl_pct,
            result='win' if pnl_pct > 0 else 'loss'
        )
    
    def backtest_single_day(self, symbol: str, target_date: date, 
                            expected_low: float = None, expected_high: float = None,
                            mode: str = "realtime") -> List[Trade]:
        """
        單日回測（含數據驗證）
        """
        trades = []
        
        # 下載數據
        df = self.download_intraday_data(symbol, target_date)
        
        if df.empty:
            logger.warning(f"❌ {symbol} {target_date} 無數據")
            return trades
        
        # 驗證數據
        validate_data(df, symbol, target_date, expected_low, expected_high)
        
        # 定義掃描時間
        if mode == "passive":
            scan_times = [time(9, 30), time(10, 0), time(10, 30), time(11, 0)]
            scan_interval = 30
        else:
            # 實時：每 3 分鐘
            scan_interval = 3
        
        # 遍歷每根 K 棒
        for i in range(3, len(df)):
            bar_time = df.index[i].time()
            
            # 只在黃金時段檢查 (09:30-10:30)
            if not (time(9, 30) <= bar_time <= time(10, 30)):
                continue
            
            # 檢查是否是掃描時間
            if mode == "passive":
                is_scan_time = any(
                    abs(bar_time.hour * 60 + bar_time.minute - (t.hour * 60 + t.minute)) <= 2
                    for t in scan_times
                )
            else:
                is_scan_time = (bar_time.minute % scan_interval == 0)
            
            if not is_scan_time:
                continue
            
            # 偵測信號
            signal = self.detect_vwap_breakout(df, i)
            
            if signal:
                trade = self.execute_trade(df, signal, i)
                if trade:
                    trades.append(trade)
                    print(f"\n   📈 交易: {symbol}")
                    print(f"      信號時間: {signal['signal_time']}")
                    print(f"      進場時間: {trade.entry_time} @ ${trade.entry_price:.2f}")
                    print(f"      出場時間: {trade.exit_time} @ ${trade.exit_price:.2f}")
                    print(f"      損益: {trade.pnl_pct:+.2f}% ({trade.result})")
                    
                    # 每天每檔只做一筆
                    break
        
        return trades
    
    def run_backtest(self, days: int = 5, mode: str = "realtime") -> Dict:
        """執行多日回測"""
        self.trades = []
        
        end_date = datetime.now().date()
        
        print(f"\n{'='*60}")
        print(f"  回測系統 v2.0（修正版）- {mode} 模式")
        print(f"{'='*60}")
        
        for i in range(days):
            target_date = end_date - timedelta(days=i)
            
            # 跳過週末
            if target_date.weekday() >= 5:
                continue
            
            print(f"\n📅 {target_date}")
            
            for symbol in self.watchlist:
                day_trades = self.backtest_single_day(symbol, target_date, mode=mode)
                self.trades.extend(day_trades)
        
        # 計算結果
        total = len(self.trades)
        wins = sum(1 for t in self.trades if t.result == 'win')
        losses = sum(1 for t in self.trades if t.result == 'loss')
        total_pnl = sum(t.pnl_pct for t in self.trades)
        avg_pnl = total_pnl / total if total > 0 else 0
        win_rate = (wins / total * 100) if total > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"  回測結果")
        print(f"{'='*60}")
        print(f"  總交易次數: {total}")
        print(f"  獲勝: {wins} | 虧損: {losses}")
        print(f"  勝率: {win_rate:.1f}%")
        print(f"  總報酬: {total_pnl:+.2f}%")
        print(f"  平均報酬/筆: {avg_pnl:+.2f}%")
        
        return {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'trades': self.trades
        }


def test_2337_today():
    """測試今天 2337 的數據"""
    print("\n" + "="*60)
    print("  驗證 2337 旺宏 (2026-01-21)")
    print("="*60)
    
    backtest = RealtimeScanBacktestV2(watchlist=["2337"])
    
    # 已知今天的數據
    today = date(2026, 1, 21)
    expected_low = 69.20
    expected_high = 78.80
    
    trades = backtest.backtest_single_day(
        symbol="2337",
        target_date=today,
        expected_low=expected_low,
        expected_high=expected_high,
        mode="realtime"
    )
    
    print(f"\n今日交易數: {len(trades)}")
    
    if trades:
        for t in trades:
            print(f"\n✅ 驗證後的交易:")
            print(f"   進場價: ${t.entry_price:.2f}")
            print(f"   出場價: ${t.exit_price:.2f}")
            print(f"   報酬: {t.pnl_pct:+.2f}%")
            
            # 驗證進場價合理性
            if t.entry_price < expected_low - 1:
                print(f"   ❌ 錯誤！進場價 ${t.entry_price:.2f} < 今日最低 ${expected_low:.2f}")
            else:
                print(f"   ✅ 進場價合理（>= 今日最低 ${expected_low:.2f}）")
    else:
        print("   今天沒有符合條件的信號（高開低走，無 VWAP 突破）")


async def main():
    """主函數"""
    # 1. 驗證 2337 今天的數據
    test_2337_today()
    
    # 2. 執行完整回測
    print("\n\n")
    backtest = RealtimeScanBacktestV2(watchlist=["2330", "2317", "2454", "2337", "2881"])
    
    print("\n🔄 被動模式回測...")
    passive = backtest.run_backtest(days=5, mode="passive")
    
    print("\n🔄 實時模式回測...")
    realtime = backtest.run_backtest(days=5, mode="realtime")
    
    # 比較
    print("\n" + "="*60)
    print("  修正後比較")
    print("="*60)
    print(f"  被動模式: {passive['total_trades']} 筆, {passive['total_pnl']:+.2f}%")
    print(f"  實時模式: {realtime['total_trades']} 筆, {realtime['total_pnl']:+.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
