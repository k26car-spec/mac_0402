
"""
User Influence Service
允許用戶設定「主觀偏好」來影響 AI 評分系統的結果
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

USER_INFLUENCE_FILE = os.path.join(
    os.path.dirname(__file__), 
    "../../../data/user_influence.json"
)

DEFAULT_INFLUENCE = {
    "global_bias": 0,           # 全局加分/扣分 (-20 to +20)
    "risk_appetite": "neutral", # aggressive, neutral, conservative
    "favored_sectors": [],      # 偏好產業
    "stock_bias": {},           # 特定股票的偏好 {symbol: score_bias}
    "custom_supports": {},      # 用戶自定義支撐 {symbol: [price1, price2]}
    "custom_resistances": {},   # 用戶自定義壓力
    "narrative_insight": ""     # 用戶的主觀觀點 (影響文字分析)
}

class UserInfluenceService:
    def __init__(self):
        self.influence = self._load_influence()
        
    def _load_influence(self) -> Dict:
        if os.path.exists(USER_INFLUENCE_FILE):
            try:
                with open(USER_INFLUENCE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load user influence: {e}")
        return DEFAULT_INFLUENCE.copy()

    def save_influence(self):
        try:
            os.makedirs(os.path.dirname(USER_INFLUENCE_FILE), exist_ok=True)
            with open(USER_INFLUENCE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.influence, f, ensure_ascii=False, indent=2)
            logger.info("Successfully saved user influence")
        except Exception as e:
            logger.error(f"Failed to save user influence: {e}")

    def set_global_bias(self, bias: int):
        self.influence["global_bias"] = max(-30, min(30, bias))
        self.save_influence()

    def set_stock_bias(self, symbol: str, bias: int):
        self.influence["stock_bias"][symbol] = bias
        self.save_influence()
        
    def set_custom_support(self, symbol: str, price: float):
        if symbol not in self.influence["custom_supports"]:
            self.influence["custom_supports"][symbol] = []
        if price not in self.influence["custom_supports"][symbol]:
            self.influence["custom_supports"][symbol].append(price)
            self.save_influence()

    def get_bias_for_stock(self, symbol: str) -> int:
        bias = self.influence.get("global_bias", 0)
        bias += self.influence.get("stock_bias", {}).get(symbol, 0)
        
        # 根據風險偏好調整
        appetite = self.influence.get("risk_appetite", "neutral")
        if appetite == "aggressive":
            bias += 10
        elif appetite == "conservative":
            bias -= 10
            
        return bias

    def get_custom_levels(self, symbol: str) -> Dict[str, List[float]]:
        return {
            "supports": self.influence.get("custom_supports", {}).get(symbol, []),
            "resistances": self.influence.get("custom_resistances", {}).get(symbol, [])
        }

    def set_narrative(self, text: str):
        self.influence["narrative_insight"] = text
        self.save_influence()

influence_service = UserInfluenceService()
