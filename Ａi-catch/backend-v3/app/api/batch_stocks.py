"""
批量股票查詢 API
用於一次性獲取多個股票的名稱和基本資訊
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class BatchStockRequest(BaseModel):
    codes: List[str]


class StockNameResponse(BaseModel):
    code: str
    name: str
    source: str  # 'fubon', 'yfinance', 'cache', 'default'


@router.post("/stocks/batch-names", response_model=List[StockNameResponse])
async def get_batch_stock_names(request: BatchStockRequest):
    """
    批量獲取股票名稱
    
    優化點：
    1. 並發查詢（不是串聯）
    2. 優先使用富邦API（最快）
    3. 自動fallback到yfinance
    4. 返回完整映射
    
    Example:
        POST /api/stocks/batch-names
        {"codes": ["2330", "2337", "2454"]}
        
        Response:
        [
            {"code": "2330", "name": "台積電", "source": "fubon"},
            {"code": "2337", "name": "旺宏", "source": "fubon"},
            {"code": "2454", "name": "聯發科", "source": "yfinance"}
        ]
    """
    if not request.codes:
        raise HTTPException(status_code=400, detail="股票代碼清單不可為空")
    
    if len(request.codes) > 100:
        raise HTTPException(status_code=400, detail="一次最多查詢100檔股票")
    
    logger.info(f"📊 批量查詢股票名稱: {len(request.codes)} 檔")
    
    # 並發查詢所有股票
    tasks = [_get_single_stock_name(code) for code in request.codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 整理結果
    response = []
    for code, result in zip(request.codes, results):
        if isinstance(result, Exception):
            logger.warning(f"⚠️ {code} 查詢失敗: {result}")
            response.append(StockNameResponse(
                code=code,
                name=code,  # fallback to code
                source="error"
            ))
        else:
            response.append(result)
    
    logger.info(f"✅ 批量查詢完成: {len(response)} 檔股票")
    return response


async def _get_single_stock_name(code: str) -> StockNameResponse:
    """
    查詢單一股票名稱（內部函數）
    優先順序: 預定義名稱 > 富邦API > Yahoo Finance
    """
    # 預定義常用股票名稱（最快）
    PREDEFINED_NAMES = {
        '2330': '台積電', '2454': '聯發科', '2317': '鴻海', '3008': '大立光',
        '2881': '富邦金', '2882': '國泰金', '2412': '中華電', '2308': '台達電',
        '2337': '旺宏', '2303': '聯電', '2344': '華邦電', '3034': '聯詠',
        '2379': '瑞昱', '2408': '南亞科', '3231': '緯創', '2603': '長榮',
        '2609': '陽明', '2615': '萬海', '2891': '中信金', '2886': '兆豐金',
        '2884': '玉山金', '2892': '第一金', '2002': '中鋼', '1101': '台泥',
        '1301': '台塑', '1303': '南亞', '1326': '台化', '6505': '台塑化',
        '2912': '統一超', '9910': '豐泰', '2301': '光寶科', '3017': '奇鋐',
        '2449': '京元電', '6257': '矽格', '6770': '力積電', '3706': '神達',
        '2371': '大同', '2312': '金寶', '3265': '台星科', '8150': '南茂',
        '6239': '力成', '3661': '世芯-KY', '3443': '創意', '2313': '華通',
        '2314': '台揚', '6285': '啟碁', '3163': '波若威', '3363': '上詮',
        '5521': '工信', '8422': '可寧衛', '1815': '富喬', '3481': '群創',
        '2327': '國巨', '6282': '康舒', '1605': '華新', '2367': '燿華',
        '8074': '鉅橡', '8155': '博智', '5498': '凱崴', '3037': '欣興',
        '8046': '南電', '3189': '景碩', '2618': '長榮航', '1802': '台玻',
    }
    
    # 1. 檢查預定義名稱
    if code in PREDEFINED_NAMES:
        return StockNameResponse(
            code=code,
            name=PREDEFINED_NAMES[code],
            source="predefined"
        )
    
    # 2. 嘗試富邦API（最快最準確）
    try:
        from app.services.fubon_service import fubon_service
        quote = await asyncio.wait_for(
            fubon_service.get_quote_data(code),
            timeout=2.0
        )
        if quote and 'name' in quote and quote['name'] != code:
            return StockNameResponse(
                code=code,
                name=quote['name'],
                source="fubon"
            )
    except asyncio.TimeoutError:
        logger.debug(f"⏱️ Fubon API timeout for {code}")
    except Exception as e:
        logger.debug(f"⚠️ Fubon API error for {code}: {e}")
    
    # 3. Fallback: Yahoo Finance
    try:
        import yfinance as yf
        from app.patch_yfinance import fix_taiwan_symbol
        
        symbol = fix_taiwan_symbol(code)
        ticker = yf.Ticker(symbol)
        info = await asyncio.wait_for(
            asyncio.to_thread(lambda: ticker.info),
            timeout=3.0
        )
        
        # 嘗試多個可能的名稱欄位
        for key in ['longName', 'shortName', 'name']:
            if key in info and info[key] and info[key] != code:
                name = info[key]
                # 移除常見後綴
                name = name.replace(' Corporation', '').replace(' Co., Ltd.', '')
                name = name.replace(' Inc.', '').strip()
                return StockNameResponse(
                    code=code,
                    name=name,
                    source="yfinance"
                )
    except asyncio.TimeoutError:
        logger.debug(f"⏱️ Yahoo Finance timeout for {code}")
    except Exception as e:
        logger.debug(f"⚠️ Yahoo Finance error for {code}: {e}")
    
    # 4. 最終fallback：返回股票代碼
    logger.warning(f"❌ 無法查詢 {code} 的名稱，使用代碼作為名稱")
    return StockNameResponse(
        code=code,
        name=code,
        source="fallback"
    )


@router.get("/stocks/name/{code}")
async def get_single_stock_name_endpoint(code: str):
    """
    查詢單一股票名稱（向後兼容的端點）
    """
    if not code or not code.isdigit() or len(code) != 4:
        raise HTTPException(status_code=400, detail="無效的股票代碼")
    
    result = await _get_single_stock_name(code)
    return {
        "code": result.code,
        "name": result.name,
        "source": result.source
    }
