"""
大單訊號記錄 Models
Big Order Signal Records Database Model
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.database.base import Base


class BigOrderSignal(Base):
    """大單訊號記錄表"""
    __tablename__ = "big_order_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 訊號基本資訊
    signal_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # 唯一訊號 ID
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # 股票資訊
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 訊號類型
    signal_type: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL
    
    # 價格資訊
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float)
    take_profit: Mapped[Optional[float]] = mapped_column(Float)
    
    # 分數指標
    composite_score: Mapped[float] = mapped_column(Float)  # 綜合分數
    confidence: Mapped[float] = mapped_column(Float)  # 信心度
    quality_score: Mapped[float] = mapped_column(Float)  # 品質分數
    momentum_score: Mapped[Optional[float]] = mapped_column(Float)  # 動能分數
    volume_score: Mapped[Optional[float]] = mapped_column(Float)  # 成交量分數
    pattern_score: Mapped[Optional[float]] = mapped_column(Float)  # 型態分數
    
    # 品質等級
    quality_level: Mapped[str] = mapped_column(String(20))  # 優秀/良好/普通/不佳
    
    # 分析原因
    reason: Mapped[Optional[str]] = mapped_column(Text)
    warnings: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    
    # 額外數據
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB)  # 額外分析數據
    
    # 數據來源
    data_source: Mapped[str] = mapped_column(String(20), default="fubon")  # fubon / yahoo
    
    # 記錄時間
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BigOrderSignal {self.stock_code} {self.signal_type} @ {self.price}>"

    def to_dict(self):
        """轉換為字典"""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "signal_type": self.signal_type,
            "price": self.price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "composite_score": self.composite_score,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "momentum_score": self.momentum_score,
            "volume_score": self.volume_score,
            "pattern_score": self.pattern_score,
            "quality_level": self.quality_level,
            "reason": self.reason,
            "warnings": self.warnings or [],
            "extra_data": self.extra_data,
            "data_source": self.data_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
