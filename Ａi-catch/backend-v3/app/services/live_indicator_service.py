"""
盤中即時指標服務 (Live Indicator Service)
基於富邦 API 數據計算實時 VWAP, KD 等指標
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from app.services.fubon_service import get_intraday_data, calculate_vwap

logger = logging.getLogger(__name__)

def get_projected_volume_ratio(current_vol: int, yesterday_vol: int) -> float:
    """
    計算今日預估成交量與昨日總量的比值
    台股交易時間為 270 分鐘 (09:00 - 13:30)
    """
    if yesterday_vol <= 0: return 1.0
    
    now = datetime.now()
    # 這裡假設是在開盤時間內調用。如果不是，限制在 1~270
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    
    if now < market_open:
        return 0.0 # 還沒開盤
        
    elapsed_mins = max(1, min(270, (now - market_open).seconds // 60))
    
    # 預估量 = (目前量 / 已過分鐘) * 270
    projected_vol = (current_vol / elapsed_mins) * 270
    return round(projected_vol / yesterday_vol, 2)

async def get_live_indicators(symbol: str) -> Dict[str, Any]:
    """
    獲取盤中即時指標
    """
    try:
        # 1. 獲取 1 分鐘 K 線數據
        candles = await get_intraday_data(symbol, timeframe="1")
        
        if not candles:
            return {
                "vwap": 0.0,
                "kd_k": 50,
                "kd_d": 50,
                "status": "no_data"
            }
            
        # 2. 計算 VWAP
        vwap = calculate_vwap(candles)
        
        # 3. 計算 KD 指標 (需要 pandas)
        df = pd.DataFrame(candles)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        
        # KD 計算邏輯 (9, 3, 3)
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        
        # 初始化 K, D
        k = 50.0
        d = 50.0
        
        k_list = []
        d_list = []
        
        for i in range(len(df)):
            if pd.isna(rsv[i]):
                k_list.append(50.0)
                d_list.append(50.0)
                continue
                
            k = k * (2/3) + rsv[i] * (1/3)
            d = d * (2/3) + k * (1/3)
            k_list.append(k)
            d_list.append(d)
            
        current_k = round(k_list[-1], 2)
        current_d = round(d_list[-1], 2)
        
        # 4. 判斷 KD 狀態
        kd_status = "neutral"
        if current_k > current_d and k_list[-2] <= d_list[-2]:
            kd_status = "gold_cross"
        elif current_k < current_d and k_list[-2] >= d_list[-2]:
            kd_status = "death_cross"
            
        return {
            "vwap": vwap,
            "kd_k": current_k,
            "kd_d": current_d,
            "kd_status": kd_status,
            "current_price": float(df['close'].iloc[-1]),
            "current_volume": int(df['volume'].sum()),
            "status": "success",
            "data_points": len(df)
        }
        
    except Exception as e:
        logger.error(f"計算盤中指標失敗 {symbol}: {e}")
        return {
            "vwap": 0.0,
            "kd_k": 50,
            "kd_d": 50,
            "status": "error",
            "error": str(e)
        }
