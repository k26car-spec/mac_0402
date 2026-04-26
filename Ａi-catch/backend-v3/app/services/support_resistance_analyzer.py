"""
撐壓趨勢轉折分析服務
Support & Resistance Trend Reversal Analysis

功能：
1. 撐壓位偵測（動態計算多層級撐壓）
2. 趨勢轉折偵測（多指標綜合判斷）
3. 突破/跌破訊號
4. 風險回報評估
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class SupportResistanceLevel:
    """撐壓位"""
    price: float
    type: str  # 'support' 或 'resistance'
    strength: float  # 0-100 強度
    source: str  # 來源：'ma', 'pivot', 'fibonacci', 'history', 'round'
    description: str
    distance_pct: float  # 與當前價格距離百分比


@dataclass
class TrendReversalSignal:
    """趨勢轉折訊號"""
    type: str  # 'bullish_reversal', 'bearish_reversal', 'continuation'
    strength: float  # 0-100 強度
    confidence: float  # 0-1 信心度
    signals: List[str]  # 訊號列表
    description: str
    action: str  # 'buy', 'sell', 'hold'


@dataclass
class TrendStatus:
    """趨勢狀態"""
    short_term: str  # 'bullish', 'bearish', 'sideways'
    mid_term: str
    long_term: str
    overall: str
    strength: float  # 趨勢強度 0-100


@dataclass
class SupportResistanceAnalysis:
    """撐壓趨勢分析結果"""
    stock_code: str
    stock_name: str
    current_price: float
    timestamp: str
    
    # 撐壓位分析
    resistance_levels: List[Dict]
    support_levels: List[Dict]
    nearest_resistance: float
    nearest_support: float
    resistance_distance_pct: float
    support_distance_pct: float
    vwap: float  # 🆕 新增真實 VWAP
    
    # 趨勢狀態
    trend_status: Dict
    
    # 轉折訊號
    reversal_signal: Dict
    
    # 關鍵價位
    key_levels: List[Dict]
    
    # 交易建議
    recommendation: str
    risk_reward_analysis: Dict
    
    # 評分
    overall_score: float


class SupportResistanceAnalyzer:
    """撐壓趨勢轉折分析器"""
    
    def __init__(self):
        self.cache = {}
    
    async def analyze(self, stock_code: str) -> Optional[Dict]:
        """
        執行撐壓趨勢轉折分析
        
        Returns:
            完整的撐壓趨勢分析結果
        """
        try:
            # 取得股票價格資料
            price_data = await self._get_price_data(stock_code)
            if not price_data or not price_data.get('current_price'):
                logger.warning(f"無法取得 {stock_code} 價格資料")
                return None
            
            # 取得股票名稱
            stock_name = await self._get_stock_name(stock_code)
            
            current_price = price_data['current_price']
            
            # 1. 計算撐壓位
            resistance_levels = self._calculate_resistance_levels(price_data)
            support_levels = self._calculate_support_levels(price_data)
            
            # 2. 分析趨勢狀態
            trend_status = self._analyze_trend_status(price_data)
            
            # 3. 偵測趨勢轉折
            reversal_signal = self._detect_reversal_signal(price_data, trend_status)
            
            # 4. 計算關鍵價位
            key_levels = self._calculate_key_levels(price_data, resistance_levels, support_levels)
            
            # 5. 風險回報分析
            risk_reward = self._analyze_risk_reward(
                current_price,
                resistance_levels,
                support_levels
            )
            
            # 6. 生成交易建議
            recommendation = self._generate_recommendation(
                trend_status, reversal_signal, risk_reward
            )
            
            # 7. 計算綜合評分
            overall_score = self._calculate_overall_score(
                trend_status, reversal_signal, risk_reward
            )
            
            # 最近撐壓
            nearest_resistance = resistance_levels[0]['price'] if resistance_levels else current_price * 1.05
            nearest_support = support_levels[0]['price'] if support_levels else current_price * 0.95
            
            result = SupportResistanceAnalysis(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                timestamp=datetime.now().isoformat(),
                resistance_levels=[asdict(r) if isinstance(r, SupportResistanceLevel) else r for r in resistance_levels],
                support_levels=[asdict(s) if isinstance(s, SupportResistanceLevel) else s for s in support_levels],
                nearest_resistance=nearest_resistance,
                nearest_support=nearest_support,
                resistance_distance_pct=round((nearest_resistance - current_price) / current_price * 100, 2),
                support_distance_pct=round((current_price - nearest_support) / current_price * 100, 2),
                vwap=price_data.get('vwap', current_price), # 🆕 帶入真實 VWAP
                trend_status=trend_status if isinstance(trend_status, dict) else asdict(trend_status),
                reversal_signal=reversal_signal if isinstance(reversal_signal, dict) else asdict(reversal_signal),
                key_levels=key_levels,
                recommendation=recommendation,
                risk_reward_analysis=risk_reward,
                overall_score=overall_score
            )
            
            return asdict(result)
            
        except Exception as e:
            logger.error(f"撐壓趨勢分析失敗 {stock_code}: {e}")
            return None
    
    async def _get_price_data(self, stock_code: str) -> Dict:
        """取得股票價格資料"""
        try:
            from app.services.stock_comprehensive_analyzer import StockComprehensiveAnalyzer
            analyzer = StockComprehensiveAnalyzer()
            return await analyzer._get_stock_price_data(stock_code)
        except Exception as e:
            logger.error(f"取得價格資料失敗: {e}")
            return {}
    
    async def _get_stock_name(self, stock_code: str) -> str:
        """取得股票名稱"""
        try:
            from app.services.stock_comprehensive_analyzer import get_stock_name
            return get_stock_name(stock_code)
        except:
            return stock_code
    
    def _calculate_resistance_levels(self, price_data: Dict) -> List[Dict]:
        """計算多層級壓力位"""
        current_price = price_data.get('current_price', 0)
        levels = []
        
        if not current_price:
            return []
        
        # 1. 均線壓力
        ma_levels = ['ma5', 'ma10', 'ma20', 'ma60']
        for ma in ma_levels:
            ma_value = price_data.get(ma, 0)
            if ma_value and ma_value > current_price:
                distance = (ma_value - current_price) / current_price * 100
                levels.append({
                    'price': round(ma_value, 2),
                    'type': 'resistance',
                    'strength': self._calculate_ma_strength(ma),
                    'source': 'ma',
                    'description': f'{ma.upper()} 均線壓力',
                    'distance_pct': round(distance, 2)
                })
        
        # 2. 現有壓力位
        for key in ['resistance_1', 'resistance_2']:
            value = price_data.get(key, 0)
            if value and value > current_price:
                distance = (value - current_price) / current_price * 100
                levels.append({
                    'price': round(value, 2),
                    'type': 'resistance',
                    'strength': 70 if key == 'resistance_1' else 60,
                    'source': 'history',
                    'description': '歷史壓力位' + (' (近)' if key == 'resistance_1' else ' (遠)'),
                    'distance_pct': round(distance, 2)
                })
        
        # 3. 整數關卡
        round_up = ((current_price // 10) + 1) * 10
        if round_up > current_price:
            distance = (round_up - current_price) / current_price * 100
            levels.append({
                'price': round(round_up, 2),
                'type': 'resistance',
                'strength': 50,
                'source': 'round',
                'description': f'整數關卡 {int(round_up)}',
                'distance_pct': round(distance, 2)
            })
        
        # 4. 費波納契 (38.2%, 50%, 61.8% 回撤)
        # 假設最近高低點差異作為計算基礎
        high = price_data.get('high', current_price * 1.05)
        low = price_data.get('low', current_price * 0.95)
        price_range = high - low
        
        fib_levels = [
            (0.382, '費波納契 38.2%'),
            (0.5, '費波納契 50%'),
            (0.618, '費波納契 61.8%'),
        ]
        
        for ratio, desc in fib_levels:
            fib_price = low + price_range * (1 + ratio)
            if fib_price > current_price:
                distance = (fib_price - current_price) / current_price * 100
                levels.append({
                    'price': round(fib_price, 2),
                    'type': 'resistance',
                    'strength': 55,
                    'source': 'fibonacci',
                    'description': desc,
                    'distance_pct': round(distance, 2)
                })
        
        # 排序：按價格由低到高（最近的壓力在前）
        levels.sort(key=lambda x: x['price'])
        
        return levels[:5]  # 返回最近 5 個壓力位
    
    def _calculate_support_levels(self, price_data: Dict) -> List[Dict]:
        """計算多層級支撐位"""
        current_price = price_data.get('current_price', 0)
        levels = []
        
        if not current_price:
            return []
        
        # 1. 均線支撐
        ma_levels = ['ma5', 'ma10', 'ma20', 'ma60']
        for ma in ma_levels:
            ma_value = price_data.get(ma, 0)
            if ma_value and ma_value < current_price:
                distance = (current_price - ma_value) / current_price * 100
                levels.append({
                    'price': round(ma_value, 2),
                    'type': 'support',
                    'strength': self._calculate_ma_strength(ma),
                    'source': 'ma',
                    'description': f'{ma.upper()} 均線支撐',
                    'distance_pct': round(distance, 2)
                })
        
        # 2. 現有支撐位
        for key in ['support_1', 'support_2']:
            value = price_data.get(key, 0)
            if value and value < current_price:
                distance = (current_price - value) / current_price * 100
                levels.append({
                    'price': round(value, 2),
                    'type': 'support',
                    'strength': 70 if key == 'support_1' else 60,
                    'source': 'history',
                    'description': '歷史支撐位' + (' (近)' if key == 'support_1' else ' (遠)'),
                    'distance_pct': round(distance, 2)
                })
        
        # 3. 整數關卡
        round_down = (current_price // 10) * 10
        if round_down < current_price and round_down > 0:
            distance = (current_price - round_down) / current_price * 100
            levels.append({
                'price': round(round_down, 2),
                'type': 'support',
                'strength': 50,
                'source': 'round',
                'description': f'整數關卡 {int(round_down)}',
                'distance_pct': round(distance, 2)
            })
        
        # 排序：按價格由高到低（最近的支撐在前）
        levels.sort(key=lambda x: x['price'], reverse=True)
        
        return levels[:5]  # 返回最近 5 個支撐位
    
    def _calculate_ma_strength(self, ma_type: str) -> float:
        """計算均線強度權重"""
        weights = {'ma5': 60, 'ma10': 70, 'ma20': 85, 'ma60': 90}
        return weights.get(ma_type, 50)
    
    def _analyze_trend_status(self, price_data: Dict) -> Dict:
        """分析趨勢狀態"""
        current_price = price_data.get('current_price', 0)
        ma5 = price_data.get('ma5', current_price)
        ma10 = price_data.get('ma10', current_price)
        ma20 = price_data.get('ma20', current_price)
        ma60 = price_data.get('ma60', current_price)
        
        # 短期趨勢（5日、10日均線）
        if current_price > ma5 > ma10:
            short_term = 'bullish'
            short_strength = 80
        elif current_price < ma5 < ma10:
            short_term = 'bearish'
            short_strength = 80
        elif current_price > ma5:
            short_term = 'bullish'
            short_strength = 60
        elif current_price < ma5:
            short_term = 'bearish'
            short_strength = 60
        else:
            short_term = 'sideways'
            short_strength = 50
        
        # 中期趨勢（20日均線）
        if current_price > ma20 and ma5 > ma20:
            mid_term = 'bullish'
            mid_strength = 75
        elif current_price < ma20 and ma5 < ma20:
            mid_term = 'bearish'
            mid_strength = 75
        else:
            mid_term = 'sideways'
            mid_strength = 50
        
        # 長期趨勢（60日均線）
        if current_price > ma60 and ma20 > ma60:
            long_term = 'bullish'
            long_strength = 70
        elif current_price < ma60 and ma20 < ma60:
            long_term = 'bearish'
            long_strength = 70
        else:
            long_term = 'sideways'
            long_strength = 50
        
        # 綜合趨勢
        bullish_count = [short_term, mid_term, long_term].count('bullish')
        bearish_count = [short_term, mid_term, long_term].count('bearish')
        
        if bullish_count >= 2:
            overall = 'bullish'
        elif bearish_count >= 2:
            overall = 'bearish'
        else:
            overall = 'sideways'
        
        # 計算趨勢強度
        avg_strength = (short_strength + mid_strength + long_strength) / 3
        
        # 均線排列加分
        if ma5 > ma10 > ma20 > ma60:
            avg_strength = min(avg_strength + 20, 100)  # 完美多頭排列
        elif ma5 < ma10 < ma20 < ma60:
            avg_strength = min(avg_strength + 20, 100)  # 完美空頭排列
        
        return {
            'short_term': short_term,
            'mid_term': mid_term,
            'long_term': long_term,
            'overall': overall,
            'strength': round(avg_strength, 1),
            'ma_arrangement': price_data.get('ma_arrangement', '未知'),
            'ma_trend': price_data.get('ma_trend', '未知')
        }
    
    def _detect_reversal_signal(self, price_data: Dict, trend_status: Dict) -> Dict:
        """偵測趨勢轉折訊號"""
        signals = []
        signal_type = 'continuation'
        confidence = 0.5
        strength = 50
        
        current_price = price_data.get('current_price', 0)
        prev_close = price_data.get('prev_close', current_price)
        change_pct = price_data.get('change_pct', 0)
        
        # 技術指標
        rsi = price_data.get('rsi_14', 50)
        kd_k = price_data.get('kd_k', 50)
        kd_d = price_data.get('kd_d', 50)
        macd = price_data.get('macd', 0)
        macd_histogram = price_data.get('macd_histogram', 0)
        
        # 量價分析
        volume_analysis = price_data.get('volume_price_analysis', {})
        volume_ratio = price_data.get('volume_ratio', 1)
        divergence_type = volume_analysis.get('divergence_type', 'none')
        
        # === 看多轉折訊號 ===
        bullish_signals = []
        
        # 1. RSI 超賣反彈
        if rsi < 30:
            bullish_signals.append('RSI 超賣 (<30)，可能反彈')
        elif rsi < 40 and rsi > price_data.get('prev_rsi', rsi):
            bullish_signals.append('RSI 從低檔回升')
        
        # 2. KD 黃金交叉
        if kd_k > kd_d and kd_k < 30:
            bullish_signals.append('KD 低檔黃金交叉')
        elif kd_k > kd_d and kd_k < 50:
            bullish_signals.append('KD 黃金交叉')
        
        # 3. MACD 翻多
        if macd_histogram > 0 and macd < 0:
            bullish_signals.append('MACD 柱狀體翻紅')
        
        # 4. 量價背離（看漲）
        if divergence_type == 'bullish_divergence':
            bullish_signals.append('量價看漲背離')
        
        # 5. 突破關鍵均線
        ma_signal = price_data.get('ma_signal', '')
        if '突破MA20' in ma_signal:
            bullish_signals.append('突破 20 日均線')
        elif '突破MA10' in ma_signal:
            bullish_signals.append('突破 10 日均線')
        
        # 6. 爆量紅K
        if volume_ratio > 1.5 and change_pct > 2:
            bullish_signals.append('放量上漲 (+{:.1f}%)'.format(change_pct))
        
        # === 看空轉折訊號 ===
        bearish_signals = []
        
        # 1. RSI 超買回落
        if rsi > 70:
            bearish_signals.append('RSI 超買 (>70)，可能回落')
        elif rsi > 60 and rsi < price_data.get('prev_rsi', rsi):
            bearish_signals.append('RSI 從高檔下滑')
        
        # 2. KD 死亡交叉
        if kd_k < kd_d and kd_k > 70:
            bearish_signals.append('KD 高檔死亡交叉')
        elif kd_k < kd_d and kd_k > 50:
            bearish_signals.append('KD 死亡交叉')
        
        # 3. MACD 翻空
        if macd_histogram < 0 and macd > 0:
            bearish_signals.append('MACD 柱狀體翻綠')
        
        # 4. 量價背離（看跌）
        if divergence_type == 'bearish_divergence':
            bearish_signals.append('量價看跌背離')
        
        # 5. 跌破關鍵均線
        if '跌破MA20' in ma_signal:
            bearish_signals.append('跌破 20 日均線')
        elif '跌破MA10' in ma_signal:
            bearish_signals.append('跌破 10 日均線')
        
        # 6. 爆量黑K
        if volume_ratio > 1.5 and change_pct < -2:
            bearish_signals.append('放量下跌 ({:.1f}%)'.format(change_pct))
        
        # === 判斷轉折類型 ===
        if len(bullish_signals) >= 2 and trend_status['overall'] != 'bullish':
            signal_type = 'bullish_reversal'
            signals = bullish_signals
            strength = min(50 + len(bullish_signals) * 15, 95)
            confidence = min(0.5 + len(bullish_signals) * 0.1, 0.9)
            action = 'buy'
            description = '多重看多轉折訊號出現，空轉多機率提高'
        elif len(bearish_signals) >= 2 and trend_status['overall'] != 'bearish':
            signal_type = 'bearish_reversal'
            signals = bearish_signals
            strength = min(50 + len(bearish_signals) * 15, 95)
            confidence = min(0.5 + len(bearish_signals) * 0.1, 0.9)
            action = 'sell'
            description = '多重看空轉折訊號出現，多轉空機率提高'
        elif len(bullish_signals) >= 1 and trend_status['overall'] == 'bullish':
            signal_type = 'continuation'
            signals = bullish_signals
            strength = 60
            confidence = 0.7
            action = 'hold'
            description = '多頭趨勢持續中'
        elif len(bearish_signals) >= 1 and trend_status['overall'] == 'bearish':
            signal_type = 'continuation'
            signals = bearish_signals
            strength = 60
            confidence = 0.7
            action = 'hold'
            description = '空頭趨勢持續中'
        else:
            signal_type = 'neutral'
            signals = ['暫無明確轉折訊號']
            strength = 50
            confidence = 0.5
            action = 'hold'
            description = '趨勢不明，建議觀望'
        
        return {
            'type': signal_type,
            'strength': strength,
            'confidence': round(confidence, 2),
            'signals': signals[:5],  # 最多顯示 5 個訊號
            'description': description,
            'action': action,
            'bullish_count': len(bullish_signals),
            'bearish_count': len(bearish_signals)
        }
    
    def _calculate_key_levels(
        self,
        price_data: Dict,
        resistance_levels: List[Dict],
        support_levels: List[Dict]
    ) -> List[Dict]:
        """計算關鍵價位"""
        current_price = price_data.get('current_price', 0)
        key_levels = []
        
        # 加入最強壓力位
        if resistance_levels:
            strongest_r = max(resistance_levels, key=lambda x: x['strength'])
            key_levels.append({
                'price': strongest_r['price'],
                'type': 'key_resistance',
                'importance': 'high',
                'description': f"關鍵壓力: {strongest_r['description']}"
            })
        
        # 加入最強支撐位
        if support_levels:
            strongest_s = max(support_levels, key=lambda x: x['strength'])
            key_levels.append({
                'price': strongest_s['price'],
                'type': 'key_support',
                'importance': 'high',
                'description': f"關鍵支撐: {strongest_s['description']}"
            })
        
        # 計算可能的突破點
        if resistance_levels:
            nearest_r = resistance_levels[0]
            key_levels.append({
                'price': nearest_r['price'],
                'type': 'breakout_target',
                'importance': 'medium',
                'description': f"突破目標價: {nearest_r['price']}"
            })
        
        # 計算停損點
        if support_levels:
            nearest_s = support_levels[0]
            key_levels.append({
                'price': nearest_s['price'],
                'type': 'stop_loss',
                'importance': 'high',
                'description': f"建議停損: {nearest_s['price']}"
            })
        
        return key_levels
    
    def _analyze_risk_reward(
        self,
        current_price: float,
        resistance_levels: List[Dict],
        support_levels: List[Dict]
    ) -> Dict:
        """風險回報分析"""
        if not resistance_levels or not support_levels or not current_price:
            return {
                'risk_reward_ratio': 0,
                'potential_upside_pct': 0,
                'potential_downside_pct': 0,
                'assessment': '資料不足',
                'recommendation': 'hold'
            }
        
        # 最近的壓力和支撐
        nearest_resistance = resistance_levels[0]['price']
        nearest_support = support_levels[0]['price']
        
        # 計算潛在漲跌幅
        potential_upside = (nearest_resistance - current_price) / current_price * 100
        potential_downside = (current_price - nearest_support) / current_price * 100
        
        # 計算風報比
        if potential_downside > 0:
            risk_reward_ratio = potential_upside / potential_downside
        else:
            risk_reward_ratio = 0
        
        # 評估
        if risk_reward_ratio >= 3:
            assessment = '優質交易機會 (RR >= 3:1)'
            recommendation = 'buy'
        elif risk_reward_ratio >= 2:
            assessment = '中等機會 (RR >= 2:1)'
            recommendation = 'consider'
        elif risk_reward_ratio >= 1:
            assessment = '一般機會 (RR >= 1:1)'
            recommendation = 'caution'
        else:
            assessment = '風險過高 (RR < 1:1)'
            recommendation = 'avoid'
        
        return {
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'potential_upside_pct': round(potential_upside, 2),
            'potential_downside_pct': round(potential_downside, 2),
            'target_price': round(nearest_resistance, 2),
            'stop_loss_price': round(nearest_support, 2),
            'assessment': assessment,
            'recommendation': recommendation
        }
    
    def _generate_recommendation(
        self,
        trend_status: Dict,
        reversal_signal: Dict,
        risk_reward: Dict
    ) -> str:
        """生成交易建議"""
        reversal_type = reversal_signal.get('type', 'neutral')
        reversal_action = reversal_signal.get('action', 'hold')
        rr_ratio = risk_reward.get('risk_reward_ratio', 0)
        trend_overall = trend_status.get('overall', 'sideways')
        
        # 綜合判斷
        if reversal_type == 'bullish_reversal' and rr_ratio >= 2:
            return '🟢 強力買進 - 趨勢轉折訊號明確，風報比佳'
        elif reversal_type == 'bullish_reversal':
            return '🟡 觀察買進 - 出現看多轉折，注意風險控制'
        elif reversal_type == 'bearish_reversal':
            return '🔴 減碼/觀望 - 出現看空轉折訊號'
        elif trend_overall == 'bullish' and rr_ratio >= 2:
            return '🟢 趨勢買進 - 多頭趨勢中，可考慮進場'
        elif trend_overall == 'bearish':
            return '🔴 觀望 - 空頭趨勢中，不建議進場'
        else:
            return '⚪ 持平觀望 - 趨勢不明，等待訊號'
    
    def _calculate_overall_score(
        self,
        trend_status: Dict,
        reversal_signal: Dict,
        risk_reward: Dict
    ) -> float:
        """計算綜合評分 (0-100)"""
        score = 50  # 基準分
        
        # 趨勢加減分
        trend = trend_status.get('overall', 'sideways')
        if trend == 'bullish':
            score += 15
        elif trend == 'bearish':
            score -= 15
        
        # 趨勢強度
        trend_strength = trend_status.get('strength', 50)
        score += (trend_strength - 50) * 0.2
        
        # 轉折訊號
        reversal_type = reversal_signal.get('type', 'neutral')
        reversal_strength = reversal_signal.get('strength', 50)
        if reversal_type == 'bullish_reversal':
            score += reversal_strength * 0.2
        elif reversal_type == 'bearish_reversal':
            score -= reversal_strength * 0.2
        
        # 風報比
        rr_ratio = risk_reward.get('risk_reward_ratio', 1)
        if rr_ratio >= 3:
            score += 15
        elif rr_ratio >= 2:
            score += 10
        elif rr_ratio >= 1:
            score += 5
        else:
            score -= 10
        
        return max(0, min(100, round(score, 1)))


# 全域實例
support_resistance_analyzer = SupportResistanceAnalyzer()
