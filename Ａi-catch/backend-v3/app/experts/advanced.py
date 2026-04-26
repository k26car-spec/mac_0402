"""
Pattern Recognition and Market Sentiment Experts
形态识别和市场情绪专家
"""

from typing import Dict, Any, Optional
from decimal import Decimal

from .base import BaseExpert, ExpertSignal, SignalType, TimeFrame


class PatternRecognitionExpert(BaseExpert):
    """形态识别专家 - K线形态识别"""
    
    def __init__(self):
        super().__init__("形态识别")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        K线形态识别
        
        检测：
        1. 经典K线形态（锤子线、吞没等）
        2. 多K线组合
        3. 缺口分析
        """
        indicators = {}
        reasoning_parts = []
        
        # 获取K线数据
        open_price = data.get("open", 0)
        high = data.get("high", 0)
        low = data.get("low", 0)
        close = data.get("close", 0)
        prev_close = data.get("prev_close", close)
        
        if close == 0 or open_price == 0:
            return None
        
        # 计算实体和影线
        body = abs(close - open_price)
        upper_shadow = high - max(close, open_price)
        lower_shadow = min(close, open_price) - low
        total_range = high - low
        
        if total_range == 0:
            return None
        
        # 1. 锤子线/上吊线检测
        if body > 0:
            body_ratio = body / total_range
            lower_ratio = lower_shadow / total_range
            upper_ratio = upper_shadow / total_range
            
            # 锤子线：实体小、下影线长
            if body_ratio < 0.3 and lower_ratio > 0.5 and upper_ratio < 0.1:
                if close > open_price:
                    indicators["hammer"] = 0.7
                    reasoning_parts.append("锤子线形态(看涨)")
                else:
                    indicators["hanging_man"] = -0.6
                    reasoning_parts.append("上吊线形态(看跌)")
            
            # 倒锤子线/射击之星
            elif body_ratio < 0.3 and upper_ratio > 0.5 and lower_ratio < 0.1:
                if close > open_price:
                    indicators["inverted_hammer"] = 0.6
                    reasoning_parts.append("倒锤子线(可能反转)")
                else:
                    indicators["shooting_star"] = -0.7
                    reasoning_parts.append("射击之星(看跌)")
        
        # 2. 十字星检测
        if body / total_range < 0.1:
            indicators["doji"] = 0.3
            reasoning_parts.append("十字星(趋势不明)")
        
        # 3. 长实体K线
        if body / total_range > 0.7:
            if close > open_price:
                indicators["strong_bullish"] = 0.8
                reasoning_parts.append("长阳线(强势)")
            else:
                indicators["strong_bearish"] = -0.8
                reasoning_parts.append("长阴线(弱势)")
        
        # 4. 缺口分析
        gap = (open_price - prev_close) / prev_close if prev_close > 0 else 0
        if abs(gap) > 0.02:
            if gap > 0:
                indicators["gap_up"] = min(gap / 0.05, 0.7)
                reasoning_parts.append(f"向上跳空{gap*100:.1f}%")
            else:
                indicators["gap_down"] = max(gap / 0.05, -0.7)
                reasoning_parts.append(f"向下跳空{abs(gap)*100:.1f}%")
        
        # 5. 包含关系（简化版）
        prev_high = data.get("prev_high", high)
        prev_low = data.get("prev_low", low)
        
        if high > prev_high and low < prev_low:
            if close > open_price:
                indicators["engulfing_bullish"] = 0.8
                reasoning_parts.append("看涨吞没")
            else:
                indicators["engulfing_bearish"] = -0.8
                reasoning_parts.append("看跌吞没")
        
        if not indicators:
            return None
        
        strength = self._calculate_strength(indicators)
        confidence = self._calculate_confidence(indicators)
        
        avg_indicator = sum(indicators.values()) / len(indicators)
        
        if avg_indicator > 0.6:
            signal_type = SignalType.STRONG_BUY
        elif avg_indicator > 0.2:
            signal_type = SignalType.BUY
        elif avg_indicator < -0.6:
            signal_type = SignalType.STRONG_SELL
        elif avg_indicator < -0.2:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "无明显形态"
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "open": float(open_price),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "body_ratio": float(body / total_range) if total_range > 0 else 0,
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )


class VolatilityExpert(BaseExpert):
    """波动率专家 - ATR和波动性分析"""
    
    def __init__(self):
        super().__init__("波动率")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        波动率分析
        
        检测：
        1. ATR（平均真实波幅）
        2. 波动率收缩/扩张
        3. 布林带
        """
        indicators = {}
        reasoning_parts = []
        
        current_price = data.get("current_price", 0)
        atr = data.get("atr", 0)  # Average True Range
        atr_avg = data.get("atr_avg", atr)  # ATR均值
        bb_upper = data.get("bb_upper", current_price * 1.05)  # 布林上轨
        bb_lower = data.get("bb_lower", current_price * 0.95)  # 布林下轨
        bb_middle = data.get("bb_middle", current_price)  # 布林中轨
        
        if current_price == 0:
            return None
        
        # 1. ATR分析
        if atr_avg > 0:
            atr_ratio = atr / atr_avg
            
            if atr_ratio > 1.5:
                indicators["high_volatility"] = -0.4
                reasoning_parts.append(f"波动率激增{(atr_ratio-1)*100:.0f}%")
            elif atr_ratio < 0.6:
                indicators["volatility_squeeze"] = 0.6
                reasoning_parts.append("波动率收缩(可能突破)")
        
        # 2. 布林带分析
        bb_width = bb_upper - bb_lower
        bb_position = (current_price - bb_lower) / bb_width if bb_width > 0 else 0.5
        
        if bb_position > 0.95:
            indicators["bb_overbought"] = -0.7
            reasoning_parts.append("触及布林上轨(超买)")
        elif bb_position < 0.05:
            indicators["bb_oversold"] = 0.7
            reasoning_parts.append("触及布林下轨(超卖)")
        elif 0.4 < bb_position < 0.6:
            indicators["bb_middle"] = 0.0
            reasoning_parts.append("布林中轨附近")
        
        # 3. 布林带宽度（相对波动率）
        bb_width_pct = bb_width / bb_middle if bb_middle > 0 else 0
        if bb_width_pct < 0.04:
            indicators["bb_squeeze"] = 0.5
            reasoning_parts.append("布林带收窄(待突破)")
        elif bb_width_pct > 0.12:
            indicators["bb_expansion"] = -0.3
            reasoning_parts.append("布林带扩张(高波动)")
        
        # 4. 价格相对布林中轨
        distance_to_middle = (current_price - bb_middle) / bb_middle if bb_middle > 0 else 0
        if abs(distance_to_middle) > 0.03:
            if distance_to_middle > 0:
                indicators["above_bb_mid"] = 0.4
                reasoning_parts.append("强于布林中轨")
            else:
                indicators["below_bb_mid"] = -0.4
                reasoning_parts.append("弱于布林中轨")
        
        if not indicators:
            return None
        
        strength = self._calculate_strength(indicators)
        confidence = self._calculate_confidence(indicators)
        
        avg_indicator = sum(indicators.values()) / len(indicators)
        
        if avg_indicator > 0.5:
            signal_type = SignalType.BUY
        elif avg_indicator > 0:
            signal_type = SignalType.HOLD
        elif avg_indicator < -0.5:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "波动率正常"
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "atr": float(atr),
                "atr_ratio": float(atr / atr_avg) if atr_avg > 0 else 1.0,
                "bb_position": float(bb_position),
                "bb_width_pct": float(bb_width_pct),
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )


class MarketSentimentExpert(BaseExpert):
    """市场情绪专家"""
    
    def __init__(self):
        super().__init__("市场情绪")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        市场情绪分析
        
        检测：
        1. 市场宽度（涨跌家数比）
        2. 成交金额变化
        3. 外资动向
        """
        indicators = {}
        reasoning_parts = []
        
        # 1. 市场宽度
        advance_decline_ratio = data.get("advance_decline_ratio", 1.0)  # 涨跌比
        
        if advance_decline_ratio > 2.0:
            indicators["strong_breadth"] = 0.7
            reasoning_parts.append(f"市场宽度强劲(涨跌比{advance_decline_ratio:.1f})")
        elif advance_decline_ratio < 0.5:
            indicators["weak_breadth"] = -0.7
            reasoning_parts.append(f"市场宽度疲弱(涨跌比{advance_decline_ratio:.1f})")
        
        # 2. 成交金额变化
        value_change = data.get("value_change", 0)  # 成交金额变化
        if abs(value_change) > 0.3:
            if value_change > 0:
                indicators["value_increase"] = min(value_change, 0.8)
                reasoning_parts.append(f"成交金额大增{value_change*100:.0f}%")
            else:
                indicators["value_decrease"] = max(value_change, -0.5)
                reasoning_parts.append("成交金额萎缩")
        
        # 3. 外资动向
        foreign_net_buy = data.get("foreign_net_buy", 0)  # 外资净买（百万）
        if abs(foreign_net_buy) > 100:
            if foreign_net_buy > 0:
                strength = min(foreign_net_buy / 500, 0.8)
                indicators["foreign_buying"] = strength
                reasoning_parts.append(f"外资买超{foreign_net_buy:.0f}百万")
            else:
                strength = max(foreign_net_buy / 500, -0.8)
                indicators["foreign_selling"] = strength
                reasoning_parts.append(f"外资卖超{abs(foreign_net_buy):.0f}百万")
        
        # 4. 恐慌/贪婪指数（简化版）
        fear_greed = data.get("fear_greed_index", 50)  # 0-100
        if fear_greed > 75:
            indicators["extreme_greed"] = -0.6
            reasoning_parts.append(f"市场贪婪({fear_greed:.0f})")
        elif fear_greed < 25:
            indicators["extreme_fear"] = 0.7
            reasoning_parts.append(f"市场恐慌({fear_greed:.0f})")
        
        if not indicators:
            # 如果没有特殊情绪信号，返回中性
            return None
        
        strength = self._calculate_strength(indicators)
        confidence = self._calculate_confidence(indicators)
        
        avg_indicator = sum(indicators.values()) / len(indicators)
        
        if avg_indicator > 0.5:
            signal_type = SignalType.BUY
        elif avg_indicator > 0:
            signal_type = SignalType.HOLD
        elif avg_indicator < -0.5:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "市场情绪中性"
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "advance_decline_ratio": float(advance_decline_ratio),
                "foreign_net_buy": float(foreign_net_buy),
                "fear_greed_index": float(fear_greed),
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )
