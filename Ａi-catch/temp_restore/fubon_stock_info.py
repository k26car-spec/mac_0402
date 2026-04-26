#!/usr/bin/env python3
# fubon_stock_info.py - 透過富邦 API 獲取股票資訊

import requests
import json
import logging
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)

class FubonStockInfo:
    """
    富邦證券股票資訊 API
    """
    
    def __init__(self):
        self.base_url = "https://www.fbs.com.tw/TradeRD/rest/api/stock/info"
        self.cache = {}  # 名稱快取
        self.cache_ttl = 86400  # 快取24小時
        self.last_update = {}
        
    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        獲取股票中文名稱
        
        Args:
            stock_code: 股票代碼 (如: 2330.TW 或 2330)
        
        Returns:
            str: 中文名稱，如果失敗則返回 None
        """
        # 清理股票代碼（移除 .TW）
        clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
        
        # 檢查快取
        if clean_code in self.cache:
            # 檢查快取是否過期
            if time.time() - self.last_update.get(clean_code, 0) < self.cache_ttl:
                return self.cache[clean_code]
        
        # 從 API 獲取
        try:
            name = self._fetch_from_api(clean_code)
            if name:
                self.cache[clean_code] = name
                self.last_update[clean_code] = time.time()
                return name
        except Exception as e:
            logger.error(f"富邦 API 獲取失敗 {clean_code}: {e}")
        
        return None
    
    def _fetch_from_api(self, stock_code: str) -> Optional[str]:
        """
        從 API 獲取股票資訊
        
        優先使用富邦 API (用戶指定)
        """
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 1. 優先嘗試富邦 API
        try:
            url = f"https://www.fbs.com.tw/TradeRD/rest/api/stock/info/{stock_code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            logger.info(f"嘗試從富邦 API 獲取 {stock_code}...")
            # 跳過 SSL 驗證
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, dict):
                    name_fields = ['name', 'stockName', 'stock_name', 'nm', 'stockNm']
                    for field in name_fields:
                        if field in data and data[field]:
                            name = data[field]
                            logger.info(f"✅ 富邦 API 成功: {stock_code} -> {name}")
                            return name
            else:
                logger.warning(f"富邦 API 返回狀態碼: {response.status_code}")
                
        except Exception as e:
            logger.error(f"富邦 API 失敗 {stock_code}: {e}")

        # 2. 備用：Yahoo Finance
        try:
            logger.info(f"嘗試從 Yahoo API 獲取 {stock_code}...")
            name = self._fetch_from_yahoo(stock_code)
            if name:
                logger.info(f"✅ Yahoo API 成功: {stock_code} -> {name}")
                return name
        except Exception as e:
            logger.error(f"Yahoo API 失敗 {stock_code}: {e}")
        
        return None
    
    def _fetch_from_yahoo(self, stock_code: str) -> Optional[str]:
        """
        備用方案：從 Yahoo Finance 獲取
        """
        try:
            import certifi
            
            url = f"https://query1.finance.yahoo.com/v7/finance/quote"
            params = {
                'symbols': f"{stock_code}.TW",
                'fields': 'longName,shortName'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # 使用 certifi 提供的證書
            response = requests.get(url, params=params, headers=headers, 
                                  timeout=10, verify=certifi.where())
            
            if response.status_code == 200:
                data = response.json()
                
                if 'quoteResponse' in data and 'result' in data['quoteResponse']:
                    results = data['quoteResponse']['result']
                    if results and len(results) > 0:
                        result = results[0]
                        # 優先使用 shortName，因為通常是中文
                        name = result.get('shortName') or result.get('longName')
                        if name:
                            # 移除後綴（如 "台積電 Ordinary Shares" -> "台積電"）
                            name = name.split(' Ordinary')[0].split(' ADR')[0]
                            return name
                            
        except Exception as e:
            logger.debug(f"Yahoo 備用 API 失敗 {stock_code}: {e}")
        
        return None
    
    def batch_get_names(self, stock_codes: list) -> Dict[str, str]:
        """
        批量獲取股票名稱
        
        Args:
            stock_codes: 股票代碼列表
        
        Returns:
            dict: {股票代碼: 中文名稱}
        """
        results = {}
        
        for code in stock_codes:
            clean_code = code.replace('.TW', '').replace('.TWO', '')
            name = self.get_stock_name(code)
            if name:
                results[clean_code] = name
            else:
                results[clean_code] = None
        
        return results


# 全域實例
_fubon_info = None

def get_fubon_instance():
    """獲取富邦 API 實例（單例模式）"""
    global _fubon_info
    if _fubon_info is None:
        _fubon_info = FubonStockInfo()
    return _fubon_info


def get_stock_name_from_fubon(stock_code: str) -> Optional[str]:
    """
    方便的函數：獲取股票中文名稱
    
    Args:
        stock_code: 股票代碼
    
    Returns:
        str: 中文名稱或 None
    """
    fubon = get_fubon_instance()
    return fubon.get_stock_name(stock_code)


# 測試函數
def test_fubon_api():
    """測試富邦 API"""
    print("🧪 測試富邦 API 股票資訊獲取\n")
    
    fubon = FubonStockInfo()
    
    # 測試股票列表
    test_stocks = [
        '2330.TW',  # 台積電
        '2317.TW',  # 鴻海
        '2454.TW',  # 聯發科
        '0050.TW',  # 元大台灣50
        '2344',     # 華邦電
        '8110',     # 華東
    ]
    
    print("開始測試...\n")
    
    for stock in test_stocks:
        clean_code = stock.replace('.TW', '')
        name = fubon.get_stock_name(stock)
        
        if name:
            print(f"✅ {clean_code:10s} → {name}")
        else:
            print(f"❌ {clean_code:10s} → 獲取失敗")
    
    print("\n測試完成！")


if __name__ == '__main__':
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    
    # 執行測試
    test_fubon_api()
