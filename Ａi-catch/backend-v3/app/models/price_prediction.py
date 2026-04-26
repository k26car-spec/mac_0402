"""
股價預測與自學 DB 模型
Price Prediction Self-Learning Database Models

記錄每次 LSTM 預測結果、實際結果、準確率、關鍵特徵
讓系統能從成功/失敗中自動學習改進
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, DateTime, Date,
    Numeric, Boolean, Text, Index, UniqueConstraint, Float
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PricePredictionRecord(Base):
    """
    股價預測記錄表（核心自學表）
    每次預測都會存一筆，收盤後自動驗證並更新 actual_* 欄位
    """
    __tablename__ = "price_prediction_records"
    __table_args__ = (
        UniqueConstraint('symbol', 'prediction_date', 'target_date',
                         name='uq_prediction_symbol_dates'),
        Index('ix_pred_symbol', 'symbol'),
        Index('ix_pred_date', 'prediction_date'),
        Index('ix_pred_target_date', 'target_date'),
        Index('ix_pred_verified', 'is_verified'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)

    # 基本資訊
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False, comment="預測發出日期")
    target_date: Mapped[date] = mapped_column(Date, nullable=False, comment="預測目標日期（幾日後）")
    horizon_days: Mapped[int] = mapped_column(Integer, default=2, comment="預測天數 2/5")

    # 預測值
    price_at_prediction: Mapped[Decimal] = mapped_column(Numeric(10, 2), comment="預測時的當前股價")
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), comment="預測目標價格")
    predicted_change_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3), comment="預測漲跌幅%")
    predicted_direction: Mapped[str] = mapped_column(String(10), comment="up/down/neutral")
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), comment="模型信心度 0-100")

    # 預測區間（樂觀/悲觀）
    predicted_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="樂觀預測上界")
    predicted_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="悲觀預測下界")

    # 使用的特徵（存為字串，逗號分隔）
    features_used: Mapped[Optional[str]] = mapped_column(Text, comment="使用的特徵清單 JSON")
    model_version: Mapped[Optional[str]] = mapped_column(String(50), comment="使用的模型版本")

    # ===== 實際結果（收盤後驗證填入）=====
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已驗證")
    actual_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="實際收盤價")
    actual_change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), comment="實際漲跌幅%")
    actual_direction: Mapped[Optional[str]] = mapped_column(String(10), comment="實際方向 up/down/neutral")

    # ===== 準確率評分 =====
    direction_correct: Mapped[Optional[bool]] = mapped_column(Boolean, comment="方向是否正確")
    price_error_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), comment="價格誤差%")
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="綜合準確率分數 0-100")

    # ===== 自學關鍵特徵記錄 =====
    # 預測時的關鍵指標快照（用於事後分析哪些特徵有效）
    rsi_at_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    macd_at_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    vix_at_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    institutional_net_at_prediction: Mapped[Optional[int]] = mapped_column(BigInteger, comment="法人買賣超張數")
    volume_ratio_at_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    ma5_deviation_at_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), comment="偏離MA5%")
    market_change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), comment="大盤當日漲跌%")

    # 失敗原因分析（方向預測錯誤時記錄）
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, comment="失敗原因分析")
    success_pattern: Mapped[Optional[str]] = mapped_column(Text, comment="成功模式記錄")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self):
        return f"<PricePrediction {self.symbol} {self.prediction_date}→{self.target_date} {self.predicted_direction}>"


class ModelAccuracyLog(Base):
    """
    模型準確率歷史記錄
    每週計算一次累積準確率，追蹤改進趨勢
    """
    __tablename__ = "model_accuracy_log"
    __table_args__ = (
        Index('ix_accuracy_symbol', 'symbol'),
        Index('ix_accuracy_date', 'log_date'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, comment="預測天數")

    # 統計窗口
    window_days: Mapped[int] = mapped_column(Integer, default=14, comment="統計窗口天數")
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    correct_directions: Mapped[int] = mapped_column(Integer, default=0)

    # 準確率指標
    direction_accuracy: Mapped[Decimal] = mapped_column(Numeric(5, 2), comment="方向準確率%")
    avg_price_error_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), comment="平均價格誤差%")

    # 特徵有效性分析（成功案例最常見特徵）
    top_success_features: Mapped[Optional[str]] = mapped_column(Text, comment="成功關鍵特徵 JSON")
    top_failure_patterns: Mapped[Optional[str]] = mapped_column(Text, comment="失敗模式 JSON")

    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ModelAccuracyLog {self.symbol} {self.log_date} acc={self.direction_accuracy}%>"
