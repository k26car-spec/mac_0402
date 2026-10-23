from fastapi import APIRouter, HTTPException
from typing import Optional, List
from fubon_client import fubon_client
from models import QuoteResponse, BatchQuoteResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["quotes"])

@router.get("/quote/{symbol}", response_model=Optional[QuoteResponse])
async def get_quote(symbol: str):
    """
    取得單一股票即時報價
    
    - **symbol**: 股票代號 (例如: 2330.TW)
    """
    try:
        quote = await fubon_client.get_quote(symbol)
        
        if not quote:
            raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")
        
        return quote
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quote/batch", response_model=BatchQuoteResponse)
async def get_quotes_batch(symbols: List[str]):
    """
    批量取得多個股票報價
    
    - **symbols**: 股票代號列表
    """
    try:
        results = {}
        
        for symbol in symbols:
            quote = await fubon_client.get_quote(symbol)
            if quote:
                results[symbol] = quote
        
        return {"success": True, "data": results}
        
    except Exception as e:
        logger.error(f"Error getting batch quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
