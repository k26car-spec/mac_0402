from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class QuoteResponse(BaseModel):
    """報價回應模型"""
    symbol: str
    name: str
    openPrice: float
    highPrice: float
    lowPrice: float
    closePrice: float
    change: float
    changePercent: float
    volume: int
    lastUpdated: int

class BatchQuoteResponse(BaseModel):
    """批量報價回應"""
    success: bool
    data: Dict[str, QuoteResponse]

class CandleData(BaseModel):
    """K 線數據模型"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class CandlesResponse(BaseModel):
    """K 線回應"""
    success: bool
    data: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    """健康檢查回應"""
    status: str
    connected: bool
    message: Optional[str] = None
