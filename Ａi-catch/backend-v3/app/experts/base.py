"""
Expert System Base Class
专家系统基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class TimeFrame(Enum):
    """时间框架"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class ExpertSignal:
    """专家信号"""
    
    def __init__(
        self,
        expert_name: str,
        signal_type: SignalType,
        strength: float,  # 0-1
        confidence: float,  # 0-1
        timeframe: TimeFrame,
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.expert_name = expert_name
        self.signal_type = signal_type
        self.strength = max(0.0, min(1.0, strength))
        self.confidence = max(0.0, min(1.0, confidence))
        self.timeframe = timeframe
        self.reasoning = reasoning
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "expert_name": self.expert_name,
            "signal_type": self.signal_type.value,
            "strength": self.strength,
            "confidence": self.confidence,
            "timeframe": self.timeframe.value,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class BaseExpert(ABC):
    """专家系统基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def analyze(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: Dict[str, Any]
    ) -> Optional[ExpertSignal]:
        """
        分析股票并产生信号
        
        Args:
            symbol: 股票代码
            timeframe: 时间框架
            data: 市场数据（包含价格、成交量等）
        
        Returns:
            ExpertSignal 或 None（如果无信号）
        """
        pass
    
    def _calculate_strength(self, indicators: Dict[str, float]) -> float:
        """
        根据指标计算信号强度
        
        Override this method for custom strength calculation
        """
        # 默认实现：平均值
        if not indicators:
            return 0.5
        return sum(indicators.values()) / len(indicators)
    
    def _calculate_confidence(self, indicators: Dict[str, float]) -> float:
        """
        根据指标计算置信度
        
        Override this method for custom confidence calculation
        """
        if not indicators:
            return 0.5
        
        # 计算指标的一致性（标准差的倒数）
        values = list(indicators.values())
        if len(values) == 1:
            return 0.8
        
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # 标准差越小，一致性越高，置信度越高
        consistency = 1.0 - min(std_dev, 1.0)
        return max(0.3, min(0.95, consistency))


class ExpertCombiner:
    """专家信号组合器"""
    
    @staticmethod
    def combine_signals(signals: List[ExpertSignal]) -> Dict[str, Any]:
        """
        组合多个专家信号
        
        Args:
            signals: 专家信号列表
        
        Returns:
            组合后的分析结果
        """
        if not signals:
            return {
                "overall_signal": SignalType.HOLD.value,
                "overall_strength": 0.0,
                "overall_confidence": 0.0,
                "expert_count": 0,
                "signals": []
            }
        
        # 加权投票
        signal_weights = {
            SignalType.STRONG_BUY: 2.0,
            SignalType.BUY: 1.0,
            SignalType.HOLD: 0.0,
            SignalType.SELL: -1.0,
            SignalType.STRONG_SELL: -2.0
        }
        
        total_weight = 0.0
        total_confidence = 0.0
        
        for signal in signals:
            weight = signal_weights[signal.signal_type] * signal.strength * signal.confidence
            total_weight += weight
            total_confidence += signal.confidence
        
        avg_confidence = total_confidence / len(signals)
        
        # 确定整体信号
        if total_weight > 1.5:
            overall_signal = SignalType.STRONG_BUY
        elif total_weight > 0.5:
            overall_signal = SignalType.BUY
        elif total_weight < -1.5:
            overall_signal = SignalType.STRONG_SELL
        elif total_weight < -0.5:
            overall_signal = SignalType.SELL
        else:
            overall_signal = SignalType.HOLD
        
        return {
            "overall_signal": overall_signal.value,
            "overall_strength": abs(total_weight) / len(signals),
            "overall_confidence": avg_confidence,
            "expert_count": len(signals),
            "signals": [s.to_dict() for s in signals],
            "consensus": {
                "buy_count": sum(1 for s in signals if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]),
                "sell_count": sum(1 for s in signals if s.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]),
                "hold_count": sum(1 for s in signals if s.signal_type == SignalType.HOLD)
            }
        }
