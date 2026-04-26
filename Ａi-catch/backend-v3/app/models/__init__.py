"""
Models package
SQLAlchemy ORM Models
"""

from .stock import Stock, StockQuote, OrderBook
from .analysis import ExpertSignal, AnalysisResult, Alert
from .prediction import LSTMPrediction
from .user import User
from .portfolio import Portfolio, TradeRecord, AnalysisAccuracy
from .institutional import (
    InstitutionalTrading,
    BranchTrading,
    MarginTrading,
    FuturesOpenInterest,
    OptionsOpenInterest,
    InstitutionalContinuous,
)
from .ml_signal import TradingSignal, MLModelVersion
from .price_prediction import PricePredictionRecord, ModelAccuracyLog

__all__ = [
    # 股票基礎
    "Stock",
    "StockQuote",
    "OrderBook",
    # 分析相關
    "ExpertSignal",
    "AnalysisResult",
    "Alert",
    "LSTMPrediction",
    # 用戶相關
    "User",
    "Portfolio",
    "TradeRecord",
    "AnalysisAccuracy",
    # 法人籌碼
    "InstitutionalTrading",
    "BranchTrading",
    "MarginTrading",
    "FuturesOpenInterest",
    "OptionsOpenInterest",
    "InstitutionalContinuous",
    # ML 訊號
    "TradingSignal",
    "MLModelVersion",
    # 智能股價預測（自學）
    "PricePredictionRecord",
    "ModelAccuracyLog",
]
