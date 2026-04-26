"""
FinMind API 整合服務
免費且台灣股市資料完整

API 文檔: https://finmindtrade.com/analysis/#/data/api
"""

import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import asyncio

logger = logging.getLogger(__name__)

# FinMind API 設定
FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"

# 股票市場類別對照表 (已知的上櫃股票)
# 與 patch_yfinance.py 保持同步
OTC_STOCKS = {
    # 專家確認的上櫃股票
    '3363', '3163', '5438', '6163',
    # 其他常見上櫃股票
    '8021', '8110', '8046', '8155', '5475', '3706',
    '6257', '3231', '7610', '3030', '1605',
    # 常見上櫃科技股
    '3057', '3062', '3064', '3092', '3115', '3144',
    '3188', '3217', '3224', '3242', '3252', '3265',
}

# 興櫃股票 (Yahoo/FinMind 可能無資料)
EMERGING_STOCKS = {
    '7810',
}


def get_stock_market_type(stock_code: str) -> str:
    """
    判斷股票市場類別
    
    Returns:
        'OTC' - 上櫃
        'TWSE' - 上市
        'EMERGING' - 興櫃
    """
    clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
    
    if clean_code in EMERGING_STOCKS:
        return 'EMERGING'
    elif clean_code in OTC_STOCKS:
        return 'OTC'
    else:
        return 'TWSE'


def get_yahoo_symbol(stock_code: str) -> str:
    """取得正確的 Yahoo Finance 股票代碼"""
    clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
    market_type = get_stock_market_type(clean_code)
    
    if market_type == 'OTC':
        return f"{clean_code}.TWO"
    elif market_type == 'TWSE':
        return f"{clean_code}.TW"
    else:
        return f"{clean_code}.TWO"  # 興櫃先嘗試 .TWO


class FinMindService:
    """FinMind API 服務"""
    
    def __init__(self, api_token: str = None):
        """
        初始化 FinMind 服務
        
        Args:
            api_token: API Token (可選，免費用戶不需要)
        """
        self.api_token = api_token
        self.session = None
    
    async def _get_session(self):
        if not self.session:
            import ssl
            import certifi
            
            # 使用 certifi 的證書
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_stock_price(
        self,
        stock_code: str,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """
        取得股票歷史價格
        
        API: TaiwanStockPrice
        
        Args:
            stock_code: 股票代碼 (如 2330)
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
        
        Returns:
            價格列表
        """
        clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": clean_code,
            "start_date": start_date,
            "end_date": end_date,
        }
        
        if self.api_token:
            params["token"] = self.api_token
        
        try:
            session = await self._get_session()
            async with session.get(FINMIND_API_URL, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 200 and data.get('data'):
                        logger.debug(f"FinMind 取得 {clean_code} 價格資料 {len(data['data'])} 筆")
                        return data['data']
                    else:
                        logger.debug(f"FinMind 無資料: {data.get('msg', 'unknown')}")
                else:
                    logger.warning(f"FinMind API 錯誤: {response.status}")
        except Exception as e:
            logger.debug(f"FinMind API 請求失敗: {e}")
        
        return []
    
    async def get_latest_price(self, stock_code: str) -> Optional[Dict]:
        """
        取得最新價格
        
        Returns:
            {
                'date': str,
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': int,
                'change': float,
                'source': 'finmind'
            }
        """
        # 取得最近5天資料（確保有交易日資料）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        prices = await self.get_stock_price(stock_code, start_date, end_date)
        
        if prices:
            latest = prices[-1]  # 最後一筆資料
            prev = prices[-2] if len(prices) >= 2 else latest
            
            close_price = float(latest.get('close', 0))
            prev_close = float(prev.get('close', close_price))
            change_pct = ((close_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            return {
                'date': latest.get('date'),
                'open': float(latest.get('open', 0)),
                'high': float(latest.get('max', latest.get('high', 0))),
                'low': float(latest.get('min', latest.get('low', 0))),
                'close': close_price,
                'volume': int(latest.get('Trading_Volume', latest.get('volume', 0))),
                'change': round(change_pct, 2),
                'source': 'finmind'
            }
        
        return None
    
    async def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        取得股票基本資訊
        
        API: TaiwanStockInfo
        """
        clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
        
        params = {
            "dataset": "TaiwanStockInfo",
            "data_id": clean_code,
        }
        
        if self.api_token:
            params["token"] = self.api_token
        
        try:
            session = await self._get_session()
            async with session.get(FINMIND_API_URL, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 200 and data.get('data'):
                        return data['data'][0] if data['data'] else None
        except Exception as e:
            logger.debug(f"FinMind 取得股票資訊失敗: {e}")
        
        return None
    
    async def get_institutional_investors(
        self,
        stock_code: str,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """
        取得三大法人買賣超
        
        API: TaiwanStockInstitutionalInvestorsBuySell
        """
        clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        params = {
            "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
            "data_id": clean_code,
            "start_date": start_date,
            "end_date": end_date,
        }
        
        if self.api_token:
            params["token"] = self.api_token
        
        try:
            session = await self._get_session()
            async with session.get(FINMIND_API_URL, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 200:
                        return data.get('data', [])
        except Exception as e:
            logger.debug(f"FinMind 取得法人資料失敗: {e}")
        
        return []


# 全域實例
finmind_service = FinMindService()


# 便捷函數
async def get_finmind_price(stock_code: str) -> Optional[Dict]:
    """取得 FinMind 最新價格"""
    return await finmind_service.get_latest_price(stock_code)


async def get_finmind_history(
    stock_code: str,
    days: int = 180
) -> List[Dict]:
    """取得 FinMind 歷史價格"""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    return await finmind_service.get_stock_price(stock_code, start_date, end_date)


# 測試
if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("FinMind API 測試")
        print("=" * 60)
        
        service = FinMindService()
        
        # 測試上市股票
        print("\n📊 測試上市股票 (2330 台積電):")
        price = await service.get_latest_price('2330')
        if price:
            print(f"  最新價格: {price['close']}")
            print(f"  漲跌幅: {price['change']}%")
        
        # 測試上櫃股票
        print("\n📊 測試上櫃股票 (3363):")
        price = await service.get_latest_price('3363')
        if price:
            print(f"  最新價格: {price['close']}")
            print(f"  漲跌幅: {price['change']}%")
        else:
            print("  ❌ 無法取得資料")
        
        await service.close()
        print("\n✅ 測試完成!")
    
    asyncio.run(test())
