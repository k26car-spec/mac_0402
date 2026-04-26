"""
交易訊號 ML 訓練數據模型
Trading Signal Machine Learning Data Model

用於累積訊號數據，訓練 ML 模型預測成功機率
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float, DateTime, Boolean, JSON, BigInteger, Text

from app.database.base import Base


class TradingSignal(Base):
    """
    交易訊號記錄表 - 用於 ML 訓練
    
    記錄每個訊號的:
    1. 觸發條件 (features)
    2. 後續結果 (outcomes)
    3. 是否成功 (labels for ML)
    """
    __tablename__ = "trading_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # ===== 基本資訊 =====
    signal_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # ENTRY_LONG, EXIT_LONG, etc.
    signal_source: Mapped[str] = mapped_column(String(50))  # day_trading, big_order, orb, etc.
    
    # ===== 觸發時價格 =====
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    
    # ===== ML 特徵 (Features) =====
    # VWAP 相關
    vwap: Mapped[Optional[float]] = mapped_column(Float)
    vwap_deviation: Mapped[Optional[float]] = mapped_column(Float)  # %
    
    # 資金流
    ofi: Mapped[Optional[float]] = mapped_column(Float)  # Order Flow Imbalance
    foreign_net: Mapped[Optional[float]] = mapped_column(Float)  # 外資淨買超
    trust_net: Mapped[Optional[float]] = mapped_column(Float)  # 投信淨買超
    
    # 價格位置
    support_level: Mapped[Optional[float]] = mapped_column(Float)
    resistance_level: Mapped[Optional[float]] = mapped_column(Float)
    distance_to_support: Mapped[Optional[float]] = mapped_column(Float)  # %
    distance_to_resistance: Mapped[Optional[float]] = mapped_column(Float)  # %
    
    # 量價關係
    volume_price_signal: Mapped[Optional[str]] = mapped_column(String(50))  # bullish_confirmation, etc.
    volume_ratio: Mapped[Optional[float]] = mapped_column(Float)  # 相對 5 日均量
    
    # 技術指標
    rsi: Mapped[Optional[float]] = mapped_column(Float)
    macd_signal: Mapped[Optional[str]] = mapped_column(String(20))
    
    # 時間特徵
    hour_of_day: Mapped[int] = mapped_column(Integer)  # 0-23
    minute_of_hour: Mapped[int] = mapped_column(Integer)  # 0-59
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0-6 (Mon-Sun)
    market_phase: Mapped[Optional[str]] = mapped_column(String(30))  # golden_attack, garbage_time, etc.
    
    # 預測信心度
    confidence_score: Mapped[float] = mapped_column(Float)  # 0-100
    
    # 停損停利
    stop_loss: Mapped[Optional[float]] = mapped_column(Float)
    take_profit: Mapped[Optional[float]] = mapped_column(Float)
    
    # ===== 後續追蹤 (Outcomes) =====
    # 5 分鐘後
    price_5min: Mapped[Optional[float]] = mapped_column(Float)
    return_5min: Mapped[Optional[float]] = mapped_column(Float)  # %
    checked_5min: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 30 分鐘後
    price_30min: Mapped[Optional[float]] = mapped_column(Float)
    return_30min: Mapped[Optional[float]] = mapped_column(Float)  # %
    checked_30min: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 收盤價
    price_close: Mapped[Optional[float]] = mapped_column(Float)
    return_close: Mapped[Optional[float]] = mapped_column(Float)  # %
    checked_close: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 最高/最低價 (盤中)
    max_price: Mapped[Optional[float]] = mapped_column(Float)
    min_price: Mapped[Optional[float]] = mapped_column(Float)
    max_profit: Mapped[Optional[float]] = mapped_column(Float)  # % (最大獲利)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float)  # % (最大虧損)
    
    # ===== ML 標籤 (Labels) =====
    # 是否成功 (可以有不同定義)
    is_success_5min: Mapped[Optional[bool]] = mapped_column(Boolean)  # 5 分鐘方向正確
    is_success_30min: Mapped[Optional[bool]] = mapped_column(Boolean)  # 30 分鐘方向正確
    is_success_close: Mapped[Optional[bool]] = mapped_column(Boolean)  # 收盤方向正確
    is_hit_target: Mapped[Optional[bool]] = mapped_column(Boolean)  # 達到目標價
    is_hit_stop: Mapped[Optional[bool]] = mapped_column(Boolean)  # 觸及停損
    
    # 最終結果
    final_return: Mapped[Optional[float]] = mapped_column(Float)  # 實際報酬率 %
    
    # ===== 額外數據 =====
    extra_features: Mapped[Optional[dict]] = mapped_column(JSON)  # 其他特徵
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TradingSignal {self.stock_code} {self.signal_type} @ {self.entry_price}>"

    def to_dict(self):
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "signal_type": self.signal_type,
            "entry_price": self.entry_price,
            "vwap": self.vwap,
            "vwap_deviation": self.vwap_deviation,
            "ofi": self.ofi,
            "confidence_score": self.confidence_score,
            "return_5min": self.return_5min,
            "return_30min": self.return_30min,
            "return_close": self.return_close,
            "is_success_5min": self.is_success_5min,
            "is_success_30min": self.is_success_30min,
            "final_return": self.final_return,
        }
    
    def to_ml_features(self) -> dict:
        """輸出 ML 訓練用特徵向量"""
        return {
            "vwap_deviation": self.vwap_deviation or 0,
            "ofi": self.ofi or 0,
            "foreign_net": self.foreign_net or 0,
            "trust_net": self.trust_net or 0,
            "distance_to_support": self.distance_to_support or 0,
            "distance_to_resistance": self.distance_to_resistance or 0,
            "volume_ratio": self.volume_ratio or 1,
            "rsi": self.rsi or 50,
            "hour_of_day": self.hour_of_day,
            "minute_of_hour": self.minute_of_hour,
            "day_of_week": self.day_of_week,
            "confidence_score": self.confidence_score,
        }


class MLModelVersion(Base):
    """
    ML 模型版本記錄
    追蹤每個模型版本的訓練數據和表現
    """
    __tablename__ = "ml_model_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "signal_predictor_v1"
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # 訓練數據
    training_samples: Mapped[int] = mapped_column(Integer)
    training_start_date: Mapped[datetime] = mapped_column(DateTime)
    training_end_date: Mapped[datetime] = mapped_column(DateTime)
    
    # 模型表現
    accuracy: Mapped[float] = mapped_column(Float)  # 準確率
    precision: Mapped[float] = mapped_column(Float)  # 精確率
    recall: Mapped[float] = mapped_column(Float)  # 召回率
    f1_score: Mapped[float] = mapped_column(Float)
    
    # 回測表現
    backtest_return: Mapped[Optional[float]] = mapped_column(Float)  # %
    backtest_win_rate: Mapped[Optional[float]] = mapped_column(Float)  # %
    backtest_sharpe: Mapped[Optional[float]] = mapped_column(Float)
    
    # 模型檔案
    model_path: Mapped[str] = mapped_column(String(500))  # 模型存放路徑
    
    # 是否啟用
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MLModelVersion {self.model_name} v{self.version} accuracy={self.accuracy:.2%}>"
