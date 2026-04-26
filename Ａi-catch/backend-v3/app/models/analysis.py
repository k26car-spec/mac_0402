"""
Analysis Models
分析相关的数据模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, Boolean, Numeric, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ExpertSignal(Base):
    """专家信号"""
    __tablename__ = "expert_signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    expert_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # buy/sell/hold
    strength: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)  # 0-1
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)  # 0-1
    timeframe: Mapped[Optional[str]] = mapped_column(String(10))  # 1m/5m/15m/1h/1d
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ExpertSignal {self.expert_name} - {self.symbol}: {self.signal_type}>"


class AnalysisResult(Base):
    """分析结果"""
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[Optional[str]] = mapped_column(String(10))
    
    # 主力侦测结果
    mainforce_action: Mapped[Optional[str]] = mapped_column(String(20))  # entry/exit/consolidation
    mainforce_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    
    # 综合评分
    overall_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))  # 0-1
    recommendation: Mapped[Optional[str]] = mapped_column(String(20))  # strong_buy/buy/hold/sell/strong_sell
    
    # 风险评估
    risk_level: Mapped[Optional[str]] = mapped_column(String(20))  # low/medium/high
    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    
    # 详细数据
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    expert_summary: Mapped[Optional[dict]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AnalysisResult {self.symbol} - {self.analysis_type}>"


class Alert(Base):
    """警报"""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # low/medium/high/critical
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(50))
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active/acknowledged/resolved
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # 额外数据
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Alert {self.symbol} - {self.alert_type} [{self.severity}]>"
