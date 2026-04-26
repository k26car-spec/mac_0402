"""
處置股專用交易策略系統

特點：
1. 5分鐘撮合專用進場策略
2. MA5/MA10 分層掛單
3. 風險評分（0-100）
4. 處置股特殊參數（容忍更大乖離）
5. 下一次撮合時間提示

使用：
    from app.services.disposition_stock_strategy import disposition_strategy
    report = await disposition_strategy.analyze("2337")
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import io

logger = logging.getLogger(__name__)


class DispositionStockStrategy:
    """處置股專用交易策略"""
    
    def __init__(self):
        # 處置股特殊參數
        self.match_interval = 5  # 5分鐘撮合一次
        self.max_intraday_volatility = 15  # 日內最大波動15%
        
        # 處置股風險調整參數
        self.disposition_bias_tolerance = 15  # 容忍更大乖離 15%
        self.normal_bias_tolerance = 10       # 正常股 10%
        
        # 快取
        self.cache = {}
        self.cache_time = {}
    
    async def analyze(self, symbol: str, days: int = 30, 
                      disposition_start_date: str = None) -> Dict:
        """
        分析處置股並生成交易策略
        
        Args:
            symbol: 股票代碼
            days: 分析天數
            disposition_start_date: 處置開始日期（如 '2026-01-12'）
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
            ma5 = last['MA5']
            ma10 = last['MA10']
            volume = last['Volume']
            high = last['High']
            low = last['Low']
            date_str = last.name.strftime('%Y-%m-%d')
            
            # 計算振幅
            intraday_range = ((high - low) / low * 100) if low > 0 else 0
            
            # 計算乖離率
            bias = ((price - ma5) / ma5 * 100) if ma5 > 0 else 0
            
            # 風險評分
            risk_score = self._calculate_risk_score(
                price, ma5, ma10, volume, high, low, 
                df['Volume'].rolling(5).mean().iloc[-1] if len(df) > 5 else volume
            )
            
            # 生成掛單策略
            strategies = self._generate_order_strategy(price, ma5, ma10)
            
            # 下一次撮合時間
            next_match = self._get_next_match_time()
            
            # 生成報告
            report = self._generate_report(
                symbol, date_str, price, volume, ma5, ma10,
                high, low, bias, intraday_range, risk_score, 
                strategies, next_match, disposition_start_date
            )
            
            return {
                "success": True,
                "symbol": symbol,
                "date": date_str,
                "price": round(price, 2),
                "volume": int(volume),
                "volume_shares": int(volume / 1000),
                
                # 技術指標
                "ma5": round(ma5, 2) if not pd.isna(ma5) else None,
                "ma10": round(ma10, 2) if not pd.isna(ma10) else None,
                "bias_ma5": round(bias, 2),
                "intraday_range": round(intraday_range, 2),
                
                # 風險評分
                "risk_score": risk_score,
                "risk_level": self._get_risk_level(risk_score),
                
                # 交易策略
                "strategies": strategies,
                
                # 撮合時間
                "match_interval": self.match_interval,
                "next_match_time": next_match,
                
                # 處置股狀態
                "is_disposition": True,
                "disposition_start_date": disposition_start_date,
                
                # 完整報告
                "report": report
            }
            
        except Exception as e:
            logger.error(f"分析 {symbol} 失敗: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fetch_data(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """獲取股票數據"""
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            df = ticker.history(period=f"{days}d")
            
            if df.empty:
                ticker = yf.Ticker(f"{symbol}.TWO")
                df = ticker.history(period=f"{days}d")
            
            return df if not df.empty else None
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 數據失敗: {e}")
            return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標"""
        df = df.copy()
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        return df
    
    def _calculate_risk_score(self, price: float, ma5: float, ma10: float,
                              volume: float, high: float, low: float,
                              vol_ma5: float) -> int:
        """
        處置股風險評分（0-100）
        
        考慮因素：
        1. 乖離率（處置股可容忍更大乖離）
        2. 波動率（日內振幅）
        3. 量能
        4. 趨勢（MA5/MA10排列）
        """
        score = 50  # 基礎分
        
        # 1. 乖離率
        if not pd.isna(ma5) and ma5 > 0:
            bias = ((price - ma5) / ma5) * 100
            
            if -5 < bias < 5:
                score += 20  # 接近 MA5
            elif 5 <= bias < 15:
                score += 10  # 溫和正乖離
            elif bias >= 15:
                score -= 20  # 乖離過大
            elif bias <= -10:
                score -= 10  # 跌深
        
        # 2. 波動率
        if low > 0:
            intraday_range = ((high - low) / low) * 100
            
            if intraday_range > 15:
                score -= 15  # 波動過大
            elif 8 < intraday_range <= 15:
                score += 5   # 正常處置股波動
            else:
                score += 10  # 波動收斂
        
        # 3. 量能
        if not pd.isna(vol_ma5) and vol_ma5 > 0:
            vol_ratio = volume / vol_ma5
            
            if vol_ratio > 1.5:
                score += 15  # 量能放大
            elif vol_ratio < 0.5:
                score -= 5   # 量縮（處置股正常）
        
        # 4. 趨勢
        if not pd.isna(ma5) and not pd.isna(ma10):
            if price > ma5 > ma10:
                score += 20  # 多頭排列
            elif price > ma5:
                score += 10  # 在 MA5 上方
            elif price < ma10:
                score -= 15  # 破底
        
        return max(0, min(100, score))
    
    def _get_risk_level(self, score: int) -> Dict:
        """獲取風險等級"""
        if score >= 70:
            return {"level": "LOW", "color": "green", "emoji": "🟢", "advice": "適合進場"}
        elif score >= 50:
            return {"level": "MEDIUM", "color": "yellow", "emoji": "🟡", "advice": "謹慎進場"}
        else:
            return {"level": "HIGH", "color": "red", "emoji": "🔴", "advice": "建議觀望"}
    
    def _generate_order_strategy(self, price: float, ma5: float, ma10: float) -> List[Dict]:
        """
        生成掛單策略（5分鐘撮合專用）
        """
        strategies = []
        
        if pd.isna(ma5) or pd.isna(ma10):
            return [{"type": "WAIT", "action": "數據不足", "confidence": 0}]
        
        # === 策略 A：MA5 回測買點 ===
        if price > ma5:
            buy_zone_lower = ma5 * 0.97  # MA5 下方 3%
            buy_zone_upper = ma5 * 1.02  # MA5 上方 2%
            
            if price > buy_zone_upper:
                strategies.append({
                    "type": "MA5_PULLBACK",
                    "action": "等待回檔",
                    "order_type": "限價單",
                    "target_zone": {
                        "lower": round(buy_zone_lower, 2),
                        "upper": round(buy_zone_upper, 2)
                    },
                    "recommended_price": round(buy_zone_lower, 2),
                    "reason": f"當前價 ${price:.2f} > MA5，等待回測",
                    "expected_wait": "1-3 次撮合（5-15分鐘）",
                    "stop_loss": round(ma5 * 0.95, 2),
                    "take_profit": round(price * 1.08, 2),
                    "confidence": 75
                })
            else:
                strategies.append({
                    "type": "IMMEDIATE_BUY",
                    "action": "立即掛單",
                    "order_type": "市價或限價",
                    "recommended_price": round(price, 2),
                    "reason": "價格已回測 MA5 附近",
                    "expected_wait": "下一次撮合（最多5分鐘）",
                    "stop_loss": round(ma5 * 0.95, 2),
                    "take_profit": round(price * 1.10, 2),
                    "confidence": 85
                })
        
        # === 策略 B：MA10 強支撐買點 ===
        elif ma10 * 0.98 <= price <= ma10 * 1.02:
            strategies.append({
                "type": "MA10_SUPPORT",
                "action": "分批掛單",
                "order_type": "限價單（分層）",
                "layers": [
                    {"price": round(ma10, 2), "ratio": "40%", "description": "第一層"},
                    {"price": round(ma10 * 0.97, 2), "ratio": "30%", "description": "第二層"},
                    {"price": round(ma10 * 0.95, 2), "ratio": "30%", "description": "第三層"}
                ],
                "reason": "MA10 強支撐，分層接貨",
                "stop_loss": round(ma10 * 0.92, 2),
                "take_profit": round(ma10 * 1.15, 2),
                "confidence": 70
            })
        
        # === 策略 C：破底觀望 ===
        else:
            strategies.append({
                "type": "WAIT",
                "action": "觀望",
                "reason": f"價格 ${price:.2f} 跌破 MA10 ${ma10:.2f}，趨勢轉弱",
                "watch_level": round(ma10, 2),
                "confidence": 30
            })
        
        return strategies
    
    def _get_next_match_time(self) -> str:
        """計算下一次撮合時間"""
        now = datetime.now()
        
        # 交易時段檢查
        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)
        
        if now < market_open:
            return market_open.strftime("%H:%M") + "（開盤）"
        elif now > market_close:
            return "明日 09:00"
        
        # 計算下一個 5 分鐘撮合點
        minutes_to_next = self.match_interval - (now.minute % self.match_interval)
        if minutes_to_next == self.match_interval:
            minutes_to_next = 0
        
        next_match = now + timedelta(minutes=minutes_to_next)
        next_match = next_match.replace(second=0, microsecond=0)
        
        return next_match.strftime("%H:%M")
    
    def _generate_report(self, symbol: str, date: str, price: float,
                         volume: float, ma5: float, ma10: float,
                         high: float, low: float, bias: float,
                         intraday_range: float, risk_score: int,
                         strategies: List[Dict], next_match: str,
                         disposition_start_date: str = None) -> str:
        """生成完整報告"""
        lines = []
        
        lines.append("╔════════════════════════════════════════════════════════╗")
        lines.append(f"║      【處置股專用交易策略】{symbol}                        ║")
        lines.append("╚════════════════════════════════════════════════════════╝")
        lines.append(f"\n📅 交易日：{date}")
        
        if disposition_start_date:
            lines.append(f"⚠️  處置狀態：自 {disposition_start_date} 起（5分鐘撮合）")
        else:
            lines.append("⚠️  處置狀態：5分鐘撮合交易")
        
        lines.append("\n" + "="*60)
        lines.append("📊 基本數據")
        lines.append("-"*60)
        lines.append(f"收盤價：${price:.2f}")
        lines.append(f"今日振幅：{intraday_range:.2f}%")
        lines.append(f"今日成交量：{int(volume/1000):,} 張")
        
        if not pd.isna(ma5):
            lines.append(f"MA5：${ma5:.2f}")
        if not pd.isna(ma10):
            lines.append(f"MA10：${ma10:.2f}")
        lines.append(f"乖離率(MA5)：{bias:+.2f}%")
        
        # 風險評分
        lines.append("\n" + "="*60)
        lines.append("🎯 風險評分")
        lines.append("-"*60)
        
        risk_level = self._get_risk_level(risk_score)
        lines.append(f"評分：{risk_score}/100 ({risk_level['emoji']} {risk_level['level']})")
        lines.append(f"建議：{risk_level['advice']}")
        
        # 交易策略
        lines.append("\n" + "="*60)
        lines.append("📋 交易策略（5分鐘撮合專用）")
        lines.append("-"*60)
        
        for i, strategy in enumerate(strategies, 1):
            lines.append(f"\n策略 {i}：{strategy['type']}")
            lines.append(f"  動作：{strategy['action']}")
            
            if 'recommended_price' in strategy:
                lines.append(f"  建議價：${strategy['recommended_price']}")
            
            if 'target_zone' in strategy:
                zone = strategy['target_zone']
                lines.append(f"  目標區：${zone['lower']} - ${zone['upper']}")
            
            if 'layers' in strategy:
                for layer in strategy['layers']:
                    lines.append(f"  {layer['description']}：${layer['price']} ({layer['ratio']})")
            
            if 'stop_loss' in strategy:
                lines.append(f"  停損：${strategy['stop_loss']}")
            
            if 'take_profit' in strategy:
                lines.append(f"  目標：${strategy['take_profit']}")
            
            lines.append(f"  信心度：{strategy['confidence']}%")
        
        # 處置股須知
        lines.append("\n" + "="*60)
        lines.append("⚠️  處置股交易須知")
        lines.append("-"*60)
        lines.append("1. 每 5 分鐘撮合一次（無法即時進出）")
        lines.append("2. 掛單後最長等待 5 分鐘才能成交")
        lines.append("3. 建議使用「限價單」避免滑價")
        lines.append("4. 波動劇烈，務必設定停損")
        lines.append("5. 不要追高，等待回檔")
        
        lines.append(f"\n⏰ 下一次撮合時間：{next_match}")
        
        return "\n".join(lines)


# 單例
disposition_strategy = DispositionStockStrategy()


# 測試
if __name__ == "__main__":
    import asyncio
    
    async def test():
        result = await disposition_strategy.analyze(
            "2337", 
            disposition_start_date="2026-01-12"
        )
        if result['success']:
            print(result['report'])
        else:
            print(f"錯誤：{result['error']}")
    
    asyncio.run(test())
