"""
處置股清單管理器

功能：
1. 從證交所抓取官方處置股清單
2. 維護本地處置股名單
3. 自動判斷監控股票是否為處置股
"""

import httpx
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Set
import json
import os

logger = logging.getLogger(__name__)


class DispositionStockManager:
    """處置股清單管理器"""
    
    def __init__(self):
        # 處置股清單（手動維護 + 自動抓取）
        self.disposition_stocks: Dict[str, Dict] = {}
        
        # 本地快取檔案
        self.cache_file = "/Users/Mac/Documents/ETF/AI/Ａi-catch/data/disposition_stocks.json"
        
        # 已知處置股（手動維護）
        self.known_disposition_stocks = {
            "2337": {
                "name": "旺宏",
                "start_date": "2026-01-12",
                "match_interval": 5,  # 5分鐘撮合
                "reason": "股價異常波動"
            },
            # 可以手動添加更多
        }
        
        # 載入快取
        self._load_cache()
    
    def _load_cache(self):
        """載入本地快取"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.disposition_stocks = data.get('stocks', {})
                    logger.info(f"載入 {len(self.disposition_stocks)} 支處置股")
        except Exception as e:
            logger.warning(f"載入處置股快取失敗: {e}")
        
        # 合併已知處置股
        self.disposition_stocks.update(self.known_disposition_stocks)
    
    def _save_cache(self):
        """儲存快取"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'stocks': self.disposition_stocks,
                    'updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存處置股快取失敗: {e}")
    
    async def fetch_twse_disposition_list(self) -> List[Dict]:
        """
        從證交所抓取處置股清單
        
        注意：證交所 API 可能需要特定格式
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 證交所處置股公告頁面
                # https://www.twse.com.tw/zh/trading/regulation/disposition.html
                
                # 嘗試抓取（實際 URL 可能需要調整）
                url = "https://www.twse.com.tw/rwd/zh/announcement/punish"
                
                resp = await client.get(url, params={
                    "date": datetime.now().strftime("%Y%m%d"),
                    "response": "json"
                })
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if data.get('stat') == 'OK':
                        stocks = []
                        for row in data.get('data', []):
                            # 解析證交所回傳的格式
                            if len(row) >= 3:
                                stocks.append({
                                    'symbol': row[0],
                                    'name': row[1],
                                    'reason': row[2] if len(row) > 2 else ''
                                })
                        return stocks
                
                logger.warning("證交所 API 無回應，使用本地清單")
                return []
                
        except Exception as e:
            logger.warning(f"抓取證交所處置股失敗: {e}")
            return []
    
    def add_disposition_stock(self, symbol: str, name: str = None,
                               start_date: str = None, 
                               match_interval: int = 5,
                               reason: str = None):
        """手動添加處置股"""
        self.disposition_stocks[symbol] = {
            "name": name or symbol,
            "start_date": start_date or datetime.now().strftime("%Y-%m-%d"),
            "match_interval": match_interval,
            "reason": reason or "手動添加"
        }
        self._save_cache()
        logger.info(f"已添加處置股: {symbol}")
    
    def remove_disposition_stock(self, symbol: str):
        """移除處置股（解除處置）"""
        if symbol in self.disposition_stocks:
            del self.disposition_stocks[symbol]
            self._save_cache()
            logger.info(f"已移除處置股: {symbol}")
    
    def is_disposition_stock(self, symbol: str) -> bool:
        """判斷是否為處置股"""
        return symbol in self.disposition_stocks
    
    def get_disposition_info(self, symbol: str) -> Optional[Dict]:
        """獲取處置股資訊"""
        return self.disposition_stocks.get(symbol)
    
    def get_all_disposition_stocks(self) -> Dict[str, Dict]:
        """獲取所有處置股"""
        return self.disposition_stocks
    
    def check_watchlist(self, watchlist: List[str]) -> Dict:
        """
        檢查監控清單中的處置股
        
        Args:
            watchlist: 監控股票清單（如 ORB 53支）
        
        Returns:
            {
                'total': 53,
                'disposition_count': 2,
                'disposition_stocks': [
                    {'symbol': '2337', 'name': '旺宏', ...},
                    ...
                ],
                'normal_stocks': ['2330', '2317', ...]
            }
        """
        disposition = []
        normal = []
        
        for symbol in watchlist:
            if self.is_disposition_stock(symbol):
                info = self.get_disposition_info(symbol)
                disposition.append({
                    'symbol': symbol,
                    **info
                })
            else:
                normal.append(symbol)
        
        return {
            'total': len(watchlist),
            'disposition_count': len(disposition),
            'disposition_stocks': disposition,
            'normal_count': len(normal),
            'normal_stocks': normal
        }
    
    def get_match_interval(self, symbol: str) -> int:
        """獲取撮合間隔（分鐘）"""
        info = self.get_disposition_info(symbol)
        return info.get('match_interval', 5) if info else 0


# 單例
disposition_manager = DispositionStockManager()


# 測試
if __name__ == "__main__":
    import asyncio
    
    # 測試監控清單檢查
    test_watchlist = [
        "2330", "2317", "2454", "2337", "6257", 
        "3034", "2881", "2882", "8422", "1326"
    ]
    
    result = disposition_manager.check_watchlist(test_watchlist)
    
    print("="*60)
    print("  監控清單處置股檢查")
    print("="*60)
    print(f"總監控：{result['total']} 支")
    print(f"處置股：{result['disposition_count']} 支")
    print(f"正常股：{result['normal_count']} 支")
    
    if result['disposition_stocks']:
        print("\n⚠️  處置股明細：")
        for stock in result['disposition_stocks']:
            print(f"   {stock['symbol']} {stock['name']} - 自 {stock['start_date']} 起")
