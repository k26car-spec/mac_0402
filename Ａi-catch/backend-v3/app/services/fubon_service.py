"""
富邦證券 API 整合模組
Fubon Securities API Integration for Backend v3

提供即時報價數據，優先使用富邦 API，回退到 Yahoo Finance
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# 添加項目根目錄到 path
# backend-v3/app/services/fubon_service.py -> backend-v3/app/services -> backend-v3/app -> backend-v3 -> 項目根目錄
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

# 富邦 SDK 單例
from stock_mappings import get_stock_name
_fubon_client = None
_fubon_connected = False


async def init_fubon_client():
    """初始化富邦客戶端"""
    global _fubon_client, _fubon_connected
    
    if _fubon_connected and _fubon_client:
        return True
    
    try:
        from fubon_client import fubon_client
        _fubon_client = fubon_client
        
        # 嘗試連接
        success = await _fubon_client.connect()
        _fubon_connected = success
        
        if success:
            logger.info("✅ 富邦 API 連接成功")
        else:
            logger.warning("⚠️ 富邦 API 連接失敗，將使用 Yahoo Finance 作為回退")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 富邦客戶端初始化失敗: {e}")
        _fubon_connected = False
        return False


async def get_stock_chinese_name(symbol: str) -> str:
    """使用富邦 API 抓取股票中文名稱"""
    clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
    
    # 1. 優先嘗試從富邦 API 抓取 (實時)
    try:
        if not _fubon_connected:
            await init_fubon_client()
            
        if _fubon_connected and _fubon_client:
            # 優先使用 SDK 的 ticker API
            name = await _fubon_client.get_stock_name(clean_symbol)
            if name and name != clean_symbol:
                return name
    except Exception as e:
        logger.debug(f"富邦 API 抓取名稱失敗: {e}")
        
    # 2. 備援使用原本的映射
    try:
        name = get_stock_name(clean_symbol)
        if name and name != clean_symbol:
            return name
    except:
        pass
        
    return clean_symbol


async def get_fubon_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """從富邦 API 獲取即時報價"""
    global _fubon_client, _fubon_connected
    
    if not _fubon_connected:
        await init_fubon_client()
    
    if not _fubon_connected or not _fubon_client:
        return None
    
    try:
        import asyncio
        retry_count = 2  # 減少重試次數
        
        for i in range(retry_count):
            try:
                # 設定較短的超時
                quote = await asyncio.wait_for(
                    _fubon_client.get_quote(symbol),
                    timeout=3.0  # 從 5 秒降到 3 秒
                )
                
                if quote and quote.get('price', 0) > 0:
                    quote['source'] = 'fubon'
                    quote['dataSource'] = '富邦API'
                    quote['timestamp'] = datetime.now().isoformat()
                    
                    # 計算漲跌幅
                    ref_price = quote.get('referencePrice') or quote.get('prev_close') or quote.get('previousClose') or quote.get('open')
                    
                    if ref_price and ref_price > 0:
                        quote['change'] = round((quote['price'] - ref_price) / ref_price * 100, 2)
                    elif quote.get('open', 0) > 0:
                        quote['change'] = round((quote['price'] - quote['open']) / quote['open'] * 100, 2)
                    
                    return quote
            except asyncio.TimeoutError:
                logger.warning(f"富邦報價超時: {symbol}")
                _fubon_connected = False
                return None  # 直接返回，不再重試
            except Exception as e:
                if "WebSocket" in str(e) or "Connection" in str(e) or "closed" in str(e):
                    logger.warning(f"富邦 WebSocket 斷線: {e}")
                    _fubon_connected = False
                    return None  # 直接返回，讓 Yahoo 接手
                if i == retry_count - 1:
                    pass
                await asyncio.sleep(0.1)
                
        return None
        
    except Exception as e:
        logger.error(f"富邦報價獲取失敗: {e}")
        _fubon_connected = False
        return None


async def get_yahoo_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """從 Yahoo Finance 獲取報價（回退方案）"""
    try:
        import yfinance as yf
        
        # 已知上櫃股票列表 (TPEx) - 避免對上市股票嘗試 .TWO
        known_tpex = {
            "5498", "8074", "3163", "3265", "3363", "8155", "5521", "3529",
            "6153", "8299", "8069", "5347", "6147", "3293", "3680", "4966",
            "5274", "6121", "6180", "6488", "8938", "8255", "3105", "3217"
        }
        
        suffixes_to_try = ['.TW']
        if symbol in known_tpex:
            suffixes_to_try = ['.TWO']
        else:
            # 對於未知股票，如果不是明確的上市代碼，才嘗試 .TWO
            # 這裡簡單假設除了明確的 TPEx 外，預設 .TW，失敗後才試 .TWO
            # 但為了減少 1605.TWO 的錯誤，我們可以檢查它是否在我們已知的上市名單中 (這裡沒名單，所以保留回退機制但做優化)
            suffixes_to_try = ['.TW', '.TWO']

        for suffix in suffixes_to_try:
            # 如果是第一輪 (.TW) 失敗，且股票不在已知上櫃名單，且是常見上市股，則不試 .TWO
            if suffix == '.TWO' and symbol not in known_tpex:
                if symbol in ["1605", "2330", "2317", "2454", "2881", "2882", "1101", "2002", "1301", "1303", "2603", "2609", "2615"]:
                     continue
            
            try:
                ticker = yf.Ticker(f"{symbol}{suffix}")
                hist = ticker.history(period="1d")
                info = ticker.info
                
                if not hist.empty:
                    last_row = hist.iloc[-1]
                    current_price = round(float(last_row['Close']), 2)
                    
                    # 🔧 修正：使用昨收價計算漲跌幅
                    prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
                    if prev_close and prev_close > 0:
                        change_pct = round((current_price - prev_close) / prev_close * 100, 2)
                    elif last_row['Open'] > 0:
                        # 備用: 用開盤價
                        change_pct = round((current_price - last_row['Open']) / last_row['Open'] * 100, 2)
                    else:
                        change_pct = 0
                    
                    return {
                        "symbol": symbol,
                        "price": current_price,
                        "open": round(float(last_row['Open']), 2),
                        "high": round(float(last_row['High']), 2),
                        "low": round(float(last_row['Low']), 2),
                        "volume": int(last_row['Volume']),
                        "previousClose": prev_close,
                        "change": change_pct,
                        "source": f"yahoo{suffix}",
                        "dataSource": "Yahoo",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception:
                continue
        
        return None
        
    except Exception as e:
        logger.debug(f"Yahoo Finance 報價獲取失敗 {symbol}: {e}")
        return None


async def get_order_book(symbol: str) -> Optional[Dict[str, Any]]:
    """獲取五檔揭示 (從富邦 API)"""
    global _fubon_client, _fubon_connected
    if not _fubon_connected:
        await init_fubon_client()
    if not _fubon_connected or not _fubon_client:
        return None
    try:
        clean = symbol.replace('.TW', '').replace('.TWO', '')
        return await _fubon_client.get_books(clean)
    except Exception as e:
        logger.debug(f"獲取盤口五檔失敗 {symbol}: {e}")
        return None


async def get_realtime_quote(symbol: str) -> Dict[str, Any]:
    """
    獲取即時報價（優先富邦，回退 Yahoo）
    
    Args:
        symbol: 股票代碼（如 2330）
    
    Returns:
        報價數據字典
    """
    # 清理股票代碼
    clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
    
    # 🆕 優先使用富邦 API 獲取股票名稱，不要使用靜態清單
    try:
        if not _fubon_connected:
            await init_fubon_client()
        stock_name = await _fubon_client.get_stock_name(clean_symbol)
    except Exception as e:
        logger.debug(f"富邦名稱獲取失敗，嘗試備援: {e}")
        stock_name = get_stock_name(clean_symbol) # 備援使用靜態清單
            
    if not stock_name or stock_name == clean_symbol:
        try:
            from app.services.sniper_watchlist import sniper_watchlist
            stock_name = sniper_watchlist.get_stock_name(clean_symbol)
            if stock_name == clean_symbol: stock_name = None
        except:
            pass
    
    # 1. 優先嘗試富邦 API 獲取報價 (現在 get_fubon_quote 會返回名稱)
    quote = await get_fubon_quote(clean_symbol)
    
    if quote and quote.get('price', 0) > 0:
        # 確保有名稱
        if not quote.get('name') or quote['name'] == clean_symbol:
            quote['name'] = stock_name or await get_stock_chinese_name(clean_symbol)
        return quote
    
    # 2. 回退到 Yahoo Finance
    logger.info(f"富邦報價無數據，使用 Yahoo Finance: {clean_symbol}")
    quote = await get_yahoo_quote(clean_symbol)
    
    if quote:
        quote['name'] = stock_name or await get_stock_chinese_name(clean_symbol)
        return quote
    
    # 3. 返回空數據
    return {
        "symbol": clean_symbol,
        "name": stock_name or await get_stock_chinese_name(clean_symbol),
        "price": 0,
        "change": 0,
        "error": "無法獲取報價",
        "source": "none",
        "timestamp": datetime.now().isoformat()
    }


async def get_intraday_data(symbol: str, timeframe: str = "1") -> Optional[List[Dict[str, Any]]]:
    """獲取盤中 K 線數據 (1分鐘或5分鐘)"""
    global _fubon_client, _fubon_connected
    
    if not _fubon_connected:
        await init_fubon_client()
        
    if not _fubon_connected or not _fubon_client:
        return None
        
    try:
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 使用 SDK 獲取當日 K 線
        candles = await _fubon_client.get_candles(
            symbol=clean_symbol,
            from_date=today,
            to_date=today,
            timeframe=timeframe
        )
        
        return candles
    except Exception as e:
        logger.error(f"獲取盤中 K 線失敗 {symbol}: {e}")
        return None


def calculate_vwap(candles: List[Dict[str, Any]]) -> float:
    """從 K 線數據計算 VWAP"""
    if not candles:
        return 0.0
        
    total_value = 0.0
    total_volume = 0
    
    for candle in candles:
        # Typical Price = (High + Low + Close) / 3
        high = float(candle.get('high', 0))
        low = float(candle.get('low', 0))
        close = float(candle.get('close', 0))
        volume = int(candle.get('volume', 0))
        
        typical_price = (high + low + close) / 3
        total_value += typical_price * volume
        total_volume += volume
        
    if total_volume == 0:
        return 0.0
        
    return round(total_value / total_volume, 2)


async def get_batch_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    """
    批量獲取即時報價（並行）
    優先富邦 API，回退 Yahoo Finance
    
    Args:
        symbols: 股票代碼列表（如 ['2330', '2337', '2454']）
    
    Returns:
        報價數據列表
    """
    import asyncio

    async def _get_one(symbol: str) -> Dict[str, Any]:
        try:
            clean = symbol.replace('.TW', '').replace('.TWO', '')
            quote = await get_realtime_quote(clean)
            return quote
        except Exception as e:
            logger.debug(f"批量報價失敗 {symbol}: {e}")
            return {
                "symbol": symbol.replace('.TW', '').replace('.TWO', ''),
                "name": symbol,
                "price": 0,
                "change": 0,
                "source": "error",
                "timestamp": datetime.now().isoformat()
            }

    # 並行取得所有股票報價（最多同時 10 個，避免過度壓測 API）
    semaphore = asyncio.Semaphore(10)

    async def _bounded(sym: str) -> Dict:
        async with semaphore:
            return await _get_one(sym)

    tasks = [_bounded(s) for s in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)


async def get_fubon_name(symbol: str) -> Optional[str]:
    """使用富邦 API 獲取股票中文名稱"""
    global _fubon_client, _fubon_connected
    
    clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
    
    try:
        from fubon_client import fubon_client
        if not fubon_client.is_connected:
            await fubon_client.connect()
        
        if fubon_client.is_connected:
            res = fubon_client.sdk.marketdata.rest_client.stock.intraday.ticker(symbol=clean_symbol)
            if res and 'name' in res:
                return res['name']
    except Exception as e:
        logger.debug(f"富邦名稱獲取失敗: {e}")
    return None


def get_fubon_status() -> Dict[str, Any]:
    """獲取富邦連接狀態"""
    global _fubon_connected
    try:
        from fubon_client import fubon_client
        is_actually_connected = _fubon_connected or fubon_client.is_connected
    except:
        is_actually_connected = _fubon_connected
        
    return {
        "connected": is_actually_connected,
        "source": "fubon" if is_actually_connected else "yahoo",
        "timestamp": datetime.now().isoformat()
    }
