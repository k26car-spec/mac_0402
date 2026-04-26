"""
Main Force Detection Expert
主力侦测专家
"""

from typing import Dict, Any, Optional
from decimal import Decimal

from .base import BaseExpert, ExpertSignal, SignalType, TimeFrame


class MainForceExpert(BaseExpert):
    """主力侦测专家 - 检测主力进出场"""
    
    def __init__(self):
        super().__init__("主力侦测")
        
        # 阈值配置
        self.volume_surge_threshold = 2.0  # 成交量激增倍数
        self.large_order_threshold = 1000  # 大单张数阈值
        self.price_impact_threshold = 0.02  # 价格影响阈值（2%）
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        分析主力动向
        
        检测指标：
        1. 成交量异常
        2. 大单比例
        3. 价格波动
        4. 买卖压力
        """
        # 提取数据
        current_volume = data.get("volume", 0)
        avg_volume = data.get("avg_volume", current_volume)
        large_buy_orders = data.get("large_buy_orders", 0)
        large_sell_orders = data.get("large_sell_orders", 0)
        price_change = data.get("price_change_percent", 0.0)
        
        # 分析指标
        indicators = {}
        reasoning_parts = []
        
        # 1. 成交量分析
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        if volume_ratio > self.volume_surge_threshold:
            indicators["volume_surge"] = min(volume_ratio / 3.0, 1.0)
            reasoning_parts.append(f"成交量激增{volume_ratio:.1f}倍")
        elif volume_ratio < 0.5:
            indicators["volume_surge"] = -0.3
            reasoning_parts.append("成交量萎缩")
        
        # 2. 大单分析
        total_large_orders = large_buy_orders + large_sell_orders
        if total_large_orders > self.large_order_threshold:
            buy_ratio = large_buy_orders / total_large_orders if total_large_orders > 0 else 0.5
            
            if buy_ratio > 0.6:
                indicators["large_orders"] = buy_ratio
                reasoning_parts.append(f"主力买盘强劲({buy_ratio*100:.0f}%)")
            elif buy_ratio < 0.4:
                indicators["large_orders"] = -(1 - buy_ratio)
                reasoning_parts.append(f"主力卖盘压力({(1-buy_ratio)*100:.0f}%)")
        
        # 3. 价格动能分析
        if abs(price_change) > self.price_impact_threshold:
            price_indicator = min(abs(price_change) / 0.05, 1.0)
            if price_change > 0:
                indicators["price_momentum"] = price_indicator
                reasoning_parts.append(f"价格上涨{price_change*100:.1f}%")
            else:
                indicators["price_momentum"] = -price_indicator
                reasoning_parts.append(f"价格下跌{abs(price_change)*100:.1f}%")
        
        # 4. 买卖压力比
        bid_volume = data.get("bid_volume", 0)
        ask_volume = data.get("ask_volume", 0)
        total_depth = bid_volume + ask_volume
        
        if total_depth > 0:
            bid_ratio = bid_volume / total_depth
            if bid_ratio > 0.6:
                indicators["bid_pressure"] = bid_ratio
                reasoning_parts.append(f"买盘压力大({bid_ratio*100:.0f}%)")
            elif bid_ratio < 0.4:
                indicators["bid_pressure"] = -(1 - bid_ratio)
                reasoning_parts.append(f"卖盘压力大({(1-bid_ratio)*100:.0f}%)")
        
        # 如果没有明显信号，返回 None
        if not indicators:
            return None
        
        # 计算综合强度和置信度
        strength = self._calculate_strength(indicators)
        confidence = self._calculate_confidence(indicators)
        
        # 确定信号类型
        avg_indicator = sum(indicators.values()) / len(indicators)
        
        if avg_indicator > 0.6:
            signal_type = SignalType.STRONG_BUY
        elif avg_indicator > 0.3:
            signal_type = SignalType.BUY
        elif avg_indicator < -0.6:
            signal_type = SignalType.STRONG_SELL
        elif avg_indicator < -0.3:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        # 构建推理说明
        reasoning = f"主力{'进场' if avg_indicator > 0 else '出场'}信号。" + "；".join(reasoning_parts)
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "volume_ratio": float(volume_ratio),
                "large_buy_orders": large_buy_orders,
                "large_sell_orders": large_sell_orders,
                "price_change": float(price_change),
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )


class VolumeAnalysisExpert(BaseExpert):
    """量价分析专家"""
    
    def __init__(self):
        super().__init__("量价分析")
    
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        量价分析
        
        检测：
        1. 量价配合
        2. 价涨量增/价跌量减
        3. 背离信号
        """
        price_change = data.get("price_change_percent", 0.0)
        current_volume = data.get("volume", 0)
        avg_volume = data.get("avg_volume", current_volume)
        
        if avg_volume == 0:
            return None
        
        volume_change = (current_volume - avg_volume) / avg_volume
        
        indicators = {}
        reasoning_parts = []
        
        # 量价配合分析
        if price_change > 0.01 and volume_change > 0.2:
            # 价涨量增 - 买入信号
            indicators["volume_price_match"] = min((price_change + volume_change) / 2, 1.0)
            reasoning_parts.append("价涨量增，趋势健康")
        elif price_change < -0.01 and volume_change > 0.2:
            # 价跌量增 - 可能见底
            indicators["volume_price_divergence"] = 0.6
            reasoning_parts.append("价跌量增，可能见底")
        elif price_change > 0.01 and volume_change < -0.2:
            # 价涨量缩 - 警告信号
            indicators["volume_price_mismatch"] = -0.5
            reasoning_parts.append("价涨量缩，上涨乏力")
        elif price_change < -0.01 and volume_change < -0.2:
            # 价跌量缩 - 可能见底
            indicators["volume_decrease"] = 0.4
            reasoning_parts.append("价跌量缩，卖压减轻")
        
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
        
        reasoning = "；".join(reasoning_parts)
        
        return ExpertSignal(
            expert_name=self.name,
            signal_type=signal_type,
            strength=abs(strength),
            confidence=confidence,
            timeframe=timeframe,
            reasoning=reasoning,
            metadata={
                "price_change": float(price_change),
                "volume_change": float(volume_change),
                "indicators": {k: float(v) for k, v in indicators.items()}
            }
        )
