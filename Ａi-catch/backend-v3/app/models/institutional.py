"""
Institutional Trading Models
法人籌碼相關數據模型

包含:
1. 三大法人買賣超 (InstitutionalTrading)
2. 券商分點買賣超 (BranchTrading)
3. 融資融券餘額 (MarginTrading)
4. 期貨未平倉 (FuturesOpenInterest)
5. 選擇權未平倉 (OptionsOpenInterest)
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, DateTime, Boolean, 
    Numeric, Date, Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InstitutionalTrading(Base):
    """
    三大法人買賣超日報
    資料來源: 台灣證交所 T86 表
    """
    __tablename__ = "institutional_trading"
    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_institutional_date_symbol'),
        Index('ix_institutional_date', 'trade_date'),
        Index('ix_institutional_symbol', 'symbol'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 外資 (Foreign Investors)
    foreign_buy: Mapped[int] = mapped_column(BigInteger, default=0, comment="外資買進(張)")
    foreign_sell: Mapped[int] = mapped_column(BigInteger, default=0, comment="外資賣出(張)")
    foreign_net: Mapped[int] = mapped_column(BigInteger, default=0, comment="外資買賣超(張)")
    foreign_buy_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="外資買進金額(元)")
    foreign_sell_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="外資賣出金額(元)")
    
    # 投信 (Investment Trust)
    investment_buy: Mapped[int] = mapped_column(BigInteger, default=0, comment="投信買進(張)")
    investment_sell: Mapped[int] = mapped_column(BigInteger, default=0, comment="投信賣出(張)")
    investment_net: Mapped[int] = mapped_column(BigInteger, default=0, comment="投信買賣超(張)")
    investment_buy_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="投信買進金額(元)")
    investment_sell_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="投信賣出金額(元)")
    
    # 自營商 (Dealers)
    dealer_buy: Mapped[int] = mapped_column(BigInteger, default=0, comment="自營商買進(張)")
    dealer_sell: Mapped[int] = mapped_column(BigInteger, default=0, comment="自營商賣出(張)")
    dealer_net: Mapped[int] = mapped_column(BigInteger, default=0, comment="自營商買賣超(張)")
    dealer_buy_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="自營商買進金額(元)")
    dealer_sell_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="自營商賣出金額(元)")
    
    # 合計
    total_net: Mapped[int] = mapped_column(BigInteger, default=0, comment="三大法人合計買賣超(張)")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<InstitutionalTrading {self.symbol} @ {self.trade_date}>"


class BranchTrading(Base):
    """
    券商分點買賣超
    資料來源: 富邦網站、Goodinfo 等
    """
    __tablename__ = "branch_trading"
    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', 'branch_code', name='uq_branch_date_symbol_branch'),
        Index('ix_branch_date', 'trade_date'),
        Index('ix_branch_symbol', 'symbol'),
        Index('ix_branch_code', 'branch_code'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 券商分點資訊
    broker_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="券商代碼")
    broker_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="券商名稱")
    branch_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="分點代碼")
    branch_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="分點名稱")
    
    # 買賣數據
    buy_shares: Mapped[int] = mapped_column(BigInteger, default=0, comment="買進張數")
    sell_shares: Mapped[int] = mapped_column(BigInteger, default=0, comment="賣出張數")
    net_shares: Mapped[int] = mapped_column(BigInteger, default=0, comment="買賣超張數")
    buy_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="買進金額")
    sell_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="賣出金額")
    net_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="買賣超金額")
    
    # 均價
    avg_buy_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="買進均價")
    avg_sell_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="賣出均價")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BranchTrading {self.symbol} - {self.branch_name} @ {self.trade_date}>"


class MarginTrading(Base):
    """
    融資融券餘額
    資料來源: 證交所公開資料
    """
    __tablename__ = "margin_trading"
    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_margin_date_symbol'),
        Index('ix_margin_date', 'trade_date'),
        Index('ix_margin_symbol', 'symbol'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 融資 (Margin Purchase)
    margin_buy: Mapped[int] = mapped_column(BigInteger, default=0, comment="融資買進(張)")
    margin_sell: Mapped[int] = mapped_column(BigInteger, default=0, comment="融資賣出(張)")
    margin_cash_repay: Mapped[int] = mapped_column(BigInteger, default=0, comment="現金償還(張)")
    margin_balance: Mapped[int] = mapped_column(BigInteger, default=0, comment="融資餘額(張)")
    margin_balance_prev: Mapped[int] = mapped_column(BigInteger, default=0, comment="前日融資餘額(張)")
    margin_change: Mapped[int] = mapped_column(BigInteger, default=0, comment="融資增減(張)")
    margin_limit: Mapped[Optional[int]] = mapped_column(BigInteger, comment="融資限額(張)")
    margin_utilization: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="融資使用率(%)")
    
    # 融券 (Short Selling)
    short_sell: Mapped[int] = mapped_column(BigInteger, default=0, comment="融券賣出(張)")
    short_buy: Mapped[int] = mapped_column(BigInteger, default=0, comment="融券買進(張)")
    short_stock_repay: Mapped[int] = mapped_column(BigInteger, default=0, comment="現券償還(張)")
    short_balance: Mapped[int] = mapped_column(BigInteger, default=0, comment="融券餘額(張)")
    short_balance_prev: Mapped[int] = mapped_column(BigInteger, default=0, comment="前日融券餘額(張)")
    short_change: Mapped[int] = mapped_column(BigInteger, default=0, comment="融券增減(張)")
    short_limit: Mapped[Optional[int]] = mapped_column(BigInteger, comment="融券限額(張)")
    short_utilization: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="融券使用率(%)")
    
    # 資券比 (Margin/Short Ratio)
    margin_short_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="資券比(%)")
    
    # 當沖相關
    day_trade_volume: Mapped[Optional[int]] = mapped_column(BigInteger, comment="當沖張數")
    day_trade_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="當沖比率(%)")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MarginTrading {self.symbol} @ {self.trade_date}>"


class FuturesOpenInterest(Base):
    """
    期貨未平倉部位
    資料來源: 台灣期貨交易所 (TAIFEX)
    """
    __tablename__ = "futures_open_interest"
    __table_args__ = (
        UniqueConstraint('trade_date', 'contract_code', 'identity_type', name='uq_futures_date_contract_identity'),
        Index('ix_futures_date', 'trade_date'),
        Index('ix_futures_contract', 'contract_code'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # 契約資訊
    contract_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="契約代碼 (TX=台指期)")
    contract_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="契約名稱")
    contract_month: Mapped[Optional[str]] = mapped_column(String(10), comment="到期月份")
    
    # 身份別 (foreign=外資, investment=投信, dealer=自營商)
    identity_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="身份類別")
    
    # 多單部位
    long_position: Mapped[int] = mapped_column(BigInteger, default=0, comment="多單口數")
    long_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="多單金額")
    
    # 空單部位
    short_position: Mapped[int] = mapped_column(BigInteger, default=0, comment="空單口數")
    short_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="空單金額")
    
    # 淨部位
    net_position: Mapped[int] = mapped_column(BigInteger, default=0, comment="淨多單口數(多-空)")
    net_position_change: Mapped[int] = mapped_column(BigInteger, default=0, comment="淨部位增減")
    
    # 未平倉合計
    total_oi: Mapped[int] = mapped_column(BigInteger, default=0, comment="未平倉總口數")
    total_oi_change: Mapped[int] = mapped_column(BigInteger, default=0, comment="未平倉增減")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FuturesOpenInterest {self.contract_code} {self.identity_type} @ {self.trade_date}>"


class OptionsOpenInterest(Base):
    """
    選擇權未平倉部位
    資料來源: 台灣期貨交易所 (TAIFEX)
    """
    __tablename__ = "options_open_interest"
    __table_args__ = (
        UniqueConstraint('trade_date', 'contract_code', 'option_type', 'identity_type', 
                        name='uq_options_date_contract_type_identity'),
        Index('ix_options_date', 'trade_date'),
        Index('ix_options_contract', 'contract_code'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # 契約資訊
    contract_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="契約代碼 (TXO=台指選)")
    contract_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="契約名稱")
    contract_month: Mapped[Optional[str]] = mapped_column(String(10), comment="到期月份")
    
    # 選擇權類型 (call=買權, put=賣權)
    option_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="選擇權類型")
    
    # 身份別
    identity_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="身份類別")
    
    # 買方部位
    buy_position: Mapped[int] = mapped_column(BigInteger, default=0, comment="買方口數")
    buy_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="買方金額")
    
    # 賣方部位
    sell_position: Mapped[int] = mapped_column(BigInteger, default=0, comment="賣方口數")
    sell_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), comment="賣方金額")
    
    # 淨部位
    net_position: Mapped[int] = mapped_column(BigInteger, default=0, comment="淨口數(買-賣)")
    net_position_change: Mapped[int] = mapped_column(BigInteger, default=0, comment="淨部位增減")
    
    # 未平倉合計
    total_oi: Mapped[int] = mapped_column(BigInteger, default=0, comment="未平倉總口數")
    total_oi_change: Mapped[int] = mapped_column(BigInteger, default=0, comment="未平倉增減")
    
    # P/C Ratio 相關
    put_call_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="賣權/買權比")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<OptionsOpenInterest {self.contract_code} {self.option_type} {self.identity_type} @ {self.trade_date}>"


class InstitutionalContinuous(Base):
    """
    法人連續買賣超統計 (計算結果表)
    用於加速 API 響應
    """
    __tablename__ = "institutional_continuous"
    __table_args__ = (
        UniqueConstraint('calc_date', 'symbol', name='uq_continuous_date_symbol'),
        Index('ix_continuous_date', 'calc_date'),
        Index('ix_continuous_symbol', 'symbol'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    calc_date: Mapped[date] = mapped_column(Date, nullable=False, comment="計算日期")
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 外資連續性
    foreign_direction: Mapped[Optional[str]] = mapped_column(String(10), comment="外資方向(buy/sell)")
    foreign_continuous_days: Mapped[int] = mapped_column(Integer, default=0, comment="外資連續天數")
    foreign_continuous_shares: Mapped[int] = mapped_column(BigInteger, default=0, comment="外資連續累計張數")
    
    # 投信連續性
    investment_direction: Mapped[Optional[str]] = mapped_column(String(10), comment="投信方向(buy/sell)")
    investment_continuous_days: Mapped[int] = mapped_column(Integer, default=0, comment="投信連續天數")
    investment_continuous_shares: Mapped[int] = mapped_column(BigInteger, default=0, comment="投信連續累計張數")
    
    # 自營商連續性
    dealer_direction: Mapped[Optional[str]] = mapped_column(String(10), comment="自營商方向(buy/sell)")
    dealer_continuous_days: Mapped[int] = mapped_column(Integer, default=0, comment="自營商連續天數")
    dealer_continuous_shares: Mapped[int] = mapped_column(BigInteger, default=0, comment="自營商連續累計張數")
    
    # 籌碼集中度分數
    chip_concentration_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="籌碼集中度分數(0-100)")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<InstitutionalContinuous {self.symbol} @ {self.calc_date}>"
