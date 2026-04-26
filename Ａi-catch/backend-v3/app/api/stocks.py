"""
Stock API Endpoints
股票相关的 API 端点
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import Stock

router = APIRouter()


@router.get("/", summary="获取股票列表")
async def get_stocks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    获取股票列表
    
    参数:
    - skip: 跳过的记录数
    - limit: 返回的最大记录数
    """
    stmt = select(Stock).offset(skip).limit(limit)
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    return {
        "count": len(stocks),
        "stocks": [
            {
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "industry": stock.industry,
                "is_active": stock.is_active
            }
            for stock in stocks
        ]
    }


@router.get("/{symbol}", summary="获取单一股票详情")
async def get_stock(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取单一股票的详细信息
    
    参数:
    - symbol: 股票代码（如：2330）
    """
    stmt = select(Stock).where(Stock.symbol == symbol)
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()
    
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    return {
        "id": stock.id,
        "symbol": stock.symbol,
        "name": stock.name,
        "market": stock.market,
        "industry": stock.industry,
        "sector": stock.sector,
        "listed_date": stock.listed_date,
        "is_active": stock.is_active,
        "created_at": stock.created_at,
        "updated_at": stock.updated_at
    }


@router.get("/search/{keyword}", summary="搜索股票")
async def search_stocks(
    keyword: str,
    db: AsyncSession = Depends(get_db)
):
    """
    根据关键字搜索股票
    
    参数:
    - keyword: 搜索关键字（代码或名称）
    """
    stmt = select(Stock).where(
        (Stock.symbol.contains(keyword)) | (Stock.name.contains(keyword))
    )
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    return {
        "keyword": keyword,
        "count": len(stocks),
        "stocks": [
            {
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "industry": stock.industry
            }
            for stock in stocks
        ]
    }
