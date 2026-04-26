"""
數據庫服務層
提供報價、分析結果和警報的數據庫操作
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import select, insert, update, delete, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.models.stock import Stock, StockQuote, OrderBook

logger = logging.getLogger(__name__)


class DatabaseService:
    """數據庫服務類"""
    
    # === 股票基本資料 ===
    
    @staticmethod
    async def get_stock_by_symbol(symbol: str) -> Optional[Stock]:
        """根據代碼獲取股票"""
        async with async_session() as session:
            result = await session.execute(
                select(Stock).where(Stock.symbol == symbol)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_stocks() -> List[Stock]:
        """獲取所有活躍股票"""
        async with async_session() as session:
            result = await session.execute(
                select(Stock).where(Stock.is_active == True).order_by(Stock.symbol)
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def upsert_stock(symbol: str, name: str, market: str = "TWSE", industry: str = None) -> Stock:
        """新增或更新股票資料"""
        async with async_session() as session:
            # 查詢現有股票
            result = await session.execute(
                select(Stock).where(Stock.symbol == symbol)
            )
            stock = result.scalar_one_or_none()
            
            if stock:
                stock.name = name
                stock.market = market
                if industry:
                    stock.industry = industry
            else:
                stock = Stock(symbol=symbol, name=name, market=market, industry=industry)
                session.add(stock)
            
            await session.commit()
            await session.refresh(stock)
            return stock
    
    # === 報價數據 ===
    
    @staticmethod
    async def save_quote(
        symbol: str,
        price: float,
        open_price: float = None,
        high: float = None,
        low: float = None,
        volume: int = None,
        change_price: float = None,
        change_percent: float = None,
        timestamp: datetime = None
    ) -> bool:
        """保存報價數據"""
        try:
            async with async_session() as session:
                # 獲取股票 ID
                result = await session.execute(
                    select(Stock.id).where(Stock.symbol == symbol)
                )
                stock_id = result.scalar_one_or_none()
                
                if not stock_id:
                    logger.warning(f"股票 {symbol} 不存在，無法保存報價")
                    return False
                
                quote = StockQuote(
                    stock_id=stock_id,
                    symbol=symbol,
                    timestamp=timestamp or datetime.now(),
                    open=Decimal(str(open_price)) if open_price else None,
                    high=Decimal(str(high)) if high else None,
                    low=Decimal(str(low)) if low else None,
                    close=Decimal(str(price)),
                    volume=volume,
                    change_price=Decimal(str(change_price)) if change_price else None,
                    change_percent=Decimal(str(change_percent)) if change_percent else None
                )
                session.add(quote)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存報價失敗: {e}")
            return False
    
    @staticmethod
    async def save_quotes_batch(quotes: List[Dict[str, Any]]) -> int:
        """批量保存報價"""
        saved_count = 0
        for quote_data in quotes:
            success = await DatabaseService.save_quote(
                symbol=quote_data.get("symbol"),
                price=quote_data.get("price", 0),
                open_price=quote_data.get("open"),
                high=quote_data.get("high"),
                low=quote_data.get("low"),
                volume=quote_data.get("volume"),
                change_price=quote_data.get("change_price"),
                change_percent=quote_data.get("change")
            )
            if success:
                saved_count += 1
        return saved_count
    
    @staticmethod
    async def get_latest_quote(symbol: str) -> Optional[Dict]:
        """獲取最新報價"""
        async with async_session() as session:
            result = await session.execute(
                select(StockQuote)
                .where(StockQuote.symbol == symbol)
                .order_by(desc(StockQuote.timestamp))
                .limit(1)
            )
            quote = result.scalar_one_or_none()
            
            if quote:
                return {
                    "symbol": quote.symbol,
                    "price": float(quote.close),
                    "open": float(quote.open) if quote.open else None,
                    "high": float(quote.high) if quote.high else None,
                    "low": float(quote.low) if quote.low else None,
                    "volume": quote.volume,
                    "change": float(quote.change_percent) if quote.change_percent else None,
                    "timestamp": quote.timestamp.isoformat()
                }
            return None
    
    @staticmethod
    async def get_quote_history(symbol: str, limit: int = 100) -> List[Dict]:
        """獲取歷史報價"""
        async with async_session() as session:
            result = await session.execute(
                select(StockQuote)
                .where(StockQuote.symbol == symbol)
                .order_by(desc(StockQuote.timestamp))
                .limit(limit)
            )
            quotes = result.scalars().all()
            
            return [
                {
                    "timestamp": q.timestamp.isoformat(),
                    "open": float(q.open) if q.open else None,
                    "high": float(q.high) if q.high else None,
                    "low": float(q.low) if q.low else None,
                    "close": float(q.close),
                    "volume": q.volume
                }
                for q in quotes
            ]


# 創建單例實例
db_service = DatabaseService()
