"""
Sniper Watchlist Service
當沖狙擊手清單管理服務 - 讀取 JSON 設定檔
"""

import json
import os
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

WATCHLIST_FILE = os.path.join(
    os.path.dirname(__file__),
    "../../../data/sniper_watchlist.json"
)

# 預設清單（如果 JSON 檔案不存在時使用）
DEFAULT_WATCHLIST = {
    "sectors": {
        "memory": {
            "name": "記憶體",
            "emoji": "💾",
            "stocks": ["2337", "2344", "2408"]
        },
        "semiconductor": {
            "name": "半導體",
            "emoji": "🔬",
            "stocks": ["2330", "2454", "3034"]
        }
    },
    "stock_names": {
        "2330": "台積電",
        "2454": "聯發科",
        "2337": "旺宏",
        "2344": "華邦電",
        "2408": "南亞科",
        "3034": "聯詠"
    }
}

class SniperWatchlistService:
    def __init__(self):
        self.data = self._load_watchlist()
    
    def _load_watchlist(self) -> Dict:
        """載入清單設定"""
        try:
            if os.path.exists(WATCHLIST_FILE):
                with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"✅ 載入狙擊手清單: {len(data.get('sectors', {}))} 個產業")
                    return data
        except Exception as e:
            logger.error(f"載入清單失敗: {e}")
        
        return DEFAULT_WATCHLIST

    def reload(self):
        """重新載入清單（不用重啟服務）"""
        self.data = self._load_watchlist()
        return True

    def get_sectors(self) -> Dict[str, Any]:
        """取得所有產業分類"""
        return self.data.get("sectors", {})

    def get_sector(self, sector_key: str) -> Dict:
        """取得單一產業"""
        return self.data.get("sectors", {}).get(sector_key, {})

    def get_all_stocks(self) -> List[str]:
        """取得所有股票代碼（去重）"""
        all_stocks = []
        for sector in self.data.get("sectors", {}).values():
            all_stocks.extend(sector.get("stocks", []))
        return list(set(all_stocks))

    def get_stock_name(self, symbol: str) -> str:
        """取得股票名稱"""
        return self.data.get("stock_names", {}).get(symbol, symbol)

    def add_stock_to_sector(self, sector_key: str, symbol: str, name: str = None) -> bool:
        """新增股票到產業"""
        if sector_key not in self.data.get("sectors", {}):
            return False
        
        stocks = self.data["sectors"][sector_key].get("stocks", [])
        if symbol not in stocks:
            stocks.append(symbol)
            self.data["sectors"][sector_key]["stocks"] = stocks
            
            if name:
                self.data.setdefault("stock_names", {})[symbol] = name
            
            self._save_watchlist()
            return True
        return False

    def remove_stock_from_sector(self, sector_key: str, symbol: str) -> bool:
        """從產業移除股票"""
        if sector_key not in self.data.get("sectors", {}):
            return False
        
        stocks = self.data["sectors"][sector_key].get("stocks", [])
        if symbol in stocks:
            stocks.remove(symbol)
            self.data["sectors"][sector_key]["stocks"] = stocks
            self._save_watchlist()
            return True
        return False

    def add_sector(self, key: str, name: str, emoji: str = "📊") -> bool:
        """新增產業分類"""
        if key in self.data.get("sectors", {}):
            return False
        
        self.data.setdefault("sectors", {})[key] = {
            "name": name,
            "emoji": emoji,
            "stocks": []
        }
        self._save_watchlist()
        return True

    def _save_watchlist(self):
        """儲存清單到 JSON"""
        try:
            os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
            with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info("✅ 清單已儲存")
        except Exception as e:
            logger.error(f"儲存清單失敗: {e}")

# 全域實例
sniper_watchlist = SniperWatchlistService()
