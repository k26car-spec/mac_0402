"""
台股股票代碼 <-> 名稱映射表
從 TWSE 官方 API 獲取並緩存
"""

import requests
import json
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TWStockNameMapper:
    """台股代碼<->名稱映射器"""
    
    def __init__(self):
        self.name_map: Dict[str, str] = {}
        self.last_update = None
        self.cache_duration = timedelta(days=1)  # 每天更新一次
    

    def _fetch_from_twse(self) -> Dict[str, str]:
        """從台灣證交所獲取上市股票清單"""
        try:
            # 修正 URL：舊版 URL 可能失效，改用新的 API 或正確的參數
            # 參考：https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json
            url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            mapping = {}
            
            # TWSE 回傳格式：{"data": [["代碼", "名稱", "成交量", ...], ...]}
            # 注意：第一欄是代碼，第二欄是名稱
            count = 0
            if 'data' in data:
                for row in data['data']:
                    if len(row) >= 2:
                        code = row[0].strip()
                        name = row[1].strip()
                        # 簡單過濾：只保留純數字代碼 (避免權證等)
                        # 並排除 00 開頭的 ETF (如果使用者想要 ETF 另外處理，但這裡先全抓，上層再濾)
                        if code.isdigit() and len(code) == 4:
                             mapping[code] = name
                             count += 1
            
            logger.info(f"✅ 從 TWSE 獲取 {count} 支上市股票名稱")
            return mapping
            
        except Exception as e:
            logger.error(f"從 TWSE 獲取股票清單失敗: {e}")
            return {}

    def _fetch_from_tpex(self) -> Dict[str, str]:
        """從櫃買中心獲取上櫃股票清單"""
        mapping = {}
        
        # 嘗試最近 5 天，找到有數據的日期（避開假日）
        for days_ago in range(0, 5):
            try:
                target_date = datetime.now() - timedelta(days=days_ago)
                
                # 轉民國年格式 YYY/MM/DD
                roc_year = target_date.year - 1911
                date_str = f"{roc_year}/{target_date.month:02d}/{target_date.day:02d}"
                
                # 改用更穩定的 API: 上櫃股票每日收盤行情
                # https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&d=113/05/17&s=0,asc,0
                url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&d={date_str}&s=0,asc,0"
                headers = {'User-Agent': 'Mozilla/5.0'}
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200: continue
                
                data = response.json()
                count = 0
                
                # 解析邏輯: 尋找 aaData (舊) 或其他結構
                # 根據最新觀察，TPEX json 結構通常含 'aaData' 列表
                rows = []
                if 'aaData' in data:
                    rows = data['aaData']
                elif 'tables' in data and len(data['tables']) > 0:
                     rows = data['tables'][0]['data']

                for row in rows:
                    # row format: ["代號", "名稱", ...]
                    if len(row) >= 2:
                        code = row[0].strip()
                        name = row[1].strip()
                        if code.isdigit() and len(code) == 4:
                            mapping[code] = name
                            count += 1
                
                if count > 0:
                    logger.info(f"✅ 從 TPEX 獲取 {count} 支上櫃股票名稱 ({date_str})")
                    return mapping

            except Exception as e:
                # logger.debug(f"TPEX 嘗試失敗 ({date_str}): {e}")
                continue
        
        logger.error("❌ 無法獲取 TPEX 上櫃股票清單")
        return mapping
    
    def update_mapping(self) -> bool:
        """更新股票清單"""
        if self.last_update and (datetime.now() - self.last_update) < self.cache_duration:
            logger.debug("股票清單緩存有效，跳過更新")
            return True
        
        logger.info("🔄 更新台股名稱映射表...")
        
        # 合併上市 + 上櫃
        twse_map = self._fetch_from_twse()
        tpex_map = self._fetch_from_tpex()
        
        self.name_map = {**twse_map, **tpex_map}
        
        if self.name_map:
            self.last_update = datetime.now()
            logger.info(f"✅ 股票清單更新完成，共 {len(self.name_map)} 支")
            return True
        
        return False
    
    def get_name(self, symbol: str) -> str:
        """
        獲取股票名稱
        
        Args:
            symbol: 股票代碼（支持 2330, 2330.TW, 2330.TWO 格式）
        
        Returns:
            股票中文名稱，如果找不到則返回代碼本身
        """
        # 清理代碼
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '').strip()
        
        # 確保映射表已更新
        if not self.name_map:
            self.update_mapping()
        
        # 查詢
        return self.name_map.get(clean_symbol, clean_symbol)
    
    def get_all_symbols(self) -> list:
        """獲取所有股票代碼"""
        if not self.name_map:
            self.update_mapping()
        return list(self.name_map.keys())


# 全局單例
tw_stock_mapper = TWStockNameMapper()


def get_stock_name(symbol: str) -> str:
    """
    快速獲取股票中文名稱
    
    Usage:
        >>> get_stock_name("2330")
        '台積電'
        >>> get_stock_name("3380")
        '明泰'
    """
    return tw_stock_mapper.get_name(symbol)


# 啟動時預載
try:
    tw_stock_mapper.update_mapping()
except:
    pass
