"""
訂單動能評估系統 - 增強模組
整合技術面確認、供應鏈分析、市場情緒

提供:
1. 技術面確認 (TechnicalConfirmation)
2. 供應鏈動能 (SupplyChainMomentum) 
3. 市場情緒 (MarketSentiment)
4. 動態權重 (DynamicWeights)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import requests
import logging
import asyncio

logger = logging.getLogger(__name__)


class TechnicalConfirmation:
    """技術面確認模組"""
    
    async def get_confirmation_score(self, ticker: str) -> Tuple[float, Dict]:
        """
        獲取技術面確認分數
        
        Returns:
            (score, details): 確認分數 (0-100) 和詳細資訊
        """
        try:
            # 呼叫現有的技術分析 API
            response = requests.get(
                f"http://localhost:8000/api/economic-cycle/technical/analyze/{ticker}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis = data.get('analysis', {})
                
                # 提取關鍵指標
                rsi = analysis.get('indicators_summary', {}).get('rsi', 50)
                trend = analysis.get('indicators_summary', {}).get('trend', '盤整')
                position = analysis.get('position_analysis', {}).get('score', 50)
                signal = analysis.get('final_signal', 'hold')
                
                # 計算確認分數
                score = 50.0
                
                # RSI 調整
                if 30 <= rsi <= 70:
                    score += 10  # 健康區間
                elif rsi < 30:
                    score += 5   # 超賣區
                else:
                    score -= 10  # 超買區
                
                # 趨勢調整
                if trend == '多頭':
                    score += 20
                elif trend == '空頭':
                    score -= 15
                
                # 信號調整
                signal_scores = {
                    'strong_buy': 30, 'buy': 15, 'hold': 0, 
                    'sell': -15, 'strong_sell': -25
                }
                score += signal_scores.get(signal, 0)
                
                return min(100, max(0, score)), {
                    'rsi': rsi,
                    'trend': trend,
                    'signal': signal,
                    'position': position
                }
                
        except Exception as e:
            logger.warning(f"技術面確認獲取失敗 {ticker}: {e}")
        
        return 50.0, {}
    
    def check_divergence(self, momentum_score: float, tech_score: float) -> float:
        """
        檢查動能與技術面背離
        返回信心度調整係數 (0.7 - 1.0)
        """
        if (momentum_score > 70 and tech_score < 40) or \
           (momentum_score < 40 and tech_score > 70):
            return 0.7  # 背離，降低信心度
        return 1.0


class SupplyChainMomentum:
    """供應鏈動能分析模組"""
    
    # 產業鏈關聯表
    SUPPLY_CHAINS = {
        # 台積電 → 封測、設備、材料
        '2330': ['3711', '2449', '2329', '6239', '3037'],
        # 聯發科 → IC設計相關
        '2454': ['3034', '3231', '6669', '5274'],
        # 鴻海 → 供應鏈
        '2317': ['3008', '4958', '6269', '2382'],
        # 廣達 → AI伺服器相關
        '2382': ['6669', '3231', '3037', '2308'],
        # 台達電 → 電源、散熱
        '2308': ['6414', '3653', '6438'],
    }
    
    async def get_chain_momentum(self, ticker: str) -> Tuple[float, Dict]:
        """
        獲取供應鏈動能分數
        
        分析上下游公司的平均動能
        """
        related_tickers = self.SUPPLY_CHAINS.get(ticker, [])
        
        if not related_tickers:
            return 50.0, {'related': [], 'note': '無供應鏈資料'}
        
        try:
            # 呼叫供應鏈分析 API
            response = requests.get(
                f"http://localhost:8000/api/economic-cycle/electronics/supply-chain",
                params={'companies': ','.join([ticker] + related_tickers[:3])},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis = data.get('supply_chain_analysis', {})
                
                # 計算平均動能
                scores = []
                for company, info in analysis.items():
                    if isinstance(info, dict):
                        # 從分析結果提取動能
                        momentum = info.get('momentum', 50)
                        scores.append(momentum)
                
                if scores:
                    avg_score = np.mean(scores)
                    return avg_score, {
                        'related': related_tickers[:3],
                        'avg_momentum': round(avg_score, 1)
                    }
                    
        except Exception as e:
            logger.warning(f"供應鏈分析獲取失敗 {ticker}: {e}")
        
        # 備援：直接返回產業趨勢
        return 50.0, {'related': related_tickers[:3], 'note': 'API 失敗，使用預設'}


class MarketSentiment:
    """市場情緒分析模組"""
    
    async def get_sentiment_score(self, ticker: str) -> Tuple[float, Dict]:
        """
        獲取市場情緒分數
        
        整合新聞情緒分析
        """
        try:
            # 呼叫新聞分析 API
            response = requests.get(
                f"http://localhost:8000/api/stock-analysis/news/{ticker}",
                params={'limit': 10},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 提取情緒分析
                sentiment_analysis = data.get('sentiment_analysis', {})
                positive = sentiment_analysis.get('positive', 0)
                negative = sentiment_analysis.get('negative', 0)
                total = positive + negative + sentiment_analysis.get('neutral', 0)
                
                if total > 0:
                    # 計算情緒分數
                    positive_ratio = positive / total
                    negative_ratio = negative / total
                    
                    score = 50 + (positive_ratio - negative_ratio) * 50
                    
                    return min(100, max(0, score)), {
                        'positive': positive,
                        'negative': negative,
                        'news_count': total,
                        'overall': sentiment_analysis.get('overall', '中性')
                    }
                    
        except Exception as e:
            logger.warning(f"新聞情緒分析獲取失敗 {ticker}: {e}")
        
        return 50.0, {'note': '無新聞資料'}


class DynamicWeights:
    """動態權重調整模組"""
    
    # 時間維度權重
    TIME_SENSITIVE_WEIGHTS = {
        'intraday': {
            'price_momentum': 0.30,
            'institutional_flow': 0.25,
            'large_order_ratio': 0.25,
            'revenue_growth': 0.10,
            'industry_trend': 0.10
        },
        'weekly': {
            'revenue_growth': 0.20,
            'institutional_flow': 0.25,
            'industry_trend': 0.20,
            'price_momentum': 0.20,
            'large_order_ratio': 0.15
        },
        'monthly': {
            'revenue_growth': 0.35,
            'industry_trend': 0.25,
            'institutional_flow': 0.20,
            'price_momentum': 0.10,
            'large_order_ratio': 0.10
        }
    }
    
    # 市況調整
    MARKET_CONDITION_ADJUSTMENTS = {
        'bull': {  # 多頭市場
            'price_momentum': 1.2,
            'revenue_growth': 1.1
        },
        'bear': {  # 空頭市場
            'institutional_flow': 1.3,
            'industry_trend': 0.8
        },
        'volatile': {  # 震盪市場
            'large_order_ratio': 1.2,
            'price_momentum': 0.9
        }
    }
    
    def get_weights(self, timeframe: str = 'weekly', 
                   market_condition: str = 'neutral') -> Dict[str, float]:
        """
        獲取調整後的權重
        """
        # 基礎權重
        weights = self.TIME_SENSITIVE_WEIGHTS.get(
            timeframe, self.TIME_SENSITIVE_WEIGHTS['weekly']
        ).copy()
        
        # 市況調整
        if market_condition in self.MARKET_CONDITION_ADJUSTMENTS:
            adjustments = self.MARKET_CONDITION_ADJUSTMENTS[market_condition]
            for factor, multiplier in adjustments.items():
                if factor in weights:
                    weights[factor] *= multiplier
        
        # 正規化
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}
    
    def detect_market_condition(self) -> str:
        """
        偵測當前市場狀況
        """
        try:
            # 呼叫大盤技術分析
            response = requests.get(
                "http://localhost:8000/api/economic-cycle/technical/analyze/0050",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                trend = data.get('analysis', {}).get('indicators_summary', {}).get('trend', '盤整')
                
                if trend == '多頭':
                    return 'bull'
                elif trend == '空頭':
                    return 'bear'
                else:
                    return 'neutral'
                    
        except:
            pass
        
        return 'neutral'


# 整合函數
async def get_enhanced_factors(ticker: str) -> Dict:
    """
    獲取增強因子分析
    
    Returns:
        Dict containing enhanced analysis
    """
    tech_confirm = TechnicalConfirmation()
    supply_chain = SupplyChainMomentum()
    sentiment = MarketSentiment()
    
    # 並行獲取數據
    tech_score, tech_details = await tech_confirm.get_confirmation_score(ticker)
    chain_score, chain_details = await supply_chain.get_chain_momentum(ticker)
    sentiment_score, sentiment_details = await sentiment.get_sentiment_score(ticker)
    
    return {
        'technical_confirmation': {
            'score': tech_score,
            'details': tech_details
        },
        'supply_chain': {
            'score': chain_score,
            'details': chain_details
        },
        'sentiment': {
            'score': sentiment_score,
            'details': sentiment_details
        }
    }


# 測試
if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("📊 增強模組測試")
        print("=" * 60)
        
        ticker = "2330"
        
        # 測試各模組
        print(f"\n測試股票: {ticker}")
        
        # 技術面確認
        tech = TechnicalConfirmation()
        score, details = await tech.get_confirmation_score(ticker)
        print(f"\n技術面確認: {score:.1f}")
        print(f"  詳情: {details}")
        
        # 供應鏈
        chain = SupplyChainMomentum()
        score, details = await chain.get_chain_momentum(ticker)
        print(f"\n供應鏈動能: {score:.1f}")
        print(f"  詳情: {details}")
        
        # 情緒
        sent = MarketSentiment()
        score, details = await sent.get_sentiment_score(ticker)
        print(f"\n市場情緒: {score:.1f}")
        print(f"  詳情: {details}")
        
        # 動態權重
        weights = DynamicWeights()
        print(f"\n動態權重 (weekly):")
        for factor, weight in weights.get_weights('weekly').items():
            print(f"  {factor}: {weight:.2%}")
    
    asyncio.run(test())
