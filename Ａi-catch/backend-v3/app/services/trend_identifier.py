"""
趨勢標的分辨器 (Trend Stock Identifier)
========================================
「順勢而為，事半功倍」

本模組專門識別處於「強勢多頭趨勢」的標的。
趨勢股特徵：
  1. 均線多頭排列 (MA5 > MA20 > MA60)
  2. ADX 趨勢強度 > 25
  3. 價格站穩在長天期均線之上
  4. 乖離率適中（未過度噴發）
"""

import logging
import asyncio
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class TrendIdentifier:
    """趨勢標的分辨器"""

    @staticmethod
    def identify_trend(ohlc_data: Dict) -> Dict:
        """
        根據歷史 OHLC 數據分辨趨勢等級。
        
        ohlc_data 應包含: 'closes', 'highs', 'lows', 'volumes' (至少 60 筆)
        """
        closes = np.array(ohlc_data.get('closes', []))
        highs  = np.array(ohlc_data.get('highs', []))
        lows   = np.array(ohlc_data.get('lows', []))
        
        if len(closes) < 30: # 降低門檻至 30 筆（MA60 用前幾天填充）
            return {
                'grade': 'N/A', 
                'label': '數據不足', 
                'score': 0, 
                'reasons': ['數據量不足 30 筆'],
                'is_trend_stock': False
            }

        # 1. 計算均線
        ma5  = np.mean(closes[-5:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:])
        current = closes[-1]

        # 2. 判斷多頭排列 (Bullish Alignment)
        is_bull_aligned = current > ma5 > ma20 > ma60
        
        # 3. 計算 ADX (趨勢強度)
        adx = TrendIdentifier._calc_adx(highs, lows, closes)
        
        # 4. 計算近期斜率 (Price Momentum)
        recent_10 = closes[-10:]
        slope = np.polyfit(range(len(recent_10)), recent_10, 1)[0]
        slope_pct = (slope / ma20) * 100 # 斜率佔股價比

        # 5. 趨勢打分
        trend_score = 0
        reasons = []

        # 均線分
        if is_bull_aligned:
            trend_score += 40
            reasons.append("均線完美多頭排列")
        elif current > ma20 > ma60:
            trend_score += 25
            reasons.append("中長期支撐穩固")
        
        # 強度分 (ADX)
        if adx > 35:
            trend_score += 30
            reasons.append(f"強勢趨勢 (ADX={adx:.1f})")
        elif adx > 25:
            trend_score += 15
            reasons.append(f"趨勢成形 (ADX={adx:.1f})")
        
        # 斜率分
        if slope_pct > 0.5:
            trend_score += 20
            reasons.append("價格斜率向上")
        
        # 乖離檢查 (防止過熱)
        deviation = (current - ma20) / ma20 * 100
        if deviation > 15:
            trend_score -= 20
            reasons.append(f"注意！乖離過大({deviation:.1f}%)")

        # 6. 分級
        if trend_score >= 80:
            grade = "AAA"  # 極強趨勢股
            label = "🔥 超強趨勢"
        elif trend_score >= 60:
            grade = "AA"   # 穩定趨勢股
            label = "📈 穩定趨勢"
        elif trend_score >= 40:
            grade = "A"    # 潛力趨勢股
            label = "⭐ 趨勢萌芽"
        else:
            grade = "B"    # 無明顯趨勢
            label = "⚖️ 區間/無感"

        return {
            'symbol': ohlc_data.get('symbol', ''),
            'grade': grade,
            'label': label,
            'score': trend_score,
            'adx': round(adx, 2),
            'ma_alignment': "BULL" if is_bull_aligned else "MIXED",
            'deviation_20': round(deviation, 2),
            'reasons': reasons,
            'is_trend_stock': trend_score >= 60
        }

    @staticmethod
    def _calc_adx(highs, lows, closes, period=14):
        """計算 ADX"""
        if len(closes) < period * 2: return 0
        
        tr_arr = []
        for i in range(1, len(closes)):
            tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
            tr_arr.append(tr)
            
        dm_p, dm_m = [], []
        for i in range(1, len(highs)):
            up = highs[i] - highs[i-1]
            dn = lows[i-1] - lows[i]
            dm_p.append(up if up > dn and up > 0 else 0)
            dm_m.append(dn if dn > up and dn > 0 else 0)
            
        tr_s = pd.Series(tr_arr).rolling(period).mean().iloc[-1]
        dm_p_s = pd.Series(dm_p).rolling(period).mean().iloc[-1]
        dm_m_s = pd.Series(dm_m).rolling(period).mean().iloc[-1]
        
        if tr_s == 0: return 0
        di_p = dm_p_s / tr_s * 100
        di_m = dm_m_s / tr_s * 100
        
        if (di_p + di_m) == 0: return 0
        dx = abs(di_p - di_m) / (di_p + di_m) * 100
        return dx

# 單例
trend_identifier = TrendIdentifier()
