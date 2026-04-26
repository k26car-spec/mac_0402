"""
Sniper Watchlist API
當沖狙擊手清單管理 API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from app.services.sniper_watchlist import sniper_watchlist

router = APIRouter(prefix="/api/sniper", tags=["Sniper Watchlist"])


class AddStockRequest(BaseModel):
    sector_key: str
    symbol: str
    name: Optional[str] = None


class AddSectorRequest(BaseModel):
    key: str
    name: str
    emoji: Optional[str] = "📊"


@router.get("/sectors")
async def get_sectors():
    """取得所有產業分類與股票名稱對照"""
    return {
        "success": True,
        "sectors": sniper_watchlist.get_sectors(),
        "stock_names": sniper_watchlist.data.get("stock_names", {})
    }


@router.get("/stocks")
async def get_all_stocks():
    """取得所有監控股票（去重）"""
    stocks = sniper_watchlist.get_all_stocks()
    return {
        "success": True,
        "count": len(stocks),
        "stocks": stocks
    }


@router.get("/sector/{sector_key}")
async def get_sector(sector_key: str):
    """取得單一產業詳情"""
    sector = sniper_watchlist.get_sector(sector_key)
    if not sector:
        raise HTTPException(status_code=404, detail=f"產業 {sector_key} 不存在")
    
    # 附加股票名稱
    stocks_with_names = []
    for symbol in sector.get("stocks", []):
        stocks_with_names.append({
            "symbol": symbol,
            "name": sniper_watchlist.get_stock_name(symbol)
        })
    
    return {
        "success": True,
        "sector_key": sector_key,
        "sector": {
            **sector,
            "stocks_detail": stocks_with_names
        }
    }


@router.post("/stock/add")
async def add_stock(req: AddStockRequest):
    """新增股票到產業"""
    if req.sector_key not in sniper_watchlist.get_sectors():
        raise HTTPException(status_code=404, detail=f"產業分類 {req.sector_key} 不存在")
    
    success = sniper_watchlist.add_stock_to_sector(req.sector_key, req.symbol, req.name)
    if not success:
         raise HTTPException(status_code=400, detail=f"股票 {req.symbol} 已經在 {req.sector_key} 監控名單中")
    
    return {
        "success": True,
        "message": f"已將 {req.symbol} 加入 {req.sector_key}"
    }


@router.post("/stock/remove")
async def remove_stock(sector_key: str, symbol: str):
    """從產業移除股票"""
    success = sniper_watchlist.remove_stock_from_sector(sector_key, symbol)
    if not success:
        raise HTTPException(status_code=400, detail="移除失敗")
    
    return {
        "success": True,
        "message": f"已將 {symbol} 從 {sector_key} 移除"
    }


@router.post("/sector/add")
async def add_sector(req: AddSectorRequest):
    """新增產業分類"""
    success = sniper_watchlist.add_sector(req.key, req.name, req.emoji)
    if not success:
        raise HTTPException(status_code=400, detail="產業已存在")
    
    return {
        "success": True,
        "message": f"已建立產業 {req.name}"
    }


@router.post("/reload")
async def reload_watchlist():
    """重新載入清單（從 JSON 檔案）"""
    sniper_watchlist.reload()
    return {
        "success": True,
        "message": "清單已重新載入",
        "sector_count": len(sniper_watchlist.get_sectors()),
        "stock_count": len(sniper_watchlist.get_all_stocks())
    }
