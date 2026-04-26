"""
盤口微觀智商 (Order Book Micro-Intelligence)
=============================================
邁向 Level 4.5 的關鍵：識別大戶「掛單意向」。

K 線是歷史，盤口是未來。
本模組解析 Bid/Ask (買賣五檔) 的量能失衡與分布，判斷當前是「真突破」還是「假誘多」。
"""

import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class OrderBookIntelligence:
    """盤口微觀智商分析器"""

    @staticmethod
    def analyze_imbalance(bids: List[Dict], asks: List[Dict]) -> Dict:
        """
        分析買賣五檔失衡度
        bids/asks 格式: [{'price': float, 'volume': int}, ...]
        """
        if not bids or not asks:
            return {'imbalance_ratio': 1.0, 'score_adj': 0, 'bias': 'Neutral'}

        # 1. 總量計算
        total_bid_vol = sum(b.get('volume', 0) for b in bids)
        total_ask_vol = sum(a.get('volume', 0) for a in asks)
        
        if total_ask_vol == 0: return {'score_adj': 10, 'bias': 'Bullish'}
        
        ratio = total_bid_vol / total_ask_vol

        # 2. 深度偏向 (靠近現價的權重較高)
        # 第一檔權重 40%, 第二檔 25%, ... 越遠權重越低
        weights = [0.4, 0.25, 0.15, 0.1, 0.1]
        weighted_bid = sum(b.get('volume', 0) * w for b, w in zip(bids, weights))
        weighted_ask = sum(a.get('volume', 0) * w for a, w in zip(asks, weights))
        
        weighted_ratio = weighted_bid / weighted_ask if weighted_ask > 0 else 2.0

        # 3. 判斷大戶是否存在 (單筆特大掛單)
        max_bid_single = max(b.get('volume', 0) for b in bids)
        avg_bid_vol = total_bid_vol / len(bids)
        whale_floor = max_bid_single > avg_bid_vol * 2.5 # 有大單墊著

        # 4. 決策邏輯
        score_adj = 0
        bias = "Neutral"
        reasons = []

        if weighted_ratio > 1.8:
            score_adj = 15
            bias = "Bullish (買盤強勁)"
            reasons.append(f"盤口底氣足 (weighted_ratio={weighted_ratio:.1f})")
        elif weighted_ratio > 1.3:
            score_adj = 7
            bias = "Slightly Bullish"
        elif weighted_ratio < 0.5:
            score_adj = -15
            bias = "Bearish (賣壓沉重)"
            reasons.append("上方壓力山大")
        elif weighted_ratio < 0.7:
            score_adj = -7
            bias = "Slightly Bearish"

        if whale_floor and weighted_ratio > 1.0:
            score_adj += 5
            reasons.append("偵測到大戶墊單 (Whale Floor Detected)")

        return {
            'weighted_ratio': round(weighted_ratio, 2),
            'total_bid': total_bid_vol,
            'total_ask': total_ask_vol,
            'score_adj': score_adj,
            'bias': bias,
            'reasons': reasons
        }

# 單例
order_book_intel = OrderBookIntelligence()
