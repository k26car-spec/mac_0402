"""
開盤前精準選股系統 - 資料庫模型
Pre-Market Stock Selection Database Models
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base


class PreMarketAnalysis(Base):
    """開盤前分析主表"""
    __tablename__ = "premarket_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_date = Column(DateTime, default=datetime.now, index=True)
    phase = Column(String(50))  # 'overnight', 'morning', 'final'
    
    # 市場整體預測
    market_sentiment = Column(String(20))  # 'bullish', 'bearish', 'neutral'
    opening_direction = Column(String(50))  # '強勢開高', '平開', '開低'
    risk_level = Column(String(20))  # 'low', 'medium', 'high'
    
    # JSON數據
    us_market_data = Column(JSON)  # 美股數據
    asia_market_data = Column(JSON)  # 亞股數據
    news_summary = Column(JSON)  # 新聞摘要
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 關聯
    selections = relationship("FinalSelection", back_populates="analysis")


class USMarketImpact(Base):
    """美股影響分析"""
    __tablename__ = "us_market_impact"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.now, index=True)
    
    # 三大指數
    nasdaq_change = Column(Float)
    dow_jones_change = Column(Float)
    sp500_change = Column(Float)
    
    # 關鍵個股
    nvidia_change = Column(Float)
    apple_change = Column(Float)
    amd_change = Column(Float)
    tesla_change = Column(Float)
    
    # 市場指標
    vix_level = Column(Float)
    fear_greed_index = Column(Integer)
    
    # 期貨
    taiwan_futures_change = Column(Float)
    nikkei_futures_change = Column(Float)
    
    # 影響評估
    impact_level = Column(String(20))  # 'high', 'medium', 'low'
    sentiment = Column(String(20))
    
    # 受影響的台股類股
    affected_sectors = Column(JSON)
    hot_stocks = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.now)


class InstitutionalFlow(Base):
    """法人籌碼流向"""
    __tablename__ = "institutional_flow"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.now, index=True)
    stock_id = Column(String(10), index=True)
    stock_name = Column(String(50))
    
    # 三大法人買賣超（張）
    foreign_net_buy = Column(Integer)  # 外資
    trust_net_buy = Column(Integer)  # 投信
    dealer_net_buy = Column(Integer)  # 自營商
    
    # 分析結果
    consensus = Column(Boolean, default=False)  # 三大法人一致
    confidence = Column(Float)  # 信心度 0-1
    trend = Column(String(20))  # 'accumulating', 'distributing', 'neutral'
    
    # 累計數據
    foreign_3day_total = Column(Integer)
    foreign_5day_total = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.now)


class TechnicalScreening(Base):
    """技術面篩選結果"""
    __tablename__ = "technical_screening"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_date = Column(DateTime, default=datetime.now, index=True)
    stock_id = Column(String(10), index=True)
    stock_name = Column(String(50))
    
    # 當前價格與均線
    current_price = Column(Float)
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    
    # 技術指標
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    volume_ratio = Column(Float)  # 量比
    
    # 型態判斷
    breakout = Column(Boolean, default=False)  # 突破
    bullish_alignment = Column(Boolean, default=False)  # 多頭排列
    golden_cross = Column(Boolean, default=False)  # 黃金交叉
    
    # 綜合分數
    technical_score = Column(Integer)  # 0-100
    signals = Column(JSON)  # 符合的訊號列表
    
    created_at = Column(DateTime, default=datetime.now)


class NewsImpact(Base):
    """新聞影響追蹤"""
    __tablename__ = "news_impact"
    
    id = Column(Integer, primary_key=True, index=True)
    news_time = Column(DateTime, index=True)
    headline = Column(Text)
    source = Column(String(50))
    
    # 影響分析
    sentiment = Column(String(20))  # 'positive', 'negative', 'neutral'
    importance = Column(Integer)  # 1-10
    impact_description = Column(Text)
    
    # 相關股票
    related_stocks = Column(JSON)  # [{"id": "2330", "impact": "high"}, ...]
    affected_sectors = Column(JSON)
    
    # 分類
    category = Column(String(50))  # 'earnings', 'policy', 'M&A', 'tech', etc.
    is_urgent = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.now)


class FinalSelection(Base):
    """最終精選結果"""
    __tablename__ = "final_selection"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("premarket_analysis.id"))
    selection_date = Column(DateTime, default=datetime.now, index=True)
    
    # 排名與標的
    rank = Column(Integer)
    stock_id = Column(String(10), index=True)
    stock_name = Column(String(50))
    
    # 綜合評分
    total_score = Column(Integer)  # 0-100
    conditions_met = Column(Integer)  # 符合條件數
    confidence = Column(Float)  # 0-1
    
    # 評分細項
    us_impact_score = Column(Integer)
    institutional_score = Column(Integer)
    technical_score = Column(Integer)
    news_score = Column(Integer)
    
    # 選股原因
    reasons = Column(JSON)  # 列表
    
    # 交易策略
    entry_price = Column(Float)  # 建議進場價
    target_price = Column(Float)  # 目標價
    stop_loss = Column(Float)  # 停損價
    position_size = Column(String(20))  # '40%資金', '30%資金'
    strategy = Column(Text)  # 進場策略描述
    
    # 實際結果（事後填寫）
    actual_entry = Column(Float, nullable=True)
    actual_exit = Column(Float, nullable=True)
    actual_profit_percent = Column(Float, nullable=True)
    trade_result = Column(String(20), nullable=True)  # 'win', 'loss', 'break_even', 'not_traded'
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 關聯
    analysis = relationship("PreMarketAnalysis", back_populates="selections")


class OpeningExecution(Base):
    """開盤執行記錄"""
    __tablename__ = "opening_execution"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_date = Column(DateTime, default=datetime.now, index=True)
    stock_id = Column(String(10), index=True)
    stock_name = Column(String(50))
    
    # 開盤數據
    opening_price = Column(Float)
    expected_price = Column(Float)  # 預期價格
    gap_percent = Column(Float)  # 跳空幅度
    
    # 開盤型態
    opening_pattern = Column(String(20))  # 'gap_up', 'flat', 'gap_down'
    
    # 量能分析
    first_5min_volume = Column(Integer)
    avg_5min_volume = Column(Integer)
    volume_ratio = Column(Float)
    volume_status = Column(String(20))  # 'surge', 'normal', 'weak'
    
    # 執行決策
    decision = Column(String(20))  # 'buy', 'wait', 'skip'
    reason = Column(Text)
    urgency = Column(String(20))  # '立即', '正常', '觀望', '放棄'
    
    # 實際交易
    executed = Column(Boolean, default=False)
    execution_price = Column(Float, nullable=True)
    execution_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)


class SelectionStatistics(Base):
    """選股統計表"""
    __tablename__ = "selection_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(DateTime, index=True)
    period_end = Column(DateTime, index=True)
    
    # 交易統計
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    break_even_trades = Column(Integer)
    
    # 勝率
    win_rate = Column(Float)
    
    # 獲利統計
    total_profit_percent = Column(Float)
    avg_profit = Column(Float)
    avg_loss = Column(Float)
    expected_value = Column(Float)
    
    # 最佳/最差交易
    best_trade_percent = Column(Float)
    worst_trade_percent = Column(Float)
    
    # 紀律執行統計
    stop_loss_followed = Column(Integer)  # 嚴守停損次數
    chased_high = Column(Integer)  # 追高次數
    volume_confirmed = Column(Integer)  # 量能確認次數
    
    # 條件符合統計
    avg_conditions_met = Column(Float)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MarketSchedule(Base):
    """市場時間表"""
    __tablename__ = "market_schedule"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    
    # 重要時間點
    us_market_close = Column(DateTime)  # 美股收盤（台灣時間）
    overnight_analysis_time = Column(DateTime)  # 21:00
    morning_scan_time = Column(DateTime)  # 08:00
    futures_open_time = Column(DateTime)  # 08:45
    final_selection_time = Column(DateTime)  # 08:55
    market_open_time = Column(DateTime)  # 09:00
    
    # 狀態
    is_trading_day = Column(Boolean, default=True)
    holiday_name = Column(String(100), nullable=True)
    
    # 提醒設置
    alerts_enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.now)
