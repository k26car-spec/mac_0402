"""
ATR 動態停損計算器 (ATR Dynamic Stop Loss)
==========================================
核心邏輯: 「根據個股性格(波動度)動態設定停損距離，
          不讓溫吞股太鬆、不讓火爆股太窄而洗掉」

公式:
  ATR(14) = 過去14日的「真實波幅」平均
  停損距離 = ATR × 1.5
  目標距離 = ATR × 2.5  (風報比至少 1.7:1)

分級:
  ATR% <= 2%  → 低波動 (金融/電信等)
  ATR% 2-4%  → 中波動 (一般科技股)
  ATR% > 4%  → 高波動 (題材股/小型股)
"""

import logging
from typing import Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


def calculate_atr(
    highs: list,
    lows: list,
    closes: list,
    period: int = 14
) -> float:
    """
    計算 ATR (Average True Range)

    True Range = max(H-L, |H-prevC|, |L-prevC|)
    ATR = SMA(TR, period)
    """
    if len(highs) < period + 1:
        return 0.0

    trs = []
    for i in range(1, len(highs)):
        h, l, prev_c = highs[i], lows[i], closes[i - 1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)

    if len(trs) < period:
        return float(np.mean(trs)) if trs else 0.0

    return float(np.mean(trs[-period:]))


def get_atr_stop_levels(
    price: float,
    highs: list,
    lows: list,
    closes: list,
    atr_period: int = 14,
    sl_multiplier: float = 1.5,
    tp_multiplier: float = 2.5,
    entry_type: str = "long"
) -> Dict:
    """
    根據 ATR 計算動態停損與停利價位。

    Args:
        price:          當前進場價
        highs/lows/closes: 歷史 OHLC 資料（日 K 或 5 分 K）
        atr_period:     ATR 計算週期（預設 14）
        sl_multiplier:  停損倍率（預設 1.5 ATR）
        tp_multiplier:  停利倍率（預設 2.5 ATR，風報比約 1.7:1）
        entry_type:     'long' 做多 / 'short' 做空

    Returns:
        {
            'atr': float,
            'atr_pct': float,       # ATR 佔股價的百分比
            'volatility_grade': str,  # 'LOW' / 'MID' / 'HIGH'
            'stop_loss': float,
            'target': float,
            'sl_distance_pct': float,
            'tp_distance_pct': float,
            'risk_reward': float,
            'note': str
        }
    """
    atr = calculate_atr(highs, lows, closes, atr_period)

    # ATR 不可靠時回退為固定比例
    if atr <= 0 or price <= 0:
        fallback_sl = round(price * 0.93, 2)
        fallback_tp = round(price * 1.10, 2)
        return {
            'atr': 0.0,
            'atr_pct': 0.0,
            'volatility_grade': 'UNKNOWN',
            'stop_loss': fallback_sl,
            'target': fallback_tp,
            'sl_distance_pct': 7.0,
            'tp_distance_pct': 10.0,
            'risk_reward': 1.43,
            'note': 'ATR 資料不足，使用固定 7%/10% 備援'
        }

    atr_pct = (atr / price) * 100

    # 根據波動度分級調整倍率
    if atr_pct <= 2.0:
        grade = 'LOW'
        sl_mult = sl_multiplier * 1.0    # 低波動保持 1.5x
        tp_mult = tp_multiplier * 0.9    # 稍微收緊目標
        note = f"低波動股 ATR={atr:.2f}({atr_pct:.1f}%)，停損較緊"
    elif atr_pct <= 4.0:
        grade = 'MID'
        sl_mult = sl_multiplier * 1.0
        tp_mult = tp_multiplier * 1.0
        note = f"中波動股 ATR={atr:.2f}({atr_pct:.1f}%)，標準停損"
    else:
        grade = 'HIGH'
        sl_mult = sl_multiplier * 1.3    # 高波動放寬停損，避免被洗掉
        tp_mult = tp_multiplier * 1.2
        note = f"高波動股 ATR={atr:.2f}({atr_pct:.1f}%)，停損放寬防洗盤"

    sl_distance = atr * sl_mult
    tp_distance = atr * tp_mult

    if entry_type == "long":
        stop_loss = round(price - sl_distance, 2)
        target    = round(price + tp_distance, 2)
    else:
        stop_loss = round(price + sl_distance, 2)
        target    = round(price - tp_distance, 2)

    sl_pct = (sl_distance / price) * 100
    tp_pct = (tp_distance / price) * 100
    risk_reward = round(tp_pct / sl_pct, 2) if sl_pct > 0 else 0

    logger.info(
        f"[ATR停損] 進場${price:.2f} | ATR={atr:.2f}({atr_pct:.1f}%) "
        f"| SL=${stop_loss:.2f}(-{sl_pct:.1f}%) "
        f"| TP=${target:.2f}(+{tp_pct:.1f}%) "
        f"| 風報比={risk_reward}"
    )

    return {
        'atr': round(atr, 2),
        'atr_pct': round(atr_pct, 2),
        'volatility_grade': grade,
        'stop_loss': stop_loss,
        'target': target,
        'sl_distance_pct': round(sl_pct, 2),
        'tp_distance_pct': round(tp_pct, 2),
        'risk_reward': risk_reward,
        'note': note
    }


async def get_atr_levels_from_symbol(
    symbol: str,
    current_price: float,
    period: int = 14
) -> Dict:
    """
    直接傳入股票代號，自動用 yfinance 獲取歷史 OHLC 並計算 ATR 停損。
    供 SmartEntrySystem.evaluate_stock() 呼叫。
    """
    try:
        import yfinance as yf
        import pandas as pd

        # 優先嘗試上市 (.TW)
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="30d")
        if hist.empty:
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="30d")

        if hist.empty or len(hist) < period + 1:
            raise ValueError("資料不足")

        highs  = hist['High'].tolist()
        lows   = hist['Low'].tolist()
        closes = hist['Close'].tolist()

        return get_atr_stop_levels(
            price=current_price,
            highs=highs,
            lows=lows,
            closes=closes,
            atr_period=period
        )

    except Exception as e:
        logger.warning(f"[ATR] {symbol} 無法取得歷史數據: {e}，使用固定備援")
        return get_atr_stop_levels(
            price=current_price,
            highs=[],
            lows=[],
            closes=[],
            atr_period=period
        )
