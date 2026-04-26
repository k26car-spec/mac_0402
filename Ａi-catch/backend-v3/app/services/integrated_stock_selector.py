"""
全自動選股決策引擎
整合基本面、技術面、籌碼面、市場情緒等多維度分析
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .broker_flow_analyzer import broker_flow_analyzer
from .stock_comprehensive_analyzer import StockComprehensiveAnalyzer
from .gpt_analyzer import gpt_analyzer
from .twse_crawler import get_institutional_data

logger = logging.getLogger(__name__)


class IntegratedStockSelector:
    """
    整合選股決策引擎
    結合多維度分析提供量化評分與投資建議
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self.default_config()
        self.comprehensive_analyzer = StockComprehensiveAnalyzer()
        
        # 產業分類
        self.industry_groups = {
            '半導體': ['2330', '2303', '2454', '5347', '6770', '3034', '2379'],
            'AI伺服器': ['2382', '2345', '2317', '6669'],
            '電子零組件': ['2317', '2324', '2357', '3231', '6505'],
            '金融': ['2882', '2881', '2891', '2886', '2892'],
            '傳產': ['1301', '1303', '1326', '1402', '2002'],
            'ESG/高股息': ['0050', '0056', '00878', '00929', '00919']
        }
        
    def default_config(self) -> Dict:
        """預設配置"""
        return {
            'scoring_weights': {
                'fundamentals': 0.30,      # 基本面權重
                'technicals': 0.25,        # 技術面權重
                'broker_flow': 0.25,       # 籌碼面權重
                'market_sentiment': 0.10,  # 市場情緒
                'ai_analysis': 0.10        # AI分析
            },
            'risk_parameters': {
                'max_position_pct': 0.15,  # 單一標的最大倉位
                'stop_loss_pct': 0.08,     # 停損比例
                'take_profit_pct': 0.20,   # 停利比例
                'max_drawdown': 0.15       # 最大回撤容忍
            },
            'screening_criteria': {
                'min_market_cap': 5e9,     # 最小市值（50億）
                'min_avg_volume': 500,     # 最小日均量（張）
                'min_price': 10,           # 最低股價
                'max_price': 1000          # 最高股價
            },
            'broker_criteria': {
                'min_net_flow': 100,       # 最小淨流入（張）
                'key_brokers': ['富邦-新店', '元大-台北', '凱基-台北']
            }
        }
    
    async def analyze_stock(self, stock_code: str) -> Dict:
        """
        完整分析單一股票
        
        Args:
            stock_code: 股票代碼
            
        Returns:
            完整分析結果
        """
        try:
            logger.info(f"🔍 開始分析 {stock_code}")
            
            # 並行獲取各維度數據
            tasks = [
                self._get_fundamental_data(stock_code),
                self._get_technical_data(stock_code),
                self._get_broker_flow_data(stock_code),
                self._get_market_context(),
                self._get_institutional_data(stock_code)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            fundamental_data = results[0] if not isinstance(results[0], Exception) else {}
            technical_data = results[1] if not isinstance(results[1], Exception) else {}
            broker_flow_data = results[2] if not isinstance(results[2], Exception) else {}
            market_context = results[3] if not isinstance(results[3], Exception) else {}
            institutional_data = results[4] if not isinstance(results[4], Exception) else {}
            
            # 整合數據
            integrated_data = {
                'metadata': {
                    'stock_code': stock_code,
                    'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                    'timestamp': datetime.now().isoformat()
                },
                'fundamentals': fundamental_data,
                'technicals': technical_data,
                'broker_flow': broker_flow_data,
                'institutional': institutional_data,
                'market_context': market_context
            }
            
            # 計算綜合評分
            scores = self.calculate_composite_score(integrated_data)
            
            # AI 分析（如果可用）
            ai_analysis = await self._get_ai_analysis(integrated_data, scores)
            
            # 組裝完整結果
            result = {
                **integrated_data,
                'scores': scores,
                'ai_analysis': ai_analysis,
                'recommendation': self._generate_recommendation(scores, integrated_data),
                'risk_assessment': self._assess_risk(integrated_data, scores),
                'position_sizing': self._calculate_position_sizing(scores, integrated_data)
            }
            
            logger.info(f"✅ {stock_code} 分析完成，評分: {scores['weighted_score']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 分析 {stock_code} 失敗: {e}")
            return self._empty_analysis_result(stock_code)
    
    async def _get_fundamental_data(self, stock_code: str) -> Dict:
        """獲取基本面數據（帶超時）"""
        try:
            # 使用線程池執行 yfinance 以避免阻塞
            loop = asyncio.get_event_loop()
            
            def fetch_info():
                ticker = f"{stock_code}.TW"
                stock = yf.Ticker(ticker)
                return stock.info
            
            # 設置5秒超時
            info = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_info),
                timeout=5.0
            )
            
            return {
                'pe_ratio': info.get('trailingPE', 0) or 0,
                'pb_ratio': info.get('priceToBook', 0) or 0,
                'dividend_yield': (info.get('dividendYield', 0) or 0) * 100,
                'roe': (info.get('returnOnEquity', 0) or 0) * 100,
                'debt_to_equity': info.get('debtToEquity', 0) or 0,
                'market_cap': info.get('marketCap', 0) or 0,
                'revenue_growth': (info.get('revenueGrowth', 0) or 0) * 100
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"獲取基本面數據超時 {stock_code}")
            return {}
        except Exception as e:
            logger.warning(f"獲取基本面數據失敗 {stock_code}: {e}")
            return {}
    
    async def _get_technical_data(self, stock_code: str) -> Dict:
        """獲取技術面數據（帶超時）"""
        try:
            loop = asyncio.get_event_loop()
            
            def fetch_history():
                ticker = f"{stock_code}.TW"
                stock = yf.Ticker(ticker)
                return stock.history(period="3mo")
            
            # 設置5秒超時
            hist = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_history),
                timeout=5.0
            )
            
            if len(hist) < 20:
                return {}
            
            close_prices = hist['Close']
            
            return {
                'current_price': float(close_prices.iloc[-1]),
                'ma5': float(close_prices.rolling(5).mean().iloc[-1]),
                'ma10': float(close_prices.rolling(10).mean().iloc[-1]),
                'ma20': float(close_prices.rolling(20).mean().iloc[-1]),
                'ma60': float(close_prices.rolling(60).mean().iloc[-1]) if len(close_prices) >= 60 else float(close_prices.mean()),
                'volume_ratio': float(hist['Volume'].iloc[-1] / hist['Volume'].rolling(20).mean().iloc[-1]) if hist['Volume'].rolling(20).mean().iloc[-1] > 0 else 1.0,
                'returns_20d': float((close_prices.iloc[-1] / close_prices.iloc[-20] - 1) * 100) if len(close_prices) >= 20 else 0.0,
                'volatility': float(close_prices.pct_change().std() * np.sqrt(252) * 100)
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"獲取技術面數據超時 {stock_code}")
            return {}
        except Exception as e:
            logger.warning(f"獲取技術面數據失敗 {stock_code}: {e}")
            return {}
    
    async def _get_broker_flow_data(self, stock_code: str) -> Dict:
        """獲取券商進出數據"""
        try:
            # 使用券商分析器
            flow_data = broker_flow_analyzer.get_broker_flow_summary(stock_code, days=5)
            
            return flow_data
            
        except Exception as e:
            logger.error(f"獲取券商數據失敗 {stock_code}: {e}")
            return {}
    
    async def _get_institutional_data(self, stock_code: str) -> Dict:
        """獲取法人買賣數據"""
        try:
            # 使用 TWSE 爬蟲
            institutional = get_institutional_data()
            
            return institutional if institutional else {}
            
        except Exception as e:
            logger.error(f"獲取法人數據失敗 {stock_code}: {e}")
            return {}
    
    async def _get_market_context(self) -> Dict:
        """獲取市場環境"""
        try:
            # 大盤指數
            twii = yf.Ticker("^TWII")
            twii_hist = twii.history(period="5d")
            
            if twii_hist.empty:
                return {}
            
            return {
                'twii_close': twii_hist['Close'].iloc[-1],
                'twii_change_pct': ((twii_hist['Close'].iloc[-1] / twii_hist['Close'].iloc[-2] - 1) * 100 
                                   if len(twii_hist) >= 2 else 0),
                'market_trend': 'bullish' if twii_hist['Close'].iloc[-1] > twii_hist['Close'].iloc[0] 
                              else 'bearish',
                'vix_level': 'normal'  # 可擴充
            }
            
        except Exception as e:
            logger.error(f"獲取市場環境失敗: {e}")
            return {}
    
    async def _get_ai_analysis(self, integrated_data: Dict, scores: Dict) -> Dict:
        """獲取 AI 分析"""
        try:
            if not gpt_analyzer.initialized:
                return {'available': False}
            
            stock_data = {
                'stock_code': integrated_data['metadata']['stock_code'],
                'score': scores['weighted_score'],
                'fundamentals': integrated_data.get('fundamentals', {}),
                'technicals': integrated_data.get('technicals', {}),
                'broker_flow': integrated_data.get('broker_flow', {})
            }
            
            ai_result = gpt_analyzer.analyze_stock(stock_data)
            
            return {
                'available': True,
                'analysis': ai_result
            }
            
        except Exception as e:
            logger.error(f"AI 分析失敗: {e}")
            return {'available': False}
    
    def calculate_composite_score(self, integrated_data: Dict) -> Dict:
        """
        計算綜合評分
        """
        scores = {
            'component_scores': {},
            'weighted_score': 0,
            'final_grade': 'C',
            'recommendation': 'HOLD',
            'confidence': 0
        }
        
        try:
            weights = self.config['scoring_weights']
            
            # 1. 基本面評分
            fund_score = self._score_fundamentals(integrated_data.get('fundamentals', {}))
            scores['component_scores']['fundamentals'] = fund_score
            
            # 2. 技術面評分
            tech_score = self._score_technicals(integrated_data.get('technicals', {}))
            scores['component_scores']['technicals'] = tech_score
            
            # 3. 籌碼面評分（券商進出）
            broker_score = self._score_broker_flow(integrated_data.get('broker_flow', {}))
            scores['component_scores']['broker_flow'] = broker_score
            
            # 4. 法人買賣評分
            inst_score = self._score_institutional(integrated_data.get('institutional', {}))
            scores['component_scores']['institutional'] = inst_score
            
            # 5. 市場環境調整
            market_adjust = self._adjust_for_market(integrated_data.get('market_context', {}))
            scores['component_scores']['market_adjustment'] = market_adjust
            
            # 計算加權總分
            weighted_score = (
                fund_score * weights['fundamentals'] +
                tech_score * weights['technicals'] +
                broker_score * weights['broker_flow'] +
                inst_score * 0.10 +
                market_adjust
            )
            
            # 確保分數在 0-100 範圍
            weighted_score = max(0, min(100, weighted_score))
            
            scores['weighted_score'] = round(weighted_score, 2)
            scores['final_grade'] = self._score_to_grade(weighted_score)
            scores['recommendation'] = self._score_to_recommendation(weighted_score)
            scores['confidence'] = self._calculate_confidence(integrated_data)
            
            # 計算目標價與停損價
            if integrated_data.get('technicals', {}).get('current_price'):
                current_price = integrated_data['technicals']['current_price']
                scores['target_price'] = self._calculate_target_price(current_price, weighted_score)
                scores['stop_loss'] = self._calculate_stop_loss(current_price, integrated_data['technicals'])
            
        except Exception as e:
            logger.error(f"計算評分失敗: {e}")
        
        return scores
    
    def _score_fundamentals(self, fundamentals: Dict) -> float:
        """基本面評分 (0-100)"""
        if not fundamentals:
            return 50
        
        score = 50  # 基準分
        
        # ROE 評分
        roe = fundamentals.get('roe', 0)
        if roe > 15:
            score += 15
        elif roe > 8:
            score += 8
        elif roe < 0:
            score -= 15
        
        # 本益比評分
        pe = fundamentals.get('pe_ratio', 0)
        if 0 < pe < 15:
            score += 10
        elif pe > 30:
            score -= 10
        
        # 負債比評分
        debt_ratio = fundamentals.get('debt_to_equity', 0)
        if debt_ratio < 50:
            score += 10
        elif debt_ratio > 200:
            score -= 10
        
        # 股息殖利率
        dividend_yield = fundamentals.get('dividend_yield', 0)
        if dividend_yield > 4:
            score += 10
        
        # 營收成長
        revenue_growth = fundamentals.get('revenue_growth', 0)
        if revenue_growth > 10:
            score += 10
        elif revenue_growth < -10:
            score -= 10
        
        return max(0, min(100, score))
    
    def _score_technicals(self, technicals: Dict) -> float:
        """技術面評分 (0-100)"""
        if not technicals:
            return 50
        
        score = 50
        
        # 均線排列
        current_price = technicals.get('current_price', 0)
        ma5 = technicals.get('ma5', 0)
        ma10 = technicals.get('ma10', 0)
        ma20 = technicals.get('ma20', 0)
        ma60 = technicals.get('ma60', 0)
        
        # 多頭排列
        if current_price > ma5 > ma10 > ma20 > ma60:
            score += 20
        # 空頭排列
        elif current_price < ma5 < ma10 < ma20 < ma60:
            score -= 20
        # 部分多頭
        elif current_price > ma20:
            score += 10
        
        # 成交量
        volume_ratio = technicals.get('volume_ratio', 1)
        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio < 0.5:
            score -= 5
        
        # 近期報酬
        returns_20d = technicals.get('returns_20d', 0)
        if returns_20d > 10:
            score += 10
        elif returns_20d < -10:
            score -= 10
        
        # 波動率（低波動較佳）
        volatility = technicals.get('volatility', 30)
        if volatility < 20:
            score += 5
        elif volatility > 40:
            score -= 5
        
        return max(0, min(100, score))
    
    def _score_broker_flow(self, broker_flow: Dict) -> float:
        """籌碼面評分 (0-100)"""
        if not broker_flow:
            return 50
        
        score = 50
        
        # 淨流入評分
        net_flow = broker_flow.get('net_flow_count', 0)
        if net_flow > 1000:
            score += 25
        elif net_flow > 500:
            score += 15
        elif net_flow > 100:
            score += 10
        elif net_flow < -1000:
            score -= 25
        elif net_flow < -500:
            score -= 15
        
        # 趨勢評分
        flow_trend = broker_flow.get('flow_trend', 'neutral')
        if flow_trend == 'strong_buying':
            score += 15
        elif flow_trend == 'buying':
            score += 10
        elif flow_trend == 'strong_selling':
            score -= 15
        elif flow_trend == 'selling':
            score -= 10
        
        # 異常活動（可能是好事或壞事，需結合趨勢）
        if broker_flow.get('unusual_activity', False):
            if net_flow > 0:
                score += 5
            else:
                score -= 5
        
        # 法人比例
        inst_ratio = broker_flow.get('institutional_ratio', 0)
        if inst_ratio > 30:
            score += 10
        
        return max(0, min(100, score))
    
    def _score_institutional(self, institutional: Dict) -> float:
        """法人買賣評分 (0-100)"""
        if not institutional:
            return 50
        
        score = 50
        
        # 外資買賣
        foreign_net = institutional.get('foreign_net', 0)
        if foreign_net > 1000:
            score += 20
        elif foreign_net > 500:
            score += 10
        elif foreign_net < -1000:
            score -= 20
        elif foreign_net < -500:
            score -= 10
        
        # 投信買賣
        trust_net = institutional.get('trust_net', 0)
        if trust_net > 500:
            score += 15
        elif trust_net < -500:
            score -= 15
        
        return max(0, min(100, score))
    
    def _adjust_for_market(self, market_context: Dict) -> float:
        """市場環境調整 (-20 到 +20)"""
        if not market_context:
            return 0
        
        adjustment = 0
        
        # 大盤趨勢
        market_trend = market_context.get('market_trend', 'neutral')
        if market_trend == 'bullish':
            adjustment += 10
        elif market_trend == 'bearish':
            adjustment -= 10
        
        # 大盤漲跌幅
        twii_change = market_context.get('twii_change_pct', 0)
        if twii_change > 1:
            adjustment += 5
        elif twii_change < -1:
            adjustment -= 5
        
        return adjustment
    
    def _score_to_grade(self, score: float) -> str:
        """分數轉評級"""
        if score >= 85:
            return 'A+'
        elif score >= 75:
            return 'A'
        elif score >= 65:
            return 'B+'
        elif score >= 55:
            return 'B'
        elif score >= 45:
            return 'C'
        elif score >= 35:
            return 'D'
        else:
            return 'F'
    
    def _score_to_recommendation(self, score: float) -> str:
        """分數轉建議"""
        if score >= 80:
            return '強力買入'
        elif score >= 70:
            return '買入'
        elif score >= 60:
            return '持有'
        elif score >= 50:
            return '觀望'
        elif score >= 40:
            return '減碼'
        else:
            return '賣出'
    
    def _calculate_confidence(self, integrated_data: Dict) -> float:
        """計算信心分數"""
        confidence = 0
        max_confidence = 100
        
        # 數據完整性
        if integrated_data.get('fundamentals'):
            confidence += 25
        if integrated_data.get('technicals'):
            confidence += 25
        if integrated_data.get('broker_flow'):
            confidence += 25
        if integrated_data.get('institutional'):
            confidence += 15
        if integrated_data.get('market_context'):
            confidence += 10
        
        return min(confidence, max_confidence)
    
    def _calculate_target_price(self, current_price: float, score: float) -> float:
        """計算目標價"""
        if score >= 80:
            multiplier = 1.25
        elif score >= 70:
            multiplier = 1.20
        elif score >= 60:
            multiplier = 1.15
        else:
            multiplier = 1.10
        
        return round(current_price * multiplier, 2)
    
    def _calculate_stop_loss(self, current_price: float, technicals: Dict) -> float:
        """計算停損價"""
        # 使用 MA20 或固定比例
        ma20 = technicals.get('ma20', current_price * 0.92)
        
        stop_loss = min(ma20 * 0.98, current_price * 0.92)
        
        return round(stop_loss, 2)
    
    def _generate_recommendation(self, scores: Dict, integrated_data: Dict) -> Dict:
        """生成投資建議"""
        return {
            'action': scores['recommendation'],
            'grade': scores['final_grade'],
            'confidence': scores['confidence'],
            'entry_price': integrated_data.get('technicals', {}).get('current_price'),
            'target_price': scores.get('target_price'),
            'stop_loss': scores.get('stop_loss'),
            'holding_period': '中期 (1-3個月)',
            'key_reasons': self._extract_key_reasons(scores, integrated_data)
        }
    
    def _extract_key_reasons(self, scores: Dict, integrated_data: Dict) -> List[str]:
        """提取關鍵理由"""
        reasons = []
        
        # 基本面
        fund_score = scores['component_scores'].get('fundamentals', 50)
        if fund_score > 70:
            reasons.append('基本面強勁')
        elif fund_score < 40:
            reasons.append('基本面疲弱')
        
        # 技術面
        tech_score = scores['component_scores'].get('technicals', 50)
        if tech_score > 70:
            reasons.append('技術面看多')
        elif tech_score < 40:
            reasons.append('技術面看空')
        
        # 籌碼面
        broker_score = scores['component_scores'].get('broker_flow', 50)
        if broker_score > 70:
            reasons.append('主力買超')
        elif broker_score < 40:
            reasons.append('主力賣超')
        
        # 券商觀察
        broker_flow = integrated_data.get('broker_flow', {})
        if broker_flow.get('key_observations'):
            reasons.extend(broker_flow['key_observations'][:2])
        
        return reasons[:5]  # 最多5個理由
    
    def _assess_risk(self, integrated_data: Dict, scores: Dict) -> Dict:
        """風險評估"""
        risk_factors = []
        risk_level = 'medium'
        
        # 波動率風險
        volatility = integrated_data.get('technicals', {}).get('volatility', 30)
        if volatility > 40:
            risk_factors.append('高波動率')
            risk_level = 'high'
        
        # 流動性風險
        volume_ratio = integrated_data.get('technicals', {}).get('volume_ratio', 1)
        if volume_ratio < 0.5:
            risk_factors.append('成交量不足')
        
        # 基本面風險
        debt_ratio = integrated_data.get('fundamentals', {}).get('debt_to_equity', 0)
        if debt_ratio > 200:
            risk_factors.append('高負債比')
            risk_level = 'high'
        
        # 籌碼風險
        flow_trend = integrated_data.get('broker_flow', {}).get('flow_trend', 'neutral')
        if flow_trend in ['strong_selling', 'selling']:
            risk_factors.append('主力賣壓')
        
        # 綜合評分風險
        if scores['weighted_score'] < 40:
            risk_level = 'high'
        elif scores['weighted_score'] > 70:
            risk_level = 'low'
        
        return {
            'level': risk_level,
            'factors': risk_factors,
            'score': scores['weighted_score']
        }
    
    def _calculate_position_sizing(self, scores: Dict, integrated_data: Dict) -> Dict:
        """計算建議倉位"""
        score = scores['weighted_score']
        
        # 基礎倉位
        if score >= 80:
            base_position = 0.12
        elif score >= 70:
            base_position = 0.10
        elif score >= 60:
            base_position = 0.07
        elif score >= 50:
            base_position = 0.05
        else:
            base_position = 0.02
        
        # 波動率調整
        volatility = integrated_data.get('technicals', {}).get('volatility', 30)
        vol_adjustment = 30 / max(volatility, 10)
        
        adjusted_position = base_position * vol_adjustment
        
        # 限制最大倉位
        max_position = self.config['risk_parameters']['max_position_pct']
        final_position = min(adjusted_position, max_position)
        
        return {
            'position_pct': round(final_position * 100, 2),
            'position_ratio': round(final_position, 4),
            'risk_adjusted': True
        }
    
    def _empty_analysis_result(self, stock_code: str) -> Dict:
        """空的分析結果"""
        return {
            'metadata': {
                'stock_code': stock_code,
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'error': True
            },
            'scores': {
                'weighted_score': 0,
                'final_grade': 'N/A',
                'recommendation': '無法分析'
            }
        }
    
    async def batch_analyze_stocks(self, stock_codes: List[str], max_workers: int = 3) -> pd.DataFrame:
        """
        批量分析股票（帶超時控制）
        
        Args:
            stock_codes: 股票代碼列表
            max_workers: 最大並行數（減少以避免 yfinance 請求過快）
            
        Returns:
            分析結果 DataFrame
        """
        logger.info(f"📊 開始批量分析 {len(stock_codes)} 檔股票（每檔超時15秒）")
        
        results = []
        
        # 使用 semaphore 控制並行數
        semaphore = asyncio.Semaphore(max_workers)
        
        async def analyze_with_timeout(code):
            """帶超時的單股分析"""
            async with semaphore:
                try:
                    # 每個股票最多15秒
                    return await asyncio.wait_for(
                        self.analyze_stock(code),
                        timeout=15.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ 股票 {code} 分析超時")
                    return self._empty_analysis_result(code)
                except Exception as e:
                    logger.error(f"分析 {code} 失敗: {e}")
                    return self._empty_analysis_result(code)
        
        # 並行分析
        tasks = [analyze_with_timeout(code) for code in stock_codes]
        analyses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理結果
        for analysis in analyses:
            if isinstance(analysis, Exception):
                logger.error(f"分析失敗: {analysis}")
                continue
            
            if analysis.get('metadata', {}).get('error'):
                continue
            
            stock_code = analysis['metadata']['stock_code']
            scores = analysis['scores']
            recommendation = analysis['recommendation']
            risk = analysis['risk_assessment']
            position = analysis['position_sizing']
            
            results.append({
                '股票代碼': stock_code,
                '綜合評分': scores['weighted_score'],
                '評級': scores['final_grade'],
                '建議動作': scores['recommendation'],
                '信心分數': scores['confidence'],
                '目標價': scores.get('target_price', 'N/A'),
                '停損價': scores.get('stop_loss', 'N/A'),
                '風險等級': risk['level'],
                '建議倉位(%)': position['position_pct'],
                '基本面分數': scores['component_scores'].get('fundamentals', 0),
                '技術面分數': scores['component_scores'].get('technicals', 0),
                '籌碼面分數': scores['component_scores'].get('broker_flow', 0),
                '分析時間': analysis['metadata']['analysis_date']
            })
        
        if results:
            df = pd.DataFrame(results)
            df = df.sort_values('綜合評分', ascending=False)
            logger.info(f"✅ 批量分析完成，共 {len(df)} 檔股票")
            return df
        else:
            logger.warning("⚠️ 批量分析無有效結果")
            return pd.DataFrame()
    
    def export_report(self, df: pd.DataFrame, format: str = 'csv', filename: str = None):
        """匯出報告"""
        if df.empty:
            logger.warning("無資料可匯出")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'stock_analysis_report_{timestamp}'
        
        try:
            if format == 'csv':
                filepath = f'/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/reports/{filename}.csv'
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
                logger.info(f"✅ CSV報告已匯出: {filepath}")
                return filepath
            
            elif format == 'excel':
                filepath = f'/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/reports/{filename}.xlsx'
                df.to_excel(filepath, index=False, engine='openpyxl')
                logger.info(f"✅ Excel報告已匯出: {filepath}")
                return filepath
            
            else:
                logger.error(f"不支援的格式: {format}")
                return None
                
        except Exception as e:
            logger.error(f"匯出報告失敗: {e}")
            return None


# 全域實例
integrated_selector = IntegratedStockSelector()


# ==================== 便捷函數 ====================

async def analyze_single_stock(stock_code: str) -> Dict:
    """分析單一股票"""
    return await integrated_selector.analyze_stock(stock_code)


async def analyze_multiple_stocks(stock_codes: List[str]) -> pd.DataFrame:
    """分析多檔股票"""
    return await integrated_selector.batch_analyze_stocks(stock_codes)


async def get_top_recommendations(stock_codes: List[str], top_n: int = 10) -> pd.DataFrame:
    """獲取前N名推薦股票"""
    df = await integrated_selector.batch_analyze_stocks(stock_codes)
    
    if df.empty:
        return df
    
    # 篩選買入建議
    buy_df = df[df['建議動作'].isin(['強力買入', '買入'])]
    
    return buy_df.head(top_n)
