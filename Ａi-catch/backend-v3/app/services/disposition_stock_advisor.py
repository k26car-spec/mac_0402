"""
處置股顧問分析系統

功能：
1. 處置股偵測（量能急凍）
2. MA5/MA10 技術分析
3. 乖離率計算
4. 黃金買點訊號
5. 精確操作策略

使用方式：
    from app.services.disposition_stock_advisor import disposition_advisor
    report = await disposition_advisor.analyze("2337")
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import io

logger = logging.getLogger(__name__)


class DispositionStockAdvisor:
    """處置股顧問分析系統"""
    
    def __init__(self):
        # 處置判斷參數
        self.disposition_vol_threshold = 0.4  # 量能低於高峰期 40% 視為處置
        self.low_volume_threshold = 4000  # 4000 張以下為低量（萬股）
        
        # 乖離判斷參數
        self.high_bias_threshold = 10  # 乖離 > 10% 視為過熱
        self.safe_buy_bias = 3  # 乖離 < 3% 視為安全買點
    
    async def analyze(self, symbol: str, days: int = 30) -> Dict:
        """
        分析股票是否為處置股並給出策略建議
        
        Args:
            symbol: 股票代碼
            days: 分析天數
        
        Returns:
            完整分析報告
        """
        try:
            # 獲取數據
            df = await self._fetch_data(symbol, days)
            
            if df is None or df.empty:
                return {"success": False, "error": f"無法獲取 {symbol} 數據"}
            
            # 計算指標
            df = self._calculate_indicators(df)
            
            # 獲取最新數據
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            
            price = last['Close']
            volume = last['Volume']
            ma5 = last['MA5']
            ma10 = last['MA10']
            bias = last['Bias_MA5']
            date_str = last.name.strftime('%Y-%m-%d')
            
            # 處置判斷
            is_disposition, recent_vol, max_vol, vol_ratio = self._check_disposition(df)
            
            # 趨勢判斷
            trend = self._analyze_trend(price, ma5, ma10, bias)
            
            # 買賣策略
            strategy = self._generate_strategy(
                price, ma5, ma10, bias, volume, prev['Volume'], 
                is_disposition
            )
            
            # 黃金買點判斷
            golden_buy = self._check_golden_buy(
                price, ma5, volume, prev['Volume'], is_disposition
            )
            
            return {
                "success": True,
                "symbol": symbol,
                "date": date_str,
                "price": round(price, 2),
                "volume": int(volume),
                "volume_shares": int(volume / 1000),  # 張
                
                # 技術指標
                "ma5": round(ma5, 2),
                "ma10": round(ma10, 2),
                "bias_ma5": round(bias, 2),
                
                # 處置判斷
                "is_disposition": is_disposition,
                "disposition_detail": {
                    "recent_avg_vol": int(recent_vol),
                    "peak_vol": int(max_vol),
                    "vol_ratio": round(vol_ratio * 100, 1),
                    "threshold": self.disposition_vol_threshold * 100
                },
                
                # 趨勢分析
                "trend": trend,
                
                # 買賣策略
                "strategy": strategy,
                
                # 黃金買點
                "golden_buy": golden_buy,
                
                # 完整報告
                "report": self._generate_report(
                    symbol, date_str, price, volume, ma5, ma10, bias,
                    is_disposition, recent_vol, max_vol, vol_ratio,
                    trend, strategy, golden_buy
                )
            }
            
        except Exception as e:
            logger.error(f"分析 {symbol} 失敗: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fetch_data(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """獲取股票數據"""
        try:
            # 嘗試台股
            ticker = yf.Ticker(f"{symbol}.TW")
            df = ticker.history(period=f"{days}d")
            
            if df.empty:
                # 嘗試上櫃
                ticker = yf.Ticker(f"{symbol}.TWO")
                df = ticker.history(period=f"{days}d")
            
            return df if not df.empty else None
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 數據失敗: {e}")
            return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標"""
        df = df.copy()
        
        # 移動平均
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        # 成交量均線
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        
        # 乖離率
        df['Bias_MA5'] = (df['Close'] - df['MA5']) / df['MA5'] * 100
        df['Bias_MA10'] = (df['Close'] - df['MA10']) / df['MA10'] * 100
        
        return df
    
    def _check_disposition(self, df: pd.DataFrame) -> Tuple[bool, float, float, float]:
        """
        判斷是否為處置股（量能急凍）
        
        Returns:
            (is_disposition, recent_avg_vol, max_vol, vol_ratio)
        """
        if len(df) < 10:
            return False, 0, 0, 1.0
        
        # 近 3 日平均量
        recent_vol = df['Volume'].tail(3).mean()
        
        # 過去 20 天最大量（排除最近 3 天）
        past_data = df['Volume'].iloc[-20:-3] if len(df) > 20 else df['Volume'].iloc[:-3]
        max_vol = past_data.max() if len(past_data) > 0 else df['Volume'].max()
        
        # 量比
        vol_ratio = recent_vol / max_vol if max_vol > 0 else 1.0
        
        # 判斷
        is_disposition = vol_ratio < self.disposition_vol_threshold
        
        return is_disposition, recent_vol, max_vol, vol_ratio
    
    def _analyze_trend(self, price: float, ma5: float, ma10: float, bias: float) -> Dict:
        """分析趨勢"""
        if pd.isna(ma5) or pd.isna(ma10):
            return {"status": "UNKNOWN", "description": "數據不足"}
        
        if price > ma5 > ma10:
            status = "STRONG_BULL"
            description = "多頭強勢（股價 > MA5 > MA10）"
            emoji = "🚀"
        elif price > ma5:
            status = "BULL"
            description = "多頭（股價在 MA5 之上）"
            emoji = "📈"
        elif price > ma10:
            status = "WEAK_BULL"
            description = "弱多（股價在 MA10 之上但跌破 MA5）"
            emoji = "⚠️"
        elif price < ma5 < ma10:
            status = "STRONG_BEAR"
            description = "空頭強勢（股價 < MA5 < MA10）"
            emoji = "📉"
        else:
            status = "BEAR"
            description = "轉弱（股價跌破 MA5）"
            emoji = "🛑"
        
        # 乖離警告
        bias_warning = None
        if bias > self.high_bias_threshold:
            bias_warning = f"乖離過大 (+{bias:.1f}%)，隨時可能回檔"
        elif bias < -self.high_bias_threshold:
            bias_warning = f"乖離過大 ({bias:.1f}%)，可能超跌反彈"
        
        return {
            "status": status,
            "description": description,
            "emoji": emoji,
            "bias_warning": bias_warning
        }
    
    def _check_golden_buy(self, price: float, ma5: float, 
                          volume: float, prev_volume: float,
                          is_disposition: bool) -> Dict:
        """檢查黃金買點"""
        if pd.isna(ma5):
            return {"is_golden": False, "reason": "數據不足"}
        
        # 計算安全買入區間
        safe_buy_upper = ma5 * (1 + self.safe_buy_bias / 100)
        safe_buy_lower = ma5 * (1 - 0.02)  # MA5 下方 2%
        
        # 量縮判斷
        is_vol_shrink = volume < prev_volume * 0.8
        
        # 黃金買點條件
        if safe_buy_lower <= price <= safe_buy_upper:
            if is_vol_shrink:
                return {
                    "is_golden": True,
                    "signal": "STRONG",
                    "reason": f"股價回測 MA5 ({ma5:.2f}) 且量縮",
                    "suggestion": "分批佈局，下檔風險有限",
                    "buy_zone": f"{safe_buy_lower:.2f} - {safe_buy_upper:.2f}"
                }
            else:
                return {
                    "is_golden": False,
                    "signal": "WATCH",
                    "reason": f"股價回測 MA5，但量能仍大",
                    "suggestion": "等待量縮止穩再進場",
                    "buy_zone": f"{safe_buy_lower:.2f} - {safe_buy_upper:.2f}"
                }
        elif price < safe_buy_lower:
            return {
                "is_golden": False,
                "signal": "DANGER",
                "reason": "股價跌破 MA5",
                "suggestion": "觀察能否站回 MA5，否則減碼",
                "support": ma5
            }
        else:
            return {
                "is_golden": False,
                "signal": "WAIT",
                "reason": "股價遠離 MA5",
                "suggestion": f"等待回測 {ma5:.2f} - {safe_buy_upper:.2f} 區間",
                "buy_zone": f"{ma5:.2f} - {safe_buy_upper:.2f}"
            }
    
    def _generate_strategy(self, price: float, ma5: float, ma10: float,
                           bias: float, volume: float, prev_volume: float,
                           is_disposition: bool) -> Dict:
        """生成操作策略"""
        strategies = []
        risk_level = "MEDIUM"
        
        # 處置股策略
        if is_disposition:
            strategies.append({
                "type": "DISPOSITION",
                "action": "謹慎",
                "description": "量能急凍，不追價，僅適合低接"
            })
            risk_level = "HIGH"
        
        # 趨勢策略
        if not pd.isna(ma5):
            if price > ma5:
                if bias > self.high_bias_threshold:
                    strategies.append({
                        "type": "OVERBOUGHT",
                        "action": "減碼",
                        "description": f"乖離過大 (+{bias:.1f}%)，切勿追高"
                    })
                    risk_level = "HIGH"
                else:
                    strategies.append({
                        "type": "BULL",
                        "action": "持有",
                        "description": "趨勢向上，持有或逢低加碼"
                    })
            else:
                strategies.append({
                    "type": "BREAKDOWN",
                    "action": "觀望",
                    "description": f"跌破 MA5，觀察能否 3 日內站回 {ma5:.2f}"
                })
                risk_level = "HIGH"
        
        # 關鍵價位
        key_levels = {}
        if not pd.isna(ma5):
            key_levels["MA5_support"] = round(ma5, 2)
        if not pd.isna(ma10):
            key_levels["MA10_support"] = round(ma10, 2)
        key_levels["stop_loss"] = round(price * 0.95, 2)  # 5% 停損
        key_levels["target"] = round(price * 1.10, 2)     # 10% 目標
        
        return {
            "strategies": strategies,
            "risk_level": risk_level,
            "key_levels": key_levels
        }
    
    def _generate_report(self, symbol: str, date: str, price: float, 
                         volume: float, ma5: float, ma10: float, bias: float,
                         is_disposition: bool, recent_vol: float, max_vol: float,
                         vol_ratio: float, trend: Dict, strategy: Dict,
                         golden_buy: Dict) -> str:
        """生成完整報告"""
        lines = []
        
        lines.append(f"【股市顧問分析報告】{symbol}")
        lines.append(f"交易日：{date}")
        lines.append("-" * 40)
        lines.append(f"最新收盤：${price:.2f}")
        lines.append(f"今日成交量：{int(volume/1000):,} 張")
        lines.append(f"MA5 (短線生命線)：${ma5:.2f}")
        lines.append(f"MA10 (波段防守線)：${ma10:.2f}")
        lines.append(f"乖離率 (MA5)：{bias:+.2f}%")
        lines.append("-" * 40)
        
        # 處置判定
        lines.append("\n【1. 處置/流動性判定】")
        if is_disposition:
            lines.append("⚠️ 偵測到「量能急凍」或「處置交易」特徵")
            lines.append(f"   - 近期均量僅為高峰期的 {vol_ratio*100:.0f}%")
            lines.append("   - 策略：不追價，僅適合低接")
        else:
            lines.append("✅ 量能正常，流動性充足")
        
        # 趨勢分析
        lines.append(f"\n【2. 趨勢分析】")
        lines.append(f"{trend['emoji']} {trend['description']}")
        if trend.get('bias_warning'):
            lines.append(f"⚠️ {trend['bias_warning']}")
        
        # 操作策略
        lines.append("\n【3. 操作策略】")
        for s in strategy['strategies']:
            lines.append(f"   {s['action']}：{s['description']}")
        lines.append(f"   風險等級：{strategy['risk_level']}")
        
        # 關鍵價位
        lines.append("\n【4. 關鍵價位】")
        for k, v in strategy['key_levels'].items():
            lines.append(f"   {k}：${v}")
        
        # 黃金買點
        lines.append("\n【5. 黃金買點判定】")
        if golden_buy['is_golden']:
            lines.append(f"⭐ 【黃金買點訊號】")
            lines.append(f"   {golden_buy['reason']}")
            lines.append(f"   建議：{golden_buy['suggestion']}")
        else:
            lines.append(f"   {golden_buy['reason']}")
            if golden_buy.get('suggestion'):
                lines.append(f"   建議：{golden_buy['suggestion']}")
        
        return "\n".join(lines)


# 單例
disposition_advisor = DispositionStockAdvisor()


# 測試
if __name__ == "__main__":
    import asyncio
    
    async def test():
        result = await disposition_advisor.analyze("2337")
        if result['success']:
            print(result['report'])
        else:
            print(f"錯誤：{result['error']}")
    
    asyncio.run(test())
