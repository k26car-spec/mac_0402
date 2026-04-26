"""
Stock Models
股票相关的数据模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, Boolean, Numeric, Date, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Stock(Base):
    """股票基本资料"""
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(20), default="TWSE")
    industry: Mapped[Optional[str]] = mapped_column(String(50))
    sector: Mapped[Optional[str]] = mapped_column(String(50))
    listed_date: Mapped[Optional[datetime]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    # 关联
    quotes: Mapped[list["StockQuote"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    order_books: Mapped[list["OrderBook"]] = relationship(back_populates="stock", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stock {self.symbol} - {self.name}>"


class StockQuote(Base):
    """即时报价"""
    __tablename__ = "stock_quotes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    change_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    change_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联
    stock: Mapped["Stock"] = relationship(back_populates="quotes")

    def __repr__(self):
        return f"<StockQuote {self.symbol} @ {self.timestamp}>"


class OrderBook(Base):
    """五档挂单"""
    __tablename__ = "order_books"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # 买盘 (5档)
    bid_price_1: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    bid_volume_1: Mapped[Optional[int]] = mapped_column(BigInteger)
    bid_price_2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    bid_volume_2: Mapped[Optional[int]] = mapped_column(BigInteger)
    bid_price_3: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    bid_volume_3: Mapped[Optional[int]] = mapped_column(BigInteger)
    bid_price_4: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    bid_volume_4: Mapped[Optional[int]] = mapped_column(BigInteger)
    bid_price_5: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    bid_volume_5: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    # 卖盘 (5档)
    ask_price_1: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    ask_volume_1: Mapped[Optional[int]] = mapped_column(BigInteger)
    ask_price_2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    ask_volume_2: Mapped[Optional[int]] = mapped_column(BigInteger)
    ask_price_3: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    ask_volume_3: Mapped[Optional[int]] = mapped_column(BigInteger)
    ask_price_4: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    ask_volume_4: Mapped[Optional[int]] = mapped_column(BigInteger)
    ask_price_5: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    ask_volume_5: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联
    stock: Mapped["Stock"] = relationship(back_populates="order_books")

    def __repr__(self):
        return f"<OrderBook {self.symbol} @ {self.timestamp}>"
