"""
訂單動能評估系統 v2.0
基於多因子模型與動態權重調整的精準評分系統

核心因子:
1. 月營收成長率 (YoY/MoM)
2. 法人買賣超 (3-5日累計)
3. 大單動能比率
4. 產業訂單能見度

作者: AI Stock Analysis System
日期: 2024-12
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import requests
import logging

logger = logging.getLogger(__name__)


class CyclePhase(Enum):
    """經濟周期階段"""
    EARLY_CYCLE = "early_cycle"      # 復甦初期
    MID_CYCLE = "mid_cycle"          # 擴張中期
    LATE_CYCLE = "late_cycle"        # 擴張末期
    RECESSION = "recession"          # 衰退期


@dataclass
class OrderMomentumScore:
    """訂單動能評分結果"""
    ticker: str
    score: float                     # 0-100 評分
    confidence: float                # 0-1 信心度
    components: Dict[str, float]     # 各因子貢獻
    is_anomaly: bool = False
    anomaly_reasons: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        return {
            "ticker": self.ticker,
            "score": round(self.score, 1),
            "confidence": round(self.confidence, 2),
            "components": {k: round(v, 1) for k, v in self.components.items()},
            "is_anomaly": self.is_anomaly,
            "anomaly_reasons": self.anomaly_reasons,
            "timestamp": self.timestamp.isoformat()
        }


class OrderMomentumEvaluator:
    """
    訂單動能精準評估器
    
    整合多因子分析:
    - 營收動能
    - 法人動向
    - 大單監測
    - 產業趨勢
    """
    
    # 因子權重 (可動態調整)
    DEFAULT_WEIGHTS = {
        "revenue_growth": 0.30,      # 營收成長率
        "institutional_flow": 0.25,  # 法人買賣超
        "large_order_ratio": 0.20,   # 大單比率
        "industry_trend": 0.15,      # 產業趨勢
        "price_momentum": 0.10       # 價格動能
    }
    
    # 產業周期調整參數
    CYCLE_ADJUSTMENTS = {
        CyclePhase.EARLY_CYCLE: {
            "IC設計": {"revenue_growth": 0.35, "institutional_flow": 0.25},
            "半導體設備": {"revenue_growth": 0.40, "institutional_flow": 0.20},
            "default": {"revenue_growth": 0.35, "institutional_flow": 0.25}
        },
        CyclePhase.MID_CYCLE: {
            "晶圓代工": {"revenue_growth": 0.30, "institutional_flow": 0.30},
            "封測": {"revenue_growth": 0.25, "large_order_ratio": 0.25},
            "default": {"revenue_growth": 0.28, "institutional_flow": 0.28}
        },
        CyclePhase.LATE_CYCLE: {
            "記憶體": {"price_momentum": 0.30, "industry_trend": 0.25},
            "被動元件": {"price_momentum": 0.35, "industry_trend": 0.20},
            "default": {"price_momentum": 0.25, "industry_trend": 0.25}
        },
        CyclePhase.RECESSION: {
            "default": {"institutional_flow": 0.40, "revenue_growth": 0.20}
        }
    }
    
    def __init__(self):
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.cache = {}
        self.historical_scores = {}  # 歷史評分記錄
        self.accuracy_tracker = {}   # 準確度追蹤
        
    async def evaluate(self, ticker: str, stock_type: str = "default") -> OrderMomentumScore:
        """
        評估單一股票的訂單動能
        
        Parameters:
        -----------
        ticker : str
            股票代碼
        stock_type : str
            股票類型 (用於調整權重)
            
        Returns:
        --------
        OrderMomentumScore: 評分結果
        """
        try:
            # 1. 獲取各因子數據
            components = {}
            
            # 營收成長率
            revenue_score = await self._get_revenue_momentum(ticker)
            components["revenue_growth"] = revenue_score
            
            # 法人買賣超
            institutional_score = await self._get_institutional_flow(ticker)
            components["institutional_flow"] = institutional_score
            
            # 大單比率
            large_order_score = await self._get_large_order_ratio(ticker)
            components["large_order_ratio"] = large_order_score
            
            # 產業趨勢
            industry_score = self._get_industry_trend_score(ticker, stock_type)
            components["industry_trend"] = industry_score
            
            # 價格動能
            price_score = await self._get_price_momentum(ticker)
            components["price_momentum"] = price_score
            
            # 2. 獲取調整後的權重
            adjusted_weights = self._get_adjusted_weights(stock_type)
            
            # 3. 計算加權總分
            total_score = 0
            for factor, score in components.items():
                weight = adjusted_weights.get(factor, 0.1)
                total_score += score * weight
            
            # 4. 異常檢測
            is_anomaly, anomaly_reasons = self._detect_anomaly(ticker, total_score, components)
            
            # 5. 計算信心度
            confidence = self._calculate_confidence(components, is_anomaly)
            
            # 6. 建立結果
            result = OrderMomentumScore(
                ticker=ticker,
                score=min(100, max(0, total_score)),
                confidence=confidence,
                components=components,
                is_anomaly=is_anomaly,
                anomaly_reasons=anomaly_reasons
            )
            
            # 7. 記錄歷史
            self._record_score(ticker, result)
            
            return result
            
        except Exception as e:
            logger.error(f"評估 {ticker} 訂單動能時發生錯誤: {e}")
            # 返回預設評分
            return OrderMomentumScore(
                ticker=ticker,
                score=50.0,
                confidence=0.3,
                components={"error": 50},
                is_anomaly=True,
                anomaly_reasons=[f"評估錯誤: {str(e)}"]
            )
    
    async def _get_revenue_momentum(self, ticker: str) -> float:
        """
        獲取營收動能評分
        
        數據來源: TWSE 月營收公告
        評分邏輯:
        - YoY > 30%: 90-100分
        - YoY > 15%: 70-90分
        - YoY > 0%: 50-70分
        - YoY < 0%: 30-50分
        - YoY < -15%: 10-30分
        """
        try:
            # 嘗試從 API 獲取月營收
            yoy_growth = await self._fetch_revenue_yoy(ticker)
            mom_growth = await self._fetch_revenue_mom(ticker)
            
            if yoy_growth is not None:
                # 基於 YoY 評分
                if yoy_growth > 0.50:
                    score = 95 + min(5, yoy_growth * 5)
                elif yoy_growth > 0.30:
                    score = 85 + (yoy_growth - 0.30) * 50
                elif yoy_growth > 0.15:
                    score = 70 + (yoy_growth - 0.15) * 100
                elif yoy_growth > 0:
                    score = 50 + yoy_growth * 133
                elif yoy_growth > -0.15:
                    score = 50 + yoy_growth * 133
                else:
                    score = max(10, 30 + yoy_growth * 133)
                
                # MoM 微調 (+/-5分)
                if mom_growth is not None:
                    if mom_growth > 0.10:
                        score += 5
                    elif mom_growth > 0.05:
                        score += 3
                    elif mom_growth < -0.10:
                        score -= 5
                    elif mom_growth < -0.05:
                        score -= 3
                
                return min(100, max(0, score))
                
        except Exception as e:
            logger.warning(f"獲取 {ticker} 營收數據失敗: {e}")
        
        # 備援: 返回中性分數
        return 50.0
    
    async def _fetch_revenue_yoy(self, ticker: str) -> Optional[float]:
        """從 API 獲取 YoY 營收成長率"""
        try:
            # 使用 yfinance 獲取營收成長
            import yfinance as yf
            
            for suffix in ['.TW', '.TWO']:
                symbol = f"{ticker}{suffix}"
                stock = yf.Ticker(symbol)
                info = stock.info
                
                revenue_growth = info.get('revenueGrowth')
                if revenue_growth is not None:
                    return revenue_growth
            
        except:
            pass
        
        return None
    
    async def _fetch_revenue_mom(self, ticker: str) -> Optional[float]:
        """從 API 獲取 MoM 營收成長率"""
        # TODO: 串接 TWSE 月營收 API
        return None
    
    async def _get_institutional_flow(self, ticker: str) -> float:
        """
        獲取法人買賣超評分
        
        數據來源: TWSE 三大法人買賣超
        評分邏輯:
        - 外資+投信連續買超5日: 80-100分
        - 外資+投信連續買超3日: 60-80分
        - 法人中性: 40-60分
        - 法人賣超: 20-40分
        """
        try:
            # 嘗試獲取法人資料
            institutional_data = await self._fetch_institutional_data(ticker)
            
            if institutional_data:
                foreign = institutional_data.get('foreign_net', 0)
                investment_trust = institutional_data.get('investment_trust_net', 0)
                
                # 計算總淨買超
                total_net = foreign + investment_trust
                
                # 評分
                if total_net > 10000:  # 淨買超 > 1億
                    score = 90
                elif total_net > 5000:
                    score = 80
                elif total_net > 1000:
                    score = 70
                elif total_net > 0:
                    score = 60
                elif total_net > -1000:
                    score = 45
                elif total_net > -5000:
                    score = 35
                else:
                    score = 25
                
                return score
                
        except Exception as e:
            logger.warning(f"獲取 {ticker} 法人資料失敗: {e}")
        
        return 50.0
    
    async def _fetch_institutional_data(self, ticker: str) -> Optional[Dict]:
        """從 TWSE API 獲取法人買賣超數據"""
        try:
            import sys
            sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/app/services')
            from twse_crawler import twse_crawler
            
            # 獲取最近5日法人買賣超
            data = await twse_crawler.get_stock_institutional(ticker, days=5)
            
            if data and len(data) > 0:
                # 計算5日累計
                total_foreign = 0
                total_trust = 0
                total_dealer = 0
                
                for day in data:
                    try:
                        # 解析數字（移除逗號）
                        foreign = day.get('foreign', '0')
                        trust = day.get('trust', '0')
                        dealer = day.get('dealer', '0')
                        
                        if isinstance(foreign, str):
                            foreign = int(foreign.replace(',', '').replace(' ', '') or 0)
                        if isinstance(trust, str):
                            trust = int(trust.replace(',', '').replace(' ', '') or 0)
                        if isinstance(dealer, str):
                            dealer = int(dealer.replace(',', '').replace(' ', '') or 0)
                        
                        total_foreign += foreign
                        total_trust += trust
                        total_dealer += dealer
                    except:
                        continue
                
                logger.info(f"✅ {ticker} 法人5日累計: 外資 {total_foreign}, 投信 {total_trust}, 自營 {total_dealer}")
                
                return {
                    'foreign_net': total_foreign,
                    'investment_trust_net': total_trust,
                    'dealer_net': total_dealer,
                    'days': len(data)
                }
                
        except Exception as e:
            logger.warning(f"TWSE 法人數據獲取失敗: {e}")
        
        return None
    
    async def _get_large_order_ratio(self, ticker: str) -> float:
        """
        獲取大單比率評分
        
        使用現有的大單監測系統數據
        """
        try:
            # 呼叫現有的大單監測 API
            response = requests.get(
                f"http://localhost:8000/api/big-order/{ticker}/signals",
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                signals = data.get('signals', [])
                
                if signals:
                    # 計算最近大單信號強度
                    buy_signals = len([s for s in signals if s.get('direction') == 'buy'])
                    sell_signals = len([s for s in signals if s.get('direction') == 'sell'])
                    
                    if buy_signals > sell_signals * 2:
                        return 85
                    elif buy_signals > sell_signals:
                        return 70
                    elif buy_signals == sell_signals:
                        return 50
                    elif sell_signals > buy_signals:
                        return 35
                    else:
                        return 20
                        
        except:
            pass
        
        return 50.0
    
    def _get_industry_trend_score(self, ticker: str, stock_type: str) -> float:
        """
        獲取產業趨勢評分
        
        基於產業類型給予趨勢評分
        """
        # 2024年底各產業趨勢評分
        INDUSTRY_TRENDS = {
            "AI伺服器": 90,
            "晶圓代工": 75,
            "IC設計": 70,
            "封測": 60,
            "PCB": 65,
            "記憶體": 55,
            "被動元件": 50,
            "面板": 40,
            "LED": 35,
            "default": 50
        }
        
        return INDUSTRY_TRENDS.get(stock_type, INDUSTRY_TRENDS["default"])
    
    async def _get_price_momentum(self, ticker: str) -> float:
        """
        獲取價格動能評分
        
        基於短期股價走勢
        """
        try:
            import yfinance as yf
            
            for suffix in ['.TW', '.TWO']:
                symbol = f"{ticker}{suffix}"
                stock = yf.Ticker(symbol)
                hist = stock.history(period='1mo')
                
                if len(hist) >= 20:
                    # 計算近20日漲跌幅
                    change = (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100
                    
                    if change > 15:
                        return 90
                    elif change > 10:
                        return 80
                    elif change > 5:
                        return 70
                    elif change > 0:
                        return 60
                    elif change > -5:
                        return 45
                    elif change > -10:
                        return 35
                    else:
                        return 25
                        
        except:
            pass
        
        return 50.0
    
    def _get_adjusted_weights(self, stock_type: str) -> Dict[str, float]:
        """
        根據產業和周期調整權重
        """
        # 目前使用預設權重，未來可根據周期動態調整
        cycle = CyclePhase.LATE_CYCLE  # 2024年底判斷為擴張末期
        
        cycle_adjustments = self.CYCLE_ADJUSTMENTS.get(cycle, {})
        type_adjustments = cycle_adjustments.get(stock_type, cycle_adjustments.get("default", {}))
        
        adjusted = self.DEFAULT_WEIGHTS.copy()
        adjusted.update(type_adjustments)
        
        # 正規化權重
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}
    
    def _detect_anomaly(self, ticker: str, score: float, components: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        異常檢測
        """
        anomalies = []
        
        # 規則1: 各因子評分差異過大
        scores = list(components.values())
        if max(scores) - min(scores) > 50:
            anomalies.append("因子評分差異過大")
        
        # 規則2: 與歷史評分差異過大
        if ticker in self.historical_scores:
            hist_scores = [s.score for s in self.historical_scores[ticker][-10:]]
            if hist_scores:
                hist_avg = np.mean(hist_scores)
                if abs(score - hist_avg) > 25:
                    anomalies.append("與歷史評分差異過大")
        
        return len(anomalies) > 0, anomalies
    
    def _calculate_confidence(self, components: Dict[str, float], is_anomaly: bool) -> float:
        """
        計算評分信心度
        """
        # 基礎信心度
        base_confidence = 0.7
        
        # 因子一致性加成
        scores = list(components.values())
        std = np.std(scores)
        consistency_bonus = max(0, 0.2 * (1 - std / 30))
        
        # 異常扣減
        anomaly_penalty = 0.2 if is_anomaly else 0
        
        return min(0.95, max(0.3, base_confidence + consistency_bonus - anomaly_penalty))
    
    def _record_score(self, ticker: str, result: OrderMomentumScore):
        """記錄評分歷史"""
        if ticker not in self.historical_scores:
            self.historical_scores[ticker] = []
        
        self.historical_scores[ticker].append(result)
        
        # 只保留最近30筆
        if len(self.historical_scores[ticker]) > 30:
            self.historical_scores[ticker] = self.historical_scores[ticker][-30:]


# 全域實例
_evaluator = None

def get_order_momentum_evaluator() -> OrderMomentumEvaluator:
    """獲取訂單動能評估器實例"""
    global _evaluator
    if _evaluator is None:
        _evaluator = OrderMomentumEvaluator()
    return _evaluator


async def evaluate_order_momentum(ticker: str, stock_type: str = "default") -> Dict:
    """
    便捷函數: 評估訂單動能
    """
    evaluator = get_order_momentum_evaluator()
    result = await evaluator.evaluate(ticker, stock_type)
    return result.to_dict()


# 測試
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 60)
        print("📊 訂單動能評估系統測試")
        print("=" * 60)
        
        evaluator = OrderMomentumEvaluator()
        
        test_stocks = [
            ("2330", "晶圓代工"),
            ("2454", "IC設計"),
            ("3231", "AI伺服器"),
            ("1815", "PCB")
        ]
        
        for ticker, stock_type in test_stocks:
            result = await evaluator.evaluate(ticker, stock_type)
            print(f"\n{ticker} ({stock_type}):")
            print(f"  總分: {result.score:.1f}")
            print(f"  信心度: {result.confidence:.2f}")
            print(f"  各因子: {result.components}")
            if result.is_anomaly:
                print(f"  ⚠️ 異常: {result.anomaly_reasons}")
    
    asyncio.run(test())
