"""
歷史型態辨識引擎 (Historical Pattern Intelligence)
==================================================
【80% 經驗層】：這是我通往 Level 5.0 的核心。不再只依賴即時指標。

本模組負責尋找歷史上高勝率的經典型態：
1. VCP (Volatility Contraction Pattern) - 籌碼高度集中，準備噴發
2. Bull-Back (多頭回測) - 強勢股回測支撐，勝率極高
3. Breakout-Volume (量能突破) - 真正的大戶發動信號
"""

import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class HeritagePatternEngine:
    """歷史型態引擎 - 貢獻 80% 的決策經驗"""

    @staticmethod
    def identify_winning_patterns(ohlc_history: Dict) -> Dict:
        """
        分析歷史 K 線型態，尋找「贏家足跡」
        """
        closes = np.array(ohlc_history.get('closes', []))
        highs  = np.array(ohlc_history.get('highs', []))
        lows   = np.array(ohlc_history.get('lows', []))
        vols   = np.array(ohlc_history.get('volumes', []))

        if len(closes) < 40:
            return {'score': 0, 'patterns': [], 'heritage_rank': 'C'}

        results = []
        pattern_score = 0

        # Pattern 1: VCP (波動收斂) - 經典贏家型態
        # 特徵：近期高低點波動越來越小，代表主力洗盤接近尾聲
        vcp_match = HeritagePatternEngine._check_vcp(highs, lows)
        if vcp_match['matched']:
            pattern_score += 40
            results.append(f"🎯 發現 VCP 緊縮型態 (收斂次數: {vcp_match['counts']})")

        # Pattern 2: Strong Backtest (強勢回測 MA20)
        # 特徵：長期向上，短期回踩不破
        pullback_match = HeritagePatternEngine._check_strong_pullback(closes)
        if pullback_match:
            pattern_score += 30
            results.append("🛡️ 發現史詩級回測支撐 (Strong Bull-Back)")

        # Pattern 3: Accumulation (大戶收集區)
        # 特徵：價格不跌，且量能偶爾爆出（紅長綠短）
        acc_match = HeritagePatternEngine._check_accumulation(closes, vols)
        if acc_match:
            pattern_score += 25
            results.append("💰 發現大戶歷史收集區間 (Accumulation Area)")

        # 根據型態分數決定 Heritage 等級
        if pattern_score >= 60:
            rank = "🏆 AAA (史詩贏家位階)"
        elif pattern_score >= 40:
            rank = "🥇 AA (高勝率歷史位階)"
        elif pattern_score >= 25:
            rank = "🥈 A (穩健位階)"
        else:
            rank = "B (平庸位階)"

        return {
            'score': pattern_score,
            'patterns': results,
            'heritage_rank': rank,
            'is_heritage_winner': pattern_score >= 45
        }

    @staticmethod
    def _check_vcp(highs, lows, period=30):
        """檢查波動收斂 (簡化版)"""
        # 計算最近三個波段的高低差
        ranges = []
        for i in range(3):
            start = -((i+1)*10)
            end = -(i*10) if i > 0 else None
            p_high = np.max(highs[start:end])
            p_low  = np.min(lows[start:end])
            ranges.append(p_high - p_low)
        
        # 如果波動逐次減小 (例如: 10 -> 6 -> 3)
        if ranges[0] < ranges[1] < ranges[2]:
            return {'matched': True, 'counts': 3}
        return {'matched': False, 'counts': 0}

    @staticmethod
    def _check_strong_pullback(closes):
        """檢查強勢回測"""
        ma60 = np.mean(closes[-60:]) if len(closes) >= 60 else np.mean(closes)
        ma20 = np.mean(closes[-20:])
        # 長線向上，短線觸及 MA20 且沒跌破超過 1.5%
        if closes[-1] > ma60 and abs(closes[-1] - ma20) / ma20 < 0.015:
            return True
        return False

    @staticmethod
    def _check_accumulation(closes, vols):
        """檢查大戶收集量能"""
        avg_vol = np.mean(vols[-20:])
        # 最近 5 天有沒有出現 1.5 倍以上的量且收紅
        for i in range(1, 6):
            if vols[-i] > avg_vol * 1.5 and closes[-i] > closes[-i-1]:
                return True
        return False

# 單例
heritage_engine = HeritagePatternEngine()
