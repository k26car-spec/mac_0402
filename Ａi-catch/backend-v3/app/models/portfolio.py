"""
Portfolio Models
持有股票與交易紀錄模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, Boolean, Numeric, Text, JSON, Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database.base import Base


class TradeStatus(str, enum.Enum):
    """交易狀態"""
    OPEN = "open"           # 持有中
    CLOSED = "closed"       # 已賣出
    STOPPED = "stopped"     # 停損出場
    TARGET_HIT = "target_hit"  # 達標出場


class TradeSource(str, enum.Enum):
    """分析來源"""
    MAIN_FORCE = "main_force"        # 主力偵測
    BIG_ORDER = "big_order"          # 大單分析
    LSTM_PREDICTION = "lstm_prediction"  # LSTM 預測
    EXPERT_SIGNAL = "expert_signal"  # 專家信號
    PREMARKET = "premarket"          # 盤前分析
    MANUAL = "manual"                # 手動操作
    AI_SIMULATION = "ai_simulation"  # AI 模擬


class Portfolio(Base):
    """持有股票紀錄"""
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 進場資訊
    entry_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    entry_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    
    # 分析來源
    analysis_source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    analysis_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # 分析信心度 0-100
    analysis_details: Mapped[Optional[dict]] = mapped_column(JSON)  # 詳細分析數據
    
    # 價格設定
    stop_loss_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # 停損價
    stop_loss_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # 停損金額
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # 目標價
    
    # 當前狀態
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    unrealized_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    unrealized_profit_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    
    # 出場資訊
    exit_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    exit_reason: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 實現損益
    realized_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    realized_profit_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    
    # 狀態
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否為模擬交易
    is_short: Mapped[bool] = mapped_column(Boolean, default=False)     # 是否為做空 (融券)
    
    # 備註
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # 🆕 移動停利追蹤
    highest_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # 持倉期間最高價
    trailing_stop_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # 當前移動停損價
    trailing_activated: Mapped[bool] = mapped_column(Boolean, default=False)  # 移動停利是否已啟動
    trailing_last_update: Mapped[Optional[datetime]] = mapped_column(DateTime)  # 最後更新時間
    
    # 🆕 交易事件追蹤 (用於生成執行報告)
    trade_events: Mapped[Optional[dict]] = mapped_column(JSON)  # 記錄所有交易事件
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Portfolio {self.symbol} - {self.status}>"

    def calculate_profit(self, current_price: Decimal) -> dict:
        """計算損益"""
        if not current_price:
            return {"profit": 0, "percent": 0}
        
        total_cost = self.entry_price * self.entry_quantity
        current_value = current_price * self.entry_quantity
        
        if self.is_short:
            # 做空損益：(進場價 - 目前價) * 數量
            profit = total_cost - current_value
            percent = ((self.entry_price - current_price) / self.entry_price) * 100
        else:
            # 做多損益：(目前價 - 進場價) * 數量
            profit = current_value - total_cost
            percent = ((current_price - self.entry_price) / self.entry_price) * 100
        
        return {
            "profit": float(profit),
            "percent": float(percent)
        }


class TradeRecord(Base):
    """交易歷史紀錄"""
    __tablename__ = "trade_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)  # 關聯持有紀錄
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 交易類型
    trade_type: Mapped[str] = mapped_column(String(10), nullable=False)  # buy/sell
    trade_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # 價格資訊
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # 分析來源
    analysis_source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    analysis_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    analysis_details: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # 損益（賣出時記錄）
    profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    profit_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    
    # 是否為模擬
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 備註
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<TradeRecord {self.trade_type} {self.symbol} @ {self.price}>"


class AnalysisAccuracy(Base):
    """分析準確性紀錄 - 追蹤各分析來源的表現"""
    __tablename__ = "analysis_accuracy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    analysis_source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # 統計期間
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # 交易統計
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    
    # 損益統計
    total_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    
    # 準確率指標
    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # 勝率 %
    avg_profit_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))  # 平均獲利 %
    avg_loss_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))  # 平均損失 %
    profit_factor: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))  # 獲利因子
    risk_reward_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))  # 風險報酬比
    
    # 詳細數據
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<AnalysisAccuracy {self.analysis_source} - {self.win_rate}%>"
