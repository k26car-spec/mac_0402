"""
Prediction Models
预测相关的数据模型
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class LSTMPrediction(Base):
    """LSTM 预测结果"""
    __tablename__ = "lstm_predictions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # 预测价格
    predicted_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    predicted_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    predicted_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    
    # 预测信心度
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))  # 0-1
    
    # 模型信息
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    training_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    
    # 实际结果（用于验证）
    actual_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LSTMPrediction {self.symbol} - {self.prediction_date}>"
