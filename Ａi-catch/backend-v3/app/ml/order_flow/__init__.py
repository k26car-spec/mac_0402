"""
訂單流模式識別系統
Order Flow Pattern Recognition System

替代傳統 LSTM 價格預測，專注於市場微觀模式識別

主要模組：
- patterns: 定義6種核心市場微觀模式
- features: 訂單流特徵工程
- dataset: 訓練資料集構建
- labeler: 模式標註器
"""

from .patterns import (
    MarketPattern,
    MARKET_MICRO_PATTERNS,
    PatternThresholds
)

from .features import OrderFlowFeatureExtractor
from .labeler import PatternLabeler
from .dataset import OrderFlowDataset

__all__ = [
    'MarketPattern',
    'MARKET_MICRO_PATTERNS',
    'PatternThresholds',
    'OrderFlowFeatureExtractor',
    'PatternLabeler',
    'OrderFlowDataset',
]

__version__ = "1.0.0"
