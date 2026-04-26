#!/usr/bin/env python3
# fubon_search_api.py - 富邦證券股票搜尋 API

import requests
import json
import logging
from typing import List, Dict, Optional
import urllib3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FubonSearchAPI:
    """
    富邦證券股票搜尋 API
    提供股票資訊搜尋功能
    """
    
    def __init__(self):
        self.base_url = "https://www.fbs.com.tw/TradeRD/rest/api"
        self.timeout = 10
        
    def search_stock(self, keyword: str) -> List[Dict]:
        """
        搜尋股票（支持代碼或名稱）
        
        Args:
            keyword: 搜尋關鍵字
            
        Returns:
            股票列表 [{code, name, type}, ...]
        """
        results = []
        
        # 方法1: 嘗試獲取單一股票資訊
        if keyword.isdigit():
            stock_info = self.get_stock_info(keyword)
            if stock_info:
                results.append(stock_info)
        
        # 方法2: 嘗試搜尋 API（如果富邦有提供搜尋接口）
        # 這裡需要實際的富邦搜尋 API endpoint
        
        # 方法3: 從台股上市櫃清單搜尋（備用）
        if not results:
            results = self._search_from_tw_stocks(keyword)
        
        return results
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        獲取單一股票資訊
        """
        try:
            # 清理代碼
            code = stock_code.replace('.TW', '').replace('.TWO', '')
            
            # 方法1: 富邦個股資訊 API
            url = f"{self.base_url}/stock/info/{code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.fbs.com.tw/'
            }
            
            logger.info(f"查詢富邦 API: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
            
            logger.info(f"狀態碼: {response.status_code}")
            logger.info(f"響應內容: {response.text[:200]}")
            
            if response.status_code == 200:
                # 嘗試解析 JSON
                try:
                    data = response.json()
                    logger.info(f"JSON 數據: {data}")
                    
                    # 提取股票名稱
                    name = None
                    possible_fields = ['name', 'stockName', 'stock_name', 'nm', 'stockNm', 'Name']
                    
                    for field in possible_fields:
                        if field in data and data[field]:
                            name = data[field]
                            break
                    
                    if name:
                        return {
                            'code': code,
                            'name': name,
                            'full_code': f'{code}.TW',
                            'source': 'fubon'
                        }
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 解析失敗: {e}")
                    # 如果是 HTML，可能需要不同的 endpoint
                    
        except Exception as e:
            logger.error(f"獲取失敗: {e}")
        
        return None
    
    def _search_from_tw_stocks(self, keyword: str) -> List[Dict]:
        """
        從台股清單搜尋（內建常用股票）
        """
        # 台股上市櫃常用股票（擴充版）
        tw_stocks = {
            # 權值股
            '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2308': '台達電',
            '3008': '大立光', '2412': '中華電', '2303': '聯電', '2382': '廣達',
            '2891': '中信金', '2882': '國泰金', '2881': '富邦金', '2886': '兆豐金',
            
            # 電子股
            '2344': '華邦電', '2409': '友達', '3481': '群創', '2377': '微星',
            '2357': '華碩', '2324': '仁寶', '2301': '光寶科', '3045': '台灣大',
            
            # 傳產
            '1301': '台塑', '1303': '南亞', '1326': '台化', '1101': '台泥',
            '2002': '中鋼', '2105': '正新', '2201': '裕隆', '2207': '和泰車',
            
            # 金融
            '2884': '玉山金', '2885': '元大金', '2887': '台新金', '2892': '第一金',
            '5880': '合庫金', '2890': '永豐金',
            
            # ETF
            '0050': '元大台灣50', '0056': '元大高股息', '006208': '富邦台50',
            '00631L': '元大台灣50正2', '00632R': '元大台灣50反1',
            
            # 其他
            '8110': '華東', '8021': '尖點', '3706': '神達', '5521': '工信',
            '2357': '華碩', '2395': '研華', '3711': '日月光投控'
        }
        
        results = []
        keyword_upper = keyword.upper()
        
        for code, name in tw_stocks.items():
            # 搜尋代碼或名稱
            if (code.startswith(keyword) or 
                keyword in code or 
                keyword in name):
                results.append({
                    'code': code,
                    'name': name,
                    'full_code': f'{code}.TW',
                    'source': 'local'
                })
        
        return results[:20]  # 限制最多20個結果


# 便捷函數
def search_stocks(keyword: str) -> List[Dict]:
    """搜尋股票"""
    api = FubonSearchAPI()
    return api.search_stock(keyword)


# 測試
if __name__ == '__main__':
    print("🔍 富邦股票搜尋 API 測試\n")
    
    test_keywords = ['2330', '台積電', '金', '50']
    
    for keyword in test_keywords:
        print(f"搜尋: '{keyword}'")
        results = search_stocks(keyword)
        
        if results:
            for stock in results[:5]:
                print(f"  ✅ {stock['code']:8s} {stock['name']:12s} ({stock['source']})")
        else:
            print("  ❌ 無結果")
        print()
