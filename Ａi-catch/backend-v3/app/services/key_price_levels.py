"""
關鍵價位矩陣 (Key Price Level Matrix)
======================================
核心邏輯: 「聰明的進場點不是買在任意突破，
          而是買在突破確認後的回測支撐」

計算並追蹤以下關鍵價位：
  - PDH (Previous Day High): 昨日最高
  - PDL (Previous Day Low):  昨日最低
  - PDC (Previous Day Close): 昨日收盤
  - Today Open: 今日開盤
  - R1/S1: 日內樞軸支撐壓力 (Pivot Point)
  - 近 5 日高低點聚集帶

進場品質矩陣:
  IDEAL:   突破 PDH 後回測昨高支撐 (強勢確認)
  GOOD:    突破 Today Open R1 後支撐 (一般確認)
  POOR:    在 PDH 壓力下方硬進 (高風險)
  BLOCK:   在 PDL 以下 (不進)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 快取：避免重複查詢
_key_level_cache: Dict[str, Dict] = {}
_key_level_cache_time: Dict[str, datetime] = {}
_CACHE_TTL = 600  # 10 分鐘快取（日 K 不常變）


def calculate_pivot(
    prev_high: float,
    prev_low: float,
    prev_close: float
) -> Dict[str, float]:
    """
    計算樞軸點 (Classic Pivot Points)
    
    PP = (H + L + C) / 3
    R1 = 2×PP - L    S1 = 2×PP - H
    R2 = PP + (H-L)  S2 = PP - (H-L)
    """
    if prev_high <= 0 or prev_low <= 0 or prev_close <= 0:
        return {}

    pp = (prev_high + prev_low + prev_close) / 3
    r1 = 2 * pp - prev_low
    s1 = 2 * pp - prev_high
    r2 = pp + (prev_high - prev_low)
    s2 = pp - (prev_high - prev_low)

    return {
        'PP': round(pp, 2),
        'R1': round(r1, 2),
        'R2': round(r2, 2),
        'S1': round(s1, 2),
        'S2': round(s2, 2),
    }


def evaluate_entry_position(
    current_price: float,
    today_open: float,
    pdh: float,   # Previous Day High
    pdl: float,   # Previous Day Low
    pdc: float,   # Previous Day Close
    pivots: Dict[str, float],
    tolerance_pct: float = 1.0  # 允許的誤差範圍（%）
) -> Dict:
    """
    評估當前價格在關鍵價位矩陣中的進場品質。

    Returns:
        {
            'quality': 'IDEAL' | 'GOOD' | 'NEUTRAL' | 'POOR' | 'BLOCK',
            'score_adj': int,   # 信心度調整
            'allow': bool,
            'reason': str,
            'nearby_resistance': float,  # 最近壓力位
            'nearby_support': float,     # 最近支撐位
            'levels': Dict               # 所有關鍵價位
        }
    """
    if current_price <= 0 or pdh <= 0:
        return {
            'quality': 'NEUTRAL',
            'score_adj': 0,
            'allow': True,
            'reason': '關鍵價位數據不足，不過濾',
            'nearby_resistance': 0,
            'nearby_support': 0,
            'levels': {}
        }

    tol = current_price * tolerance_pct / 100

    # ============================================================
    # 1. 最佳進場：突破昨高 PDH 之後（IDEAL）
    #    → 股價站上 PDH，且距離 PDH 在 1% 以內（剛突破，未追高）
    # ============================================================
    if current_price > pdh and (current_price - pdh) <= tol:
        return {
            'quality': 'IDEAL',
            'score_adj': 15,
            'allow': True,
            'reason': f'✅ 完美進場：剛突破昨高 PDH={pdh:.2f} (距離 {((current_price-pdh)/pdh*100):.1f}%)',
            'nearby_resistance': pivots.get('R1', pdh * 1.02),
            'nearby_support': pdh,
            'levels': {'PDH': pdh, 'PDL': pdl, 'PDC': pdc, **pivots}
        }

    # ============================================================
    # 2. 良好進場：突破 Pivot R1（GOOD）
    # ============================================================
    r1 = pivots.get('R1', 0)
    if r1 > 0 and current_price > r1 and (current_price - r1) <= tol:
        return {
            'quality': 'GOOD',
            'score_adj': 8,
            'allow': True,
            'reason': f'⭐ 良好進場：突破樞軸 R1={r1:.2f}',
            'nearby_resistance': pivots.get('R2', r1 * 1.02),
            'nearby_support': pivots.get('PP', r1 * 0.99),
            'levels': {'PDH': pdh, 'PDL': pdl, 'PDC': pdc, **pivots}
        }

    # ============================================================
    # 3. 在 PDH 下方、高風險壓力帶（POOR）
    #    → 距離 PDH 在 2% 以內，即將碰壓力
    # ============================================================
    if pdh > 0 and current_price < pdh and (pdh - current_price) <= 2 * tol:
        return {
            'quality': 'POOR',
            'score_adj': -10,
            'allow': True,  # 允許進場但扣分
            'reason': f'⚠️ 緊靠壓力：距昨高 PDH={pdh:.2f} 僅 {((pdh-current_price)/pdh*100):.1f}%，進場品質差',
            'nearby_resistance': pdh,
            'nearby_support': pivots.get('PP', pdc),
            'levels': {'PDH': pdh, 'PDL': pdl, 'PDC': pdc, **pivots}
        }

    # ============================================================
    # 4. 跌破昨低 PDL（BLOCK）→直接阻擋
    # ============================================================
    if current_price < pdl:
        return {
            'quality': 'BLOCK',
            'score_adj': -30,
            'allow': False,
            'reason': f'🚫 跌破昨低 PDL={pdl:.2f}，絕對不進場',
            'nearby_resistance': pdl,
            'nearby_support': pivots.get('S1', pdl * 0.98),
            'levels': {'PDH': pdh, 'PDL': pdl, 'PDC': pdc, **pivots}
        }

    # ============================================================
    # 5. 中性（NEUTRAL）
    # ============================================================
    return {
        'quality': 'NEUTRAL',
        'score_adj': 0,
        'allow': True,
        'reason': f'⚖️ 中性位置 (PDH={pdh:.2f} | PDL={pdl:.2f})',
        'nearby_resistance': pdh,
        'nearby_support': pdl,
        'levels': {'PDH': pdh, 'PDL': pdl, 'PDC': pdc, **pivots}
    }


async def get_key_levels(symbol: str, current_price: float) -> Dict:
    """
    取得個股完整關鍵價位矩陣，並評估當前進場品質。
    供 SmartEntrySystem 呼叫。
    """
    now = datetime.now()

    # 快取命中
    if symbol in _key_level_cache and symbol in _key_level_cache_time:
        elapsed = (now - _key_level_cache_time[symbol]).total_seconds()
        if elapsed < _CACHE_TTL:
            cached = _key_level_cache[symbol].copy()
            # 更新進場品質評估（因為 current_price 可能已變）
            cached['entry_quality'] = evaluate_entry_position(
                current_price,
                cached.get('today_open', 0),
                cached.get('pdh', 0),
                cached.get('pdl', 0),
                cached.get('pdc', 0),
                cached.get('pivots', {})
            )
            return cached

    try:
        import yfinance as yf

        # 取 3 天日 K（確保有昨日和前日數據，考慮非交易日）
        for suffix in [".TW", ".TWO"]:
            ticker = yf.Ticker(f"{symbol}{suffix}")
            hist = ticker.history(period="5d")
            if not hist.empty and len(hist) >= 2:
                break
        else:
            raise ValueError(f"{symbol} 日 K 數據不足")

        # 最新一筆為「今日」或「最近交易日」
        pdh = float(hist['High'].iloc[-2])
        pdl = float(hist['Low'].iloc[-2])
        pdc = float(hist['Close'].iloc[-2])

        # 今日開盤
        today_open = float(hist['Open'].iloc[-1]) if len(hist) >= 1 else current_price

        pivots = calculate_pivot(pdh, pdl, pdc)

        entry_quality = evaluate_entry_position(
            current_price, today_open, pdh, pdl, pdc, pivots
        )

        result = {
            'symbol': symbol,
            'pdh': pdh,
            'pdl': pdl,
            'pdc': pdc,
            'today_open': today_open,
            'pivots': pivots,
            'entry_quality': entry_quality,
            'timestamp': now.isoformat()
        }

        _key_level_cache[symbol] = result
        _key_level_cache_time[symbol] = now

        logger.info(
            f"[關鍵價位] {symbol} PDH={pdh:.2f} PDL={pdl:.2f} "
            f"Open={today_open:.2f} | 進場品質: {entry_quality['quality']}"
        )
        return result

    except Exception as e:
        logger.warning(f"[關鍵價位] {symbol} 取得失敗: {e}")
        return {
            'symbol': symbol,
            'pdh': 0, 'pdl': 0, 'pdc': 0,
            'today_open': current_price,
            'pivots': {},
            'entry_quality': {
                'quality': 'NEUTRAL', 'score_adj': 0,
                'allow': True, 'reason': '關鍵價位取得失敗，不過濾',
                'nearby_resistance': 0, 'nearby_support': 0, 'levels': {}
            },
            'timestamp': now.isoformat()
        }
