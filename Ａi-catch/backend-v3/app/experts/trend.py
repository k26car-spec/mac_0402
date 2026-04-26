"""
Trend and Support/Resistance Experts
趋势识别和支撑阻力专家
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal

from .base import BaseExpert, ExpertSignal, SignalType, TimeFrame


class TrendExpert(BaseExpert):
    """趋势识别专家"""
    
    def __init__(self):
        super().__init__("趋势识别")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        趋势识别分析
        
        检测：
        1. 均线趋势（多头/空头排列）
        2. 价格趋势（上升/下降/盘整）
        3. 趋势强度
        """
        indicators = {}
        reasoning_parts = []
        
        current_price = data.get("current_price", 0)
        ma5 = data.get("ma5", current_price)
        ma20 = data.get("ma20", current_price)
        ma60 = data.get("ma60", current_price)
        
        if current_price == 0:
            return None
        
        # 1. 均线趋势分析
        if ma5 > ma20 > ma60:
            # 多头排列
            trend_strength = min((ma5 - ma60) / ma60 / 0.1, 1.0)
            indicators["bullish_alignment"] = trend_strength * 0.8
            reasoning_parts.append(f"多头排列，趋势强度{trend_strength*100:.0f}%")
        elif ma5 < ma20 < ma60:
            # 空头排列
            trend_strength = min((ma60 - ma5) / ma60 / 0.1, 1.0)
            indicators["bearish_alignment"] = -trend_strength * 0.8
            reasoning_parts.append(f"空头排列，趋势强度{trend_strength*100:.0f}%")
        
        # 2. 价格相对位置
        if current_price > ma5:
            above_ma5 = (current_price - ma5) / ma5
            if above_ma5 > 0.03:
                indicators["strong_uptrend"] = min(above_ma5 / 0.05, 0.7)
                reasoning_parts.append("强势上涨趋势")
            else:
                indicators["uptrend"] = 0.4
                reasoning_parts.append("温和上涨")
        elif current_price < ma5:
            below_ma5 = (ma5 - current_price) / ma5
            if below_ma5 > 0.03:
                indicators["strong_downtrend"] = -min(below_ma5 / 0.05, 0.7)
                reasoning_parts.append("强势下跌趋势")
            else:
                indicators["downtrend"] = -0.4
                reasoning_parts.append("温和下跌")
        
        # 3. 趋势一致性（价格和均线方向）
        price_direction = data.get("price_change_5d", 0)
        ma_direction = (ma5 - ma20) / ma20 if ma20 > 0 else 0
        
        if price_direction > 0 and ma_direction > 0:
            indicators["trend_consistency"] = 0.6
            reasoning_parts.append("价格与均线方向一致")
        elif price_direction < 0 and ma_direction < 0:
            indicators["trend_consistency"] = -0.6
            reasoning_parts.append("下跌趋势确认")
        elif abs(price_direction) < 0.01 and abs(ma_direction) < 0.01:
            indicators["sideways"] = 0.0
            reasoning_parts.append("盘整走势")
        
        if not indicators:
            return None
        
        strength = self._calculate_strength(indicators)
        confidence = self._calculate_confidence(indicators)
        
        avg_indicator = sum(indicators.values()) / len(indicators)
        
        if avg_indicator > 0.5:
            signal_type = SignalType.STRONG_BUY
        elif avg_indicator > 0.2:
            signal_type = SignalType.BUY
        elif avg_indicator < -0.5:
            signal_type = SignalType.STRONG_SELL
        elif avg_indicator < -0.2:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "趋势不明朗"
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "current_price": float(current_price),
                "ma5": float(ma5),
                "ma20": float(ma20),
                "ma60": float(ma60),
                "trend_direction": "up" if avg_indicator > 0 else "down" if avg_indicator < 0 else "sideways",
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )


class SupportResistanceExpert(BaseExpert):
    """支撑阻力专家"""
    
    def __init__(self):
        super().__init__("支撑阻力")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        支撑阻力分析
        
        检测：
        1. 价格相对支撑/阻力位置
        2. 突破/跌破信号
        3. 反弹/回落概率
        """
        indicators = {}
        reasoning_parts = []
        
        current_price = data.get("current_price", 0)
        high_52w = data.get("high_52w", current_price * 1.2)  # 52周最高
        low_52w = data.get("low_52w", current_price * 0.8)    # 52周最低
        ma20 = data.get("ma20", current_price)
        ma60 = data.get("ma60", current_price)
        
        if current_price == 0:
            return None
        
        # 1. 相对52周高低点位置
        price_range = high_52w - low_52w
        if price_range > 0:
            position = (current_price - low_52w) / price_range
            
            if position > 0.9:
                # 接近52周最高
                indicators["near_resistance"] = -0.6
                reasoning_parts.append(f"接近52周最高({position*100:.0f}%位置)")
            elif position < 0.1:
                # 接近52周最低
                indicators["near_support"] = 0.7
                reasoning_parts.append(f"接近52周最低({position*100:.0f}%位置)")
            elif 0.6 < position < 0.8:
                indicators["strong_area"] = 0.3
                reasoning_parts.append("中高位区间")
            elif 0.2 < position < 0.4:
                indicators["value_area"] = 0.4
                reasoning_parts.append("相对低位区间")
        
        # 2. MA20/MA60作为动态支撑阻力
        if ma20 > 0:
            distance_to_ma20 = (current_price - ma20) / ma20
            
            if -0.02 < distance_to_ma20 < 0.02:
                # 在MA20附近
                if current_price > ma20:
                    indicators["ma20_support"] = 0.5
                    reasoning_parts.append("MA20支撑测试")
                else:
                    indicators["ma20_resistance"] = -0.5
                    reasoning_parts.append("MA20压力测试")
            elif distance_to_ma20 > 0.05:
                indicators["above_ma20"] = 0.3
                reasoning_parts.append("站稳MA20上方")
            elif distance_to_ma20 < -0.05:
                indicators["below_ma20"] = -0.3
                reasoning_parts.append("跌破MA20")
        
        # 3. 整数关口（心理价位）
        price_int = int(current_price)
        if price_int % 100 == 0 or price_int % 50 == 0:
            # 整数关口附近
            if current_price >= price_int:
                indicators["round_resistance"] = -0.3
                reasoning_parts.append(f"整数关口{price_int}压力")
            else:
                indicators["round_support"] = 0.3
                reasoning_parts.append(f"整数关口{price_int}支撑")
        
        # 4. 突破信号
        volume = data.get("volume", 0)
        avg_volume = data.get("avg_volume", volume)
        
        if volume > avg_volume * 1.5:
            price_change = data.get("price_change_percent", 0)
            if abs(price_change) > 0.03:
                if price_change > 0:
                    indicators["breakout"] = 0.7
                    reasoning_parts.append("放量突破")
                else:
                    indicators["breakdown"] = -0.7
                    reasoning_parts.append("放量跌破")
        
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
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "无明显支撑阻力信号"
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "current_price": float(current_price),
                "high_52w": float(high_52w),
                "low_52w": float(low_52w),
                "price_position": float(position) if price_range > 0 else 0.5,
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )
