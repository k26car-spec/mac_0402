"""
Expert System Manager
专家系统管理器
"""

from typing import Dict, List, Any, Optional
from .base import BaseExpert, ExpertSignal, ExpertCombiner, TimeFrame
from .mainforce import MainForceExpert, VolumeAnalysisExpert
from .technical import TechnicalIndicatorExpert, MomentumExpert
from .trend import TrendExpert, SupportResistanceExpert
from .advanced import PatternRecognitionExpert, VolatilityExpert, MarketSentimentExpert


class ExpertManager:
    """专家系统管理器"""
    
    def __init__(self):
        self.experts: Dict[str, BaseExpert] = {}
        self._initialize_experts()
    
    def _initialize_experts(self):
        """初始化所有专家"""
        # 注册主力侦测专家
        self.register_expert(MainForceExpert())
        
        # 注册量价分析专家
        self.register_expert(VolumeAnalysisExpert())
        
        # 注册技术指标专家
        self.register_expert(TechnicalIndicatorExpert())
        
        # 注册动量专家
        self.register_expert(MomentumExpert())
        
        # 注册趋势识别专家
        self.register_expert(TrendExpert())
        
        # 注册支撑阻力专家
        self.register_expert(SupportResistanceExpert())
        
        # 注册形态识别专家
        self.register_expert(PatternRecognitionExpert())
        
        # 注册波动率专家
        self.register_expert(VolatilityExpert())
        
        # 注册市场情绪专家
        self.register_expert(MarketSentimentExpert())
    
    def register_expert(self, expert: BaseExpert):
        """注册新专家"""
        self.experts[expert.name] = expert
    
    async def analyze_stock(
        self,
        symbol: str,
        timeframe: TimeFrame,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用所有专家分析股票
        
        Args:
            symbol: 股票代码
            timeframe: 时间框架
            market_data: 市场数据
        
        Returns:
            综合分析结果
        """
        signals: List[ExpertSignal] = []
        
        # 让每个专家进行分析
        for expert_name, expert in self.experts.items():
            try:
                signal = await expert.analyze(symbol, timeframe, market_data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                print(f"专家 {expert_name} 分析出错: {str(e)}")
                continue
        
        # 组合所有信号
        result = ExpertCombiner.combine_signals(signals)
        
        # 添加元数据
        result.update({
            "symbol": symbol,
            "timeframe": timeframe.value,
            "active_experts": len(signals),
            "total_experts": len(self.experts)
        })
        
        return result
    
    async def get_expert_signals(
        self,
        symbol: str,
        timeframe: TimeFrame,
        market_data: Dict[str, Any],
        expert_names: Optional[List[str]] = None
    ) -> List[ExpertSignal]:
        """
        获取指定专家的信号
        
        Args:
            symbol: 股票代码
            timeframe: 时间框架
            market_data: 市场数据
            expert_names: 指定的专家名称列表（None表示所有专家）
        
        Returns:
            专家信号列表
        """
        signals = []
        
        experts_to_use = (
            {name: self.experts[name] for name in expert_names if name in self.experts}
            if expert_names
            else self.experts
        )
        
        for expert_name, expert in experts_to_use.items():
            try:
                signal = await expert.analyze(symbol, timeframe, market_data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                print(f"专家 {expert_name} 分析出错: {str(e)}")
                continue
        
        return signals
    
    def get_expert_list(self) -> List[Dict[str, str]]:
        """获取所有注册的专家列表"""
        return [
            {"name": expert.name, "type": expert.__class__.__name__}
            for expert in self.experts.values()
        ]


# 全局专家管理器实例
expert_manager = ExpertManager()
