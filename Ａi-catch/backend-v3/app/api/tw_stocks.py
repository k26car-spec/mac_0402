"""
Taiwan Stock List API
台股清單 API - 管理所有台股代碼與名稱
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from app.database import get_db
from app.models.stock import Stock
from app.services.taiwan_stock_service import taiwan_stock_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", summary="獲取所有台股清單")
async def get_all_stocks(
    skip: int = Query(0, ge=0, description="跳過的記錄數"),
    limit: int = Query(100, ge=1, le=2000, description="返回的最大記錄數"),
    market: Optional[str] = Query(None, description="市場篩選 (TWSE/TPEX)"),
    active_only: bool = Query(True, description="只顯示有效股票"),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取所有台股清單
    
    - 支援分頁查詢
    - 支援市場篩選（TWSE 上市 / TPEX 上櫃）
    """
    stmt = select(Stock)
    
    if active_only:
        stmt = stmt.where(Stock.is_active == True)
    
    if market:
        stmt = stmt.where(Stock.market == market.upper())
    
    stmt = stmt.order_by(Stock.symbol).offset(skip).limit(limit)
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    # 獲取總數
    count_stmt = select(func.count(Stock.id))
    if active_only:
        count_stmt = count_stmt.where(Stock.is_active == True)
    if market:
        count_stmt = count_stmt.where(Stock.market == market.upper())
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar()
    
    return {
        "success": True,
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "count": len(stocks),
        "stocks": [
            {
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market,
                "industry": stock.industry,
                "is_active": stock.is_active
            }
            for stock in stocks
        ]
    }


@router.get("/search", summary="搜尋股票")
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜尋關鍵字（代碼或名稱）"),
    limit: int = Query(10, ge=1, le=50, description="返回的最大記錄數"),
    db: AsyncSession = Depends(get_db)
):
    """
    搜尋股票（支援代碼和名稱模糊搜尋）
    
    - 優先從資料庫搜尋
    - 若資料庫無結果，會從證交所快取即時查詢
    
    範例:
    - /api/tw-stocks/search?q=2330
    - /api/tw-stocks/search?q=台積
    """
    # 先從資料庫搜尋
    stmt = select(Stock).where(
        or_(
            Stock.symbol.contains(q),
            Stock.name.contains(q)
        ),
        Stock.is_active == True
    ).limit(limit)
    
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    stock_list = [
        {
            "symbol": stock.symbol,
            "name": stock.name,
            "market": stock.market,
            "industry": stock.industry
        }
        for stock in stocks
    ]
    
    # 如果資料庫無結果，嘗試從證交所快取搜尋
    if not stock_list:
        # 檢查快取是否為空，如果是則先獲取資料
        if taiwan_stock_service.stock_count == 0:
            logger.info("快取為空，嘗試從證交所獲取股票清單...")
            try:
                await taiwan_stock_service.fetch_all_stocks()
            except Exception as e:
                logger.error(f"從證交所獲取股票清單失敗: {e}")
        
        # 從快取搜尋
        cache_results = taiwan_stock_service.search_stocks(q, limit)
        if cache_results:
            stock_list = cache_results
            logger.info(f"從快取找到 {len(stock_list)} 筆符合 '{q}' 的股票")
    
    return {
        "success": True,
        "keyword": q,
        "count": len(stock_list),
        "source": "database" if stocks else ("cache" if stock_list else "none"),
        "stocks": stock_list
    }


@router.get("/{symbol}", summary="獲取單一股票資訊")
async def get_stock(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    獲取單一股票的詳細資訊
    """
    stmt = select(Stock).where(Stock.symbol == symbol)
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()
    
    if not stock:
        raise HTTPException(status_code=404, detail=f"找不到股票 {symbol}")
    
    return {
        "success": True,
        "stock": {
            "symbol": stock.symbol,
            "name": stock.name,
            "market": stock.market,
            "industry": stock.industry,
            "sector": stock.sector,
            "listed_date": stock.listed_date.isoformat() if stock.listed_date else None,
            "is_active": stock.is_active,
            "created_at": stock.created_at.isoformat() if stock.created_at else None,
            "updated_at": stock.updated_at.isoformat() if stock.updated_at else None
        }
    }


@router.post("/sync", summary="從證交所同步台股清單")
async def sync_stock_list(
    db: AsyncSession = Depends(get_db)
):
    """
    從證交所和櫃買中心同步最新的台股清單
    
    - 會自動新增新股票
    - 會更新現有股票的名稱
    - 會標記已下市的股票為非活躍
    
    ⚠️ 注意：此操作可能需要較長時間（約 10-30 秒）
    """
    try:
        # 從證交所獲取最新清單
        logger.info("開始同步台股清單...")
        stocks_from_api = await taiwan_stock_service.fetch_all_stocks()
        
        if not stocks_from_api:
            return {
                "success": False,
                "error": "無法從證交所獲取股票清單",
                "message": "請稍後再試或檢查網路連線"
            }
        
        # 統計
        added = 0
        updated = 0
        
        # 獲取現有的股票代碼
        existing_stmt = select(Stock.symbol)
        existing_result = await db.execute(existing_stmt)
        existing_symbols = set(row[0] for row in existing_result.fetchall())
        
        # 新清單的代碼
        new_symbols = set(s["symbol"] for s in stocks_from_api)
        
        # 新增或更新股票
        for stock_data in stocks_from_api:
            symbol = stock_data["symbol"]
            
            if symbol in existing_symbols:
                # 更新現有股票
                stmt = select(Stock).where(Stock.symbol == symbol)
                result = await db.execute(stmt)
                stock = result.scalar_one_or_none()
                
                if stock:
                    # 只在名稱有變化時更新
                    if stock.name != stock_data["name"]:
                        stock.name = stock_data["name"]
                        stock.updated_at = datetime.utcnow()
                        updated += 1
                    
                    # 確保是活躍狀態
                    if not stock.is_active:
                        stock.is_active = True
                        stock.updated_at = datetime.utcnow()
            else:
                # 新增股票
                new_stock = Stock(
                    symbol=symbol,
                    name=stock_data["name"],
                    market=stock_data.get("market", "TWSE"),
                    industry=stock_data.get("industry", ""),
                    is_active=True
                )
                db.add(new_stock)
                added += 1
        
        # 標記已下市的股票（在資料庫中但不在新清單中）
        delisted = 0
        for symbol in existing_symbols - new_symbols:
            stmt = select(Stock).where(Stock.symbol == symbol)
            result = await db.execute(stmt)
            stock = result.scalar_one_or_none()
            if stock and stock.is_active:
                stock.is_active = False
                stock.updated_at = datetime.utcnow()
                delisted += 1
        
        await db.commit()
        
        logger.info(f"同步完成: 新增 {added}, 更新 {updated}, 下市 {delisted}")
        
        return {
            "success": True,
            "message": "台股清單同步完成",
            "statistics": {
                "total_from_api": len(stocks_from_api),
                "added": added,
                "updated": updated,
                "delisted": delisted
            },
            "last_sync": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"同步台股清單失敗: {e}")
        await db.rollback()
        return {
            "success": False,
            "error": str(e),
            "message": "同步失敗，請檢查日誌"
        }


@router.get("/stats/summary", summary="取得台股統計摘要")
async def get_stock_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    取得台股清單統計摘要
    """
    # 總數
    total_stmt = select(func.count(Stock.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar()
    
    # 活躍股票數
    active_stmt = select(func.count(Stock.id)).where(Stock.is_active == True)
    active_result = await db.execute(active_stmt)
    active = active_result.scalar()
    
    # 上市股票數
    twse_stmt = select(func.count(Stock.id)).where(Stock.market == "TWSE", Stock.is_active == True)
    twse_result = await db.execute(twse_stmt)
    twse_count = twse_result.scalar()
    
    # 上櫃股票數
    tpex_stmt = select(func.count(Stock.id)).where(Stock.market == "TPEX", Stock.is_active == True)
    tpex_result = await db.execute(tpex_stmt)
    tpex_count = tpex_result.scalar()
    
    return {
        "success": True,
        "statistics": {
            "total": total,
            "active": active,
            "inactive": total - active,
            "twse": twse_count,
            "tpex": tpex_count
        },
        "last_cache_update": taiwan_stock_service.last_update.isoformat() if taiwan_stock_service.last_update else None,
        "cache_count": taiwan_stock_service.stock_count
    }


@router.post("/init", summary="初始化台股清單")
async def init_stock_list(
    db: AsyncSession = Depends(get_db)
):
    """
    初始化台股清單（首次使用時呼叫）
    
    如果資料庫中已有股票資料，會先詢問是否覆蓋
    """
    # 檢查現有資料
    count_stmt = select(func.count(Stock.id))
    count_result = await db.execute(count_stmt)
    existing_count = count_result.scalar()
    
    if existing_count > 0:
        return {
            "success": False,
            "message": f"資料庫中已有 {existing_count} 支股票，請使用 /sync 端點進行更新",
            "existing_count": existing_count
        }
    
    # 執行同步
    return await sync_stock_list(db)
