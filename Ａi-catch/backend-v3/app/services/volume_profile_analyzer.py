"""
Volume Profile 籌碼分析服務
透過分析歷史成交量分布，找出：
- POC (Point of Control): 成交量最大的價位
- VAH (Value Area High): 價值區上緣 (大量壓力)
- VAL (Value Area Low): 價值區下緣 (大量支撐)
- 籌碼密集區
"""

import yfinance as yf
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class VolumeProfileAnalyzer:
    """籌碼分析與 Volume Profile 計算"""
    
    def __init__(self):
        self.price_buckets = 50  # 價格分區數量
        self.value_area_pct = 0.70  # 價值區包含 70% 的成交量
    
    async def analyze(self, stock_code: str, period: str = "3mo") -> Optional[Dict[str, Any]]:
        """
        分析股票的籌碼分布
        
        Args:
            stock_code: 股票代碼
            period: 分析期間 (1mo, 3mo, 6mo)
        
        Returns:
            籌碼分析結果
        """
        try:
            # 取得歷史數據
            hist = await self._get_history(stock_code, period)
            if hist is None or len(hist) < 20:
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            
            # 計算 Volume Profile
            profile = self._calculate_volume_profile(hist)
            
            # 計算 POC 和 Value Area
            poc = self._find_poc(profile)
            vah, val = self._find_value_area(profile)
            
            # 找出籌碼密集區
            high_volume_zones = self._find_high_volume_zones(profile, current_price)
            
            # 判斷籌碼位置
            position_analysis = self._analyze_position(current_price, poc, vah, val)
            
            return {
                "stock_code": stock_code,
                "current_price": current_price,
                "period": period,
                "timestamp": datetime.now().isoformat(),
                
                # Volume Profile 核心數據
                "poc": {
                    "price": poc["price"],
                    "volume": poc["volume"],
                    "description": "成交量最大價位 (Point of Control)",
                    "distance_pct": round((current_price - poc["price"]) / poc["price"] * 100, 2)
                },
                
                # 價值區
                "value_area": {
                    "high": vah,  # 大量壓力
                    "low": val,   # 大量支撐
                    "range_pct": round((vah - val) / val * 100, 2),
                    "description": f"70% 成交量集中區間: {val:.2f} ~ {vah:.2f}"
                },
                
                # 大量壓力/支撐
                "major_resistance": {
                    "price": vah,
                    "description": "上方大量壓力 (Value Area High)",
                    "distance_pct": round((vah - current_price) / current_price * 100, 2) if vah > current_price else 0
                },
                "major_support": {
                    "price": val,
                    "description": "下方大量支撐 (Value Area Low)",
                    "distance_pct": round((current_price - val) / current_price * 100, 2) if val < current_price else 0
                },
                
                # 籌碼密集區
                "high_volume_zones": high_volume_zones,
                
                # 位置分析
                "position_analysis": position_analysis,
                
                # Volume Profile 分布 (用於圖表)
                "profile_distribution": [
                    {
                        "price_low": float(row["price_low"]),
                        "price_high": float(row["price_high"]),
                        "volume": int(row["volume"]),
                        "volume_pct": round(row["volume_pct"], 2),
                        "is_poc": row.get("is_poc", False),
                        "in_value_area": row.get("in_value_area", False)
                    }
                    for row in profile[:20]  # 只返回前 20 個區間
                ]
            }
            
        except Exception as e:
            logger.error(f"Volume Profile 分析失敗 {stock_code}: {e}")
            return None
    
    async def _get_history(self, stock_code: str, period: str) -> Optional[Any]:
        """取得歷史數據"""
        try:
            # 嘗試上市
            ticker = yf.Ticker(f"{stock_code}.TW")
            hist = ticker.history(period=period)
            
            if hist.empty:
                # 嘗試上櫃
                ticker = yf.Ticker(f"{stock_code}.TWO")
                hist = ticker.history(period=period)
            
            return hist if not hist.empty else None
            
        except Exception as e:
            logger.error(f"取得歷史數據失敗: {e}")
            return None
    
    def _calculate_volume_profile(self, hist) -> List[Dict]:
        """
        計算 Volume Profile
        將價格範圍分成多個區間，統計每個區間的成交量
        """
        # 取得價格範圍
        high_prices = hist['High'].values
        low_prices = hist['Low'].values
        close_prices = hist['Close'].values
        volumes = hist['Volume'].values
        
        price_min = float(np.min(low_prices))
        price_max = float(np.max(high_prices))
        
        # 創建價格區間
        bucket_size = (price_max - price_min) / self.price_buckets
        buckets = []
        
        for i in range(self.price_buckets):
            bucket_low = price_min + i * bucket_size
            bucket_high = price_min + (i + 1) * bucket_size
            buckets.append({
                "price_low": bucket_low,
                "price_high": bucket_high,
                "price_mid": (bucket_low + bucket_high) / 2,
                "volume": 0
            })
        
        # 分配成交量到各區間
        total_volume = 0
        for idx in range(len(hist)):
            day_high = high_prices[idx]
            day_low = low_prices[idx]
            day_volume = volumes[idx]
            
            # 找出該日價格涵蓋的區間
            covered_buckets = []
            for bucket in buckets:
                if bucket["price_high"] >= day_low and bucket["price_low"] <= day_high:
                    covered_buckets.append(bucket)
            
            # 平均分配成交量
            if covered_buckets:
                vol_per_bucket = day_volume / len(covered_buckets)
                for bucket in covered_buckets:
                    bucket["volume"] += vol_per_bucket
                    total_volume += vol_per_bucket
        
        # 計算百分比並排序
        for bucket in buckets:
            bucket["volume_pct"] = (bucket["volume"] / total_volume * 100) if total_volume > 0 else 0
        
        # 按成交量排序 (從大到小)
        buckets.sort(key=lambda x: x["volume"], reverse=True)
        
        return buckets
    
    def _find_poc(self, profile: List[Dict]) -> Dict:
        """找出 POC (成交量最大的價位)"""
        if not profile:
            return {"price": 0, "volume": 0}
        
        poc_bucket = profile[0]  # 已經按成交量排序
        poc_bucket["is_poc"] = True
        
        return {
            "price": poc_bucket["price_mid"],
            "volume": int(poc_bucket["volume"])
        }
    
    def _find_value_area(self, profile: List[Dict]) -> tuple:
        """
        找出價值區 (Value Area)
        包含 70% 成交量的價格區間
        """
        if not profile:
            return (0, 0)
        
        total_volume = sum(b["volume"] for b in profile)
        target_volume = total_volume * self.value_area_pct
        
        # 從 POC 開始向兩側擴展
        cumulative_volume = 0
        value_area_buckets = []
        
        for bucket in profile:  # 已按成交量排序
            cumulative_volume += bucket["volume"]
            bucket["in_value_area"] = True
            value_area_buckets.append(bucket)
            
            if cumulative_volume >= target_volume:
                break
        
        # 找出價值區的上下限
        prices = [b["price_mid"] for b in value_area_buckets]
        vah = max(prices) if prices else 0
        val = min(prices) if prices else 0
        
        return (vah, val)
    
    def _find_high_volume_zones(self, profile: List[Dict], current_price: float) -> List[Dict]:
        """找出籌碼密集區"""
        zones = []
        
        # 取成交量前 5 大的區間
        top_buckets = profile[:5]
        
        for bucket in top_buckets:
            price = bucket["price_mid"]
            zone_type = "resistance" if price > current_price else "support"
            distance_pct = (price - current_price) / current_price * 100
            
            zones.append({
                "price": round(price, 2),
                "volume": int(bucket["volume"]),
                "volume_pct": round(bucket["volume_pct"], 2),
                "type": zone_type,
                "distance_pct": round(distance_pct, 2),
                "description": f"籌碼密集區 ({bucket['volume_pct']:.1f}% 成交量)"
            })
        
        # 按價格排序
        zones.sort(key=lambda x: x["price"], reverse=True)
        
        return zones
    
    def _analyze_position(self, current_price: float, poc: Dict, vah: float, val: float) -> Dict:
        """分析當前價格相對於籌碼分布的位置"""
        poc_price = poc["price"]
        
        if current_price > vah:
            position = "above_value_area"
            status = "突破籌碼壓力區"
            description = "股價站上大量成交區，上方無壓，有利多頭發展"
            signal = "bullish"
        elif current_price < val:
            position = "below_value_area"
            status = "跌破籌碼支撐區"
            description = "股價跌破大量成交區，原支撐轉為壓力，偏空"
            signal = "bearish"
        elif current_price > poc_price:
            position = "upper_value_area"
            status = "價值區上半部"
            description = "接近上方籌碼壓力，注意是否能突破"
            signal = "neutral_bullish"
        else:
            position = "lower_value_area"
            status = "價值區下半部"
            description = "接近下方籌碼支撐，留意支撐力道"
            signal = "neutral_bearish"
        
        return {
            "position": position,
            "status": status,
            "description": description,
            "signal": signal,
            "above_poc": current_price > poc_price,
            "in_value_area": val <= current_price <= vah
        }


# 全局實例
volume_profile_analyzer = VolumeProfileAnalyzer()
