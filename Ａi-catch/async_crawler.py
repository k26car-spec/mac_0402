# async_crawler.py - 異步股票數據爬蟲（整合富邦 SDK）

import aiohttp
import asyncio
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional
import logging
import ssl
import certifi
import time

# 先初始化 logger
logger = logging.getLogger(__name__)

# 嘗試導入富邦數據源
try:
    from fubon_data_source import fubon_data_source, get_stock_quote
    FUBON_AVAILABLE = True
    logger.info("✅ 富邦數據源已載入")
except ImportError:
    FUBON_AVAILABLE = False
    logger.warning("⚠️ 富邦數據源未可用，將使用 Yahoo Finance")

class AsyncStockCrawler:
    """
    異步股票數據爬蟲
    """
    
    def __init__(self):
        self.use_fubon = FUBON_AVAILABLE
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        # 創建 SSL 上下文以修復證書問題
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    async def fetch_yahoo_main_force(self, stock_code: str) -> Dict:
        """爬取雅虎主力進出"""
        url = f'https://tw.stock.yahoo.com/quote/{stock_code}/agent'
        
        try:
            async with self.session.get(url, headers=self.headers, ssl=self.ssl_context, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Yahoo API 返回狀態碼: {response.status}")
                    return {}
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 解析主力進出表格
                main_force_data = {
                    'stock_code': stock_code,
                    'timestamp': datetime.now().isoformat(),
                    'institutional_data': {}
                }
                
                # 找尋三大法人、主力券商
                tables = soup.find_all('table')
                for table in tables:
                    if '法人買賣超' in str(table):
                        rows = table.find_all('tr')
                        for row in rows[1:]:  # 跳過表頭
                            cols = row.find_all('td')
                            if len(cols) >= 2:
                                name = cols[0].text.strip()
                                value = cols[1].text.strip()
                                main_force_data['institutional_data'][name] = value
                
                return main_force_data
                
        except asyncio.TimeoutError:
            logger.error(f"Yahoo 數據獲取超時: {stock_code}")
            return {}
        except Exception as e:
            logger.error(f"Yahoo 數據獲取錯誤 {stock_code}: {e}")
            return {}
    
    async def fetch_yahoo_quote(self, stock_code: str) -> Dict:
        """獲取Yahoo Finance報價數據"""
        # 決定符號 (處理 .TW vs .TWO)
        symbol = stock_code  # 預設使用傳入的代碼
        
        # 如果傳入的是純數字代碼 (例如 "2330")，嘗試自動偵測或預設為 .TW
        if not symbol.endswith('.TW') and not symbol.endswith('.TWO'):
            # 嘗試查找已知後綴
            try:
                from stock_names import STOCK_NAMES
                stock_name_key_two = f"{symbol}.TWO"
                if stock_name_key_two in STOCK_NAMES:
                    symbol = stock_name_key_two # 如果在清單中明確標示為 .TWO
                else:
                    symbol = f"{symbol}.TW"     # 預設為 .TW
            except ImportError:
                symbol = f"{symbol}.TW"
        
        # 定義獲取資料的內部函數
        async def fetch_data(target_symbol):
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{target_symbol}'
            params = {'interval': '1d', 'range': '1mo'}
            try:
                async with self.session.get(url, params=params, headers=self.headers, ssl=self.ssl_context, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
            except Exception:
                return None

        # 第一次嘗試
        data = await fetch_data(symbol)
        
        # 如果失敗且是我們自動猜測的 .TW，嘗試 .TWO
        if not data and symbol.endswith('.TW') and not stock_code.endswith('.TW'):
             alt_symbol = symbol.replace('.TW', '.TWO')
             data = await fetch_data(alt_symbol)
             if data:
                 symbol = alt_symbol # 更新符號以供後續使用
        
        if not data:
            return {}
            
        try:
            if 'chart' not in data or 'result' not in data['chart']:
                return {}
            
            result = data['chart']['result'][0]
            
            # 提取OHLCV數據
            meta = result.get('meta', {})
            indicators = result.get('indicators', {})
            quotes = indicators.get('quote', [{}])[0]
            timestamps = result.get('timestamp', [])
            
            if not timestamps or not quotes:
                return {}
                
            return {
                'stock_code': stock_code, # 保持原始代碼 (供系統識別)
                'market_symbol': symbol,  # 實際查詢到的代碼 (含正確後綴)
                'currency': meta.get('currency', 'TWD'),
                'timestamp': timestamps,
                'open': quotes.get('open', []),
                'high': quotes.get('high', []),
                'low': quotes.get('low', []),
                'close': quotes.get('close', []),
                'volume': quotes.get('volume', [])
            }
                
        except Exception as e:
            logger.error(f"Yahoo Quote 解析錯誤 {stock_code}: {e}")
            return {}
    
    async def fetch_fubon_realtime(self, stock_code: str) -> Dict:
        """
        富邦即時數據（模擬API）
        實際使用時需要替換為真實的富邦API
        """
        # 這裡需要富邦的實際API endpoint
        # 以下為模擬數據結構
        return {
            'stock_code': stock_code,
            'timestamp': datetime.now().isoformat(),
            'bid_orders': [
                {'price': 500.0, 'volume': 1500},
                {'price': 499.5, 'volume': 2000},
                {'price': 499.0, 'volume': 1800},
                {'price': 498.5, 'volume': 2200},
                {'price': 498.0, 'volume': 2500}
            ],
            'ask_orders': [
                {'price': 501.0, 'volume': 800},
                {'price': 501.5, 'volume': 1200},
                {'price': 502.0, 'volume': 1000},
                {'price': 502.5, 'volume': 1500},
                {'price': 503.0, 'volume': 1300}
            ],
            'large_trades': [
                {'time': '09:30:15', 'price': 500.5, 'volume': 850},
                {'time': '09:45:30', 'price': 501.0, 'volume': 1200},
                {'time': '10:15:00', 'price': 500.0, 'volume': 950}
            ]
        }
    
    async def fetch_multiple_stocks(self, stock_list: List[str]) -> List[Dict]:
        """同時爬取多支股票"""
        tasks = []
        
        for stock in stock_list:
            # 為每支股票建立多個數據源任務
            tasks.append(self.fetch_yahoo_main_force(stock))
            tasks.append(self.fetch_yahoo_quote(stock))
            # tasks.append(self.fetch_fubon_realtime(stock))  # 如有富邦API可啟用
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理結果，過濾異常
        valid_results = []
        for result in results:
            if isinstance(result, dict) and result:
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"任務執行異常: {result}")
        
        return valid_results
    
    async def monitor_stream(self, stock_codes: List[str], callback: Callable, interval: int = 60, ignore_time_check: bool = False):
        """
        即時監控串流
        
        Args:
            stock_codes: 股票代碼列表
            callback: 數據處理回調函數
            interval: 檢查間隔（秒）
            ignore_time_check: 是否忽略交易時間檢查
        """
        # 初始化session
        if not self.session:
            # 創建帶 SSL 配置的 session
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)
        
        logger.info(f"開始監控 {len(stock_codes)} 支股票 (忽略交易時間: {ignore_time_check})")
        
        try:
            while True:
                current_time = datetime.now()
                
                # 只在交易時間監控 (或忽略檢查)
                if ignore_time_check or self._is_trading_time(current_time):
                    # ...
                    logger.info(f"⏰ 監控時間: {current_time.strftime('%H:%M:%S')}")
                    
                    # 批量取得數據
                    all_data = await self.fetch_multiple_stocks(stock_codes)
                    
                    # 按股票代碼整理數據
                    stock_data_map = {}
                    for data in all_data:
                        if 'stock_code' in data:
                            code = data['stock_code']
                            if code not in stock_data_map:
                                stock_data_map[code] = []
                            stock_data_map[code].append(data)
                    
                    # 處理並回調
                    for stock_code, data_list in stock_data_map.items():
                        try:
                            # 合併該股票的所有數據
                            merged_data = self._merge_stock_data(data_list)
                            await callback(stock_code, merged_data)
                        except Exception as e:
                            logger.error(f"回調處理錯誤 {stock_code}: {e}")
                else:
                    logger.info(f"非交易時間，等待中... ({current_time.strftime('%H:%M:%S')})")
                
                # 等待下一次更新
                await asyncio.sleep(interval)
                
        except Exception as e:
            logger.error(f"監控錯誤: {e}")
            await asyncio.sleep(5)
        finally:
            if self.session:
                await self.session.close()
    
    def _merge_stock_data(self, data_list: List[Dict]) -> Dict:
        """合併同一股票的多個數據源"""
        merged = {
            'stock_code': data_list[0].get('stock_code'),
            'timestamp': datetime.now().isoformat()
        }
        
        for data in data_list:
            merged.update(data)
        
        return merged
    
    def _is_trading_time(self, dt: datetime) -> bool:
        """
        判斷是否為交易時間
        台股交易時間：週一至週五 09:00-13:30
        """
        weekday = dt.weekday()
        hour = dt.hour
        minute = dt.minute
        
        # 週一至週五
        if 0 <= weekday <= 4:
            # 上午盤 9:00-13:30
            if hour == 9 and minute >= 0:
                return True
            elif 10 <= hour <= 12:
                return True
            elif hour == 13 and minute <= 30:
                return True
        
        return False
    
    async def close(self):
        """關閉session"""
        if self.session:
            await self.session.close()
            self.session = None


# 使用示例
async def example_usage():
    crawler = AsyncStockCrawler()
    
    # 定義回調函數
    async def on_data_received(stock_code, data):
        print(f"收到 {stock_code} 的數據: {data}")
    
    # 開始監控
    watchlist = ['2330.TW', '2317.TW', '2454.TW']
    await crawler.monitor_stream(watchlist, on_data_received, interval=60)


if __name__ == '__main__':
    # 運行示例
    asyncio.run(example_usage())
