"""
Technical Indicators Expert
技术指标专家
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal

from .base import BaseExpert, ExpertSignal, SignalType, TimeFrame


class TechnicalIndicatorExpert(BaseExpert):
    """技术指标专家 - MA, RSI, MACD"""
    
    def __init__(self):
        super().__init__("技术指标")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        技术指标综合分析
        
        指标：
        1. MA (移动平均线)
        2. RSI (相对强弱指标)
        3. MACD (指数平滑异同移动平均线)
        """
        indicators = {}
        reasoning_parts = []
        
        # 1. MA分析
        current_price = data.get("current_price", 0)
        ma5 = data.get("ma5", current_price)
        ma20 = data.get("ma20", current_price)
        ma60 = data.get("ma60", current_price)
        
        if current_price > 0:
            # 金叉/死叉
            if ma5 > ma20 > ma60:
                indicators["ma_golden_cross"] = 0.8
                reasoning_parts.append("均线多头排列")
            elif ma5 < ma20 < ma60:
                indicators["ma_death_cross"] = -0.8
                reasoning_parts.append("均线空头排列")
            
            # 价格位置
            if current_price > ma20:
                price_above_ma = min((current_price - ma20) / ma20 / 0.05, 1.0)
                indicators["price_above_ma"] = price_above_ma
                reasoning_parts.append(f"价格在MA20上方{((current_price - ma20) / ma20 * 100):.1f}%")
            elif current_price < ma20:
                price_below_ma = max((current_price - ma20) / ma20 / 0.05, -1.0)
                indicators["price_below_ma"] = price_below_ma
                reasoning_parts.append(f"价格在MA20下方{abs((current_price - ma20) / ma20 * 100):.1f}%")
        
        # 2. RSI分析
        rsi = data.get("rsi", 50)
        
        if rsi < 30:
            indicators["rsi_oversold"] = 0.7
            reasoning_parts.append(f"RSI超卖({rsi:.0f})")
        elif rsi > 70:
            indicators["rsi_overbought"] = -0.7
            reasoning_parts.append(f"RSI超买({rsi:.0f})")
        elif rsi > 50:
            indicators["rsi_bullish"] = (rsi - 50) / 50 * 0.5
            reasoning_parts.append(f"RSI偏多({rsi:.0f})")
        elif rsi < 50:
            indicators["rsi_bearish"] = (rsi - 50) / 50 * 0.5
            reasoning_parts.append(f"RSI偏空({rsi:.0f})")
        
        # 3. MACD分析
        macd_value = data.get("macd", 0)
        macd_signal = data.get("macd_signal", 0)
        macd_hist = data.get("macd_histogram", 0)
        
        if macd_value > macd_signal and macd_hist > 0:
            indicators["macd_bullish"] = min(abs(macd_hist) / 10, 0.8)
            reasoning_parts.append("MACD金叉")
        elif macd_value < macd_signal and macd_hist < 0:
            indicators["macd_bearish"] = -min(abs(macd_hist) / 10, 0.8)
            reasoning_parts.append("MACD死叉")
        
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
        
        reasoning = "技术面" + ("看多" if avg_indicator > 0 else "看空") + "。" + "；".join(reasoning_parts)
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "ma5": float(ma5),
                "ma20": float(ma20),
                "ma60": float(ma60),
                "rsi": float(rsi),
                "macd": float(macd_value),
                "macd_signal": float(macd_signal),
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )


class MomentumExpert(BaseExpert):
    """动量专家"""
    
    def __init__(self):
        super().__init__("动量分析")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        动量分析
        
        检测：
        1. 价格动量
        2. 成交量动量
        3. 加速/减速
        """
        indicators = {}
        reasoning_parts = []
        
        # 价格动量
        price_change_1d = data.get("price_change_1d", 0)
        price_change_5d = data.get("price_change_5d", 0)
        
        if abs(price_change_1d) > 0.03:
            momentum_strength = min(abs(price_change_1d) / 0.05, 1.0)
            if price_change_1d > 0:
                indicators["price_momentum"] = momentum_strength
                reasoning_parts.append(f"价格强势上涨{price_change_1d*100:.1f}%")
            else:
                indicators["price_momentum"] = -momentum_strength
                reasoning_parts.append(f"价格快速下跌{abs(price_change_1d)*100:.1f}%")
        
        # 动量加速
        if abs(price_change_1d) > abs(price_change_5d) / 5:
            indicators["accelerating"] = 0.6 if price_change_1d > 0 else -0.6
            reasoning_parts.append("动量加速")
        elif abs(price_change_1d) < abs(price_change_5d) / 5:
            indicators["decelerating"] = -0.3 if price_change_1d > 0 else 0.3
            reasoning_parts.append("动量减速")
        
        # 成交量动量
        volume_change = data.get("volume_change", 0)
        if abs(volume_change) > 0.5:
            vol_momentum = min(abs(volume_change), 1.0)
            if volume_change > 0:
                indicators["volume_momentum"] = vol_momentum * 0.5
                reasoning_parts.append(f"量能增加{volume_change*100:.0f}%")
            else:
                indicators["volume_momentum"] = vol_momentum * -0.3
                reasoning_parts.append(f"量能萎缩") 
        
        if not indicators:
            return None
        
        strength = self._calculate_strength(indicators)
        confidence = self._calculate_confidence(indicators)
        
        avg_indicator = sum(indicators.values()) / len(indicators)
        
        if avg_indicator > 0.5:
            signal_type = SignalType.BUY
        elif avg_indicator > 0:
            signal_type = SignalType.HOLD
        elif avg_indicator > -0.5:
            signal_type = SignalType.HOLD
        else:
            signal_type = SignalType.SELL
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "动量中性"
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "price_change_1d": float(price_change_1d),
                "price_change_5d": float(price_change_5d),
                "volume_change": float(volume_change),
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )
