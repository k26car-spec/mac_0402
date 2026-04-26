"""
Taiwan Stock List Service
台股清單服務 - 從證交所與櫃買中心獲取完整台股清單
"""

import asyncio
import httpx
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaiwanStockListService:
    """台股清單服務"""
    
    # 證交所上市股票清單 API
    TWSE_STOCK_LIST_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json"
    # 證交所上市公司基本資料
    TWSE_COMPANY_LIST_URL = "https://www.twse.com.tw/zh/api/codeFilters"
    # 櫃買中心上櫃股票清單
    TPEX_STOCK_LIST_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
    
    # 備用：isin 代碼查詢（包含完整名稱）
    TWSE_ISIN_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    TPEX_ISIN_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    
    def __init__(self):
        self.last_update: Optional[datetime] = None
        self._stock_cache: Dict[str, Dict] = {}
    
    async def fetch_all_stocks(self) -> List[Dict]:
        """
        獲取所有台股清單（上市 + 上櫃）
        返回格式: [{"symbol": "2330", "name": "台積電", "market": "TWSE", "industry": "半導體"}, ...]
        """
        stocks = []
        
        # 並行獲取上市和上櫃股票
        twse_task = self._fetch_twse_stocks()
        tpex_task = self._fetch_tpex_stocks()
        
        twse_stocks, tpex_stocks = await asyncio.gather(twse_task, tpex_task, return_exceptions=True)
        
        if isinstance(twse_stocks, list):
            stocks.extend(twse_stocks)
            logger.info(f"獲取上市股票 {len(twse_stocks)} 支")
        else:
            logger.error(f"獲取上市股票失敗: {twse_stocks}")
        
        if isinstance(tpex_stocks, list):
            stocks.extend(tpex_stocks)
            logger.info(f"獲取上櫃股票 {len(tpex_stocks)} 支")
        else:
            logger.error(f"獲取上櫃股票失敗: {tpex_stocks}")
        
        # 更新快取
        self._stock_cache = {s["symbol"]: s for s in stocks}
        self.last_update = datetime.now()
        
        logger.info(f"總共獲取 {len(stocks)} 支台股")
        return stocks
    
    async def _fetch_twse_stocks(self) -> List[Dict]:
        """從證交所獲取上市股票清單"""
        stocks = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 使用 ISIN 網站獲取完整資料
                response = await client.get(
                    self.TWSE_ISIN_URL,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                
                if response.status_code == 200:
                    stocks = self._parse_isin_html(response.text, "TWSE")
                    
        except Exception as e:
            logger.error(f"從證交所獲取股票清單失敗: {e}")
            # 嘗試備用方案
            stocks = await self._fetch_twse_backup()
        
        return stocks
    
    async def _fetch_twse_backup(self) -> List[Dict]:
        """備用方案：從證交所 API 獲取"""
        stocks = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json",
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data:
                        for row in data["data"]:
                            if len(row) >= 2:
                                symbol = row[0].strip()
                                name = row[1].strip()
                                if symbol.isdigit() and len(symbol) == 4:
                                    stocks.append({
                                        "symbol": symbol,
                                        "name": name,
                                        "market": "TWSE",
                                        "industry": ""
                                    })
        except Exception as e:
            logger.error(f"備用方案獲取失敗: {e}")
        return stocks
    
    async def _fetch_tpex_stocks(self) -> List[Dict]:
        """從櫃買中心獲取上櫃股票清單"""
        stocks = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 使用 ISIN 網站獲取完整資料
                response = await client.get(
                    self.TPEX_ISIN_URL,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                
                if response.status_code == 200:
                    stocks = self._parse_isin_html(response.text, "TPEX")
                    
        except Exception as e:
            logger.error(f"從櫃買中心獲取股票清單失敗: {e}")
            # 嘗試備用方案
            stocks = await self._fetch_tpex_backup()
        
        return stocks
    
    async def _fetch_tpex_backup(self) -> List[Dict]:
        """備用方案：從櫃買中心 OpenAPI 獲取"""
        stocks = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.TPEX_STOCK_LIST_URL,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        symbol = item.get("SecuritiesCompanyCode", "").strip()
                        name = item.get("CompanyName", "").strip()
                        if symbol and len(symbol) == 4 and symbol.isdigit():
                            stocks.append({
                                "symbol": symbol,
                                "name": name,
                                "market": "TPEX",
                                "industry": ""
                            })
        except Exception as e:
            logger.error(f"櫃買中心備用方案獲取失敗: {e}")
        return stocks
    
    def _parse_isin_html(self, html: str, market: str) -> List[Dict]:
        """解析 ISIN 網站的 HTML 表格"""
        stocks = []
        
        try:
            # 簡單的 HTML 解析（不依賴 BeautifulSoup）
            # 格式：<td>代碼　名稱</td>
            import re
            
            # 找到表格中的資料行
            pattern = r'<td[^>]*>(\d{4})\s*　\s*([^<]+)</td>'
            matches = re.findall(pattern, html)
            
            current_industry = ""
            for match in matches:
                symbol = match[0].strip()
                name = match[1].strip()
                
                # 過濾有效的股票代碼（4位數字）
                if symbol.isdigit() and len(symbol) == 4:
                    stocks.append({
                        "symbol": symbol,
                        "name": name,
                        "market": market,
                        "industry": current_industry
                    })
            
            # 如果沒有匹配到，嘗試其他模式
            if not stocks:
                # 嘗試解析包含產業別的格式
                lines = html.split("<tr")
                for line in lines:
                    # 尋找股票代碼和名稱
                    code_match = re.search(r'>(\d{4})\s+([^<]+)<', line)
                    if code_match:
                        symbol = code_match.group(1).strip()
                        name = code_match.group(2).strip()
                        if len(symbol) == 4:
                            stocks.append({
                                "symbol": symbol,
                                "name": name,
                                "market": market,
                                "industry": ""
                            })
                            
        except Exception as e:
            logger.error(f"解析 ISIN HTML 失敗: {e}")
        
        return stocks
    
    def get_stock_name(self, symbol: str) -> Optional[str]:
        """根據代碼取得股票名稱（從快取）"""
        stock = self._stock_cache.get(symbol)
        return stock["name"] if stock else None
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """根據代碼取得股票資訊（從快取）"""
        return self._stock_cache.get(symbol)
    
    def search_stocks(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜尋股票（從快取）"""
        keyword = keyword.lower()
        results = []
        
        for symbol, info in self._stock_cache.items():
            if (keyword in symbol.lower() or 
                keyword in info.get("name", "").lower()):
                results.append(info)
                if len(results) >= limit:
                    break
        
        return results
    
    @property
    def stock_count(self) -> int:
        """取得快取中的股票數量"""
        return len(self._stock_cache)


# 全局單例
taiwan_stock_service = TaiwanStockListService()
