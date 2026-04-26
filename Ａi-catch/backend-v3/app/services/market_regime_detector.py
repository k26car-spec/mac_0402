"""
市場機制偵測器 (Market Regime Detector)
========================================
「聰明的操盤手知道現在市場在什麼『狀態』，
 然後選擇對應的策略，而不是用同一個策略打天下。」

市場機制分類：
  TRENDING_UP    → 趨勢多頭（適合追漲動能策略）
  TRENDING_DOWN  → 趨勢空頭（禁止做多，等反彈）
  RANGING        → 高檔盤整（適合區間高賣低買）
  VOLATILE       → 高波動震盪（降低倉位，等待明確）
  BREAKOUT       → 突破行情（最佳進場時機）

每個機制對應：
  - 允許的策略清單
  - 信心度門檻調整
  - 建議倉位比例
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# 快取
_regime_cache: Optional[Dict] = None
_regime_cache_time: Optional[datetime] = None
_CACHE_TTL = 300  # 5 分鐘


def _calc_adx(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """計算 ADX 趨勢強度指標 (0~100, > 25 = 有趨勢)"""
    if len(closes) < period + 2:
        return 0.0

    h = np.array(highs)
    l = np.array(lows)
    c = np.array(closes)

    # True Range
    tr_arr = []
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
        tr_arr.append(tr)

    # Directional Movement
    dm_plus, dm_minus = [], []
    for i in range(1, len(h)):
        up   = h[i] - h[i-1]
        down = l[i-1] - l[i]
        dm_plus.append(up   if up > down and up > 0 else 0)
        dm_minus.append(down if down > up and down > 0 else 0)

    tr_arr   = np.array(tr_arr[-period*2:])
    dm_plus  = np.array(dm_plus[-period*2:])
    dm_minus = np.array(dm_minus[-period*2:])

    atr14 = np.mean(tr_arr[-period:]) if len(tr_arr) >= period else np.mean(tr_arr)
    if atr14 == 0:
        return 0.0

    di_plus  = np.mean(dm_plus[-period:]) / atr14 * 100
    di_minus = np.mean(dm_minus[-period:]) / atr14 * 100
    di_sum   = di_plus + di_minus
    if di_sum == 0:
        return 0.0

    dx = abs(di_plus - di_minus) / di_sum * 100
    return round(float(dx), 2)


def _calc_atr_pct(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """計算近期 ATR 佔股價的百分比（代表波動率）"""
    if len(closes) < period + 1:
        return 2.0

    trs = []
    h, l, c = np.array(highs), np.array(lows), np.array(closes)
    for i in range(1, len(c)):
        trs.append(max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])))

    atr = np.mean(trs[-period:]) if len(trs) >= period else np.mean(trs)
    return round(float(atr / c[-1] * 100), 2)


async def detect_market_regime(
    symbol: str = "^TWII",
    use_cache: bool = True
) -> Dict:
    """
    偵測台股大盤（或指定標的）當前所處的市場機制。

    Returns:
        {
            'regime': str,            # 機制名稱
            'regime_cn': str,         # 中文名稱
            'adx': float,             # 趨勢強度 (>25=有趨勢)
            'volatility_pct': float,  # 波動率
            'trend_dir': str,         # 'UP'/'DOWN'/'FLAT'
            'allowed_strategies': list,
            'confidence_adj': int,    # 信心度調整
            'position_scale': float,  # 倉位縮放 (1.0=正常, 0.5=減半)
            'suggestion': str
        }
    """
    global _regime_cache, _regime_cache_time

    if use_cache and _regime_cache and _regime_cache_time:
        elapsed = (datetime.now() - _regime_cache_time).total_seconds()
        if elapsed < _CACHE_TTL:
            return _regime_cache

    try:
        import yfinance as yf

        ticker_sym = "^TWII"   # 加權指數
        ticker = yf.Ticker(ticker_sym)
        hist = await asyncio.to_thread(ticker.history, period="3mo", interval="1d")

        if hist.empty or len(hist) < 20:
            return _default_regime("資料不足")

        highs  = hist['High'].tolist()
        lows   = hist['Low'].tolist()
        closes = hist['Close'].tolist()

        # ── 指標計算 ──
        adx = _calc_adx(highs, lows, closes)
        atr_pct = _calc_atr_pct(highs, lows, closes)

        closes_arr = np.array(closes)
        ma20 = float(np.mean(closes_arr[-20:]))
        ma5  = float(np.mean(closes_arr[-5:]))
        current = float(closes_arr[-1])

        # 近期斜率（趨勢方向）
        recent_10 = closes_arr[-10:]
        slope = float(np.polyfit(range(len(recent_10)), recent_10, 1)[0])
        trend_dir = 'UP' if slope > 0 else 'DOWN'

        # 近20日最高/最低
        high_20 = float(np.max(highs[-20:]))
        low_20  = float(np.min(lows[-20:]))
        range_pct = ((high_20 - low_20) / low_20) * 100

        # ── 機制判斷邏輯 ──

        # 突破行情：突破近 20 日高點
        if current >= high_20 * 0.99 and trend_dir == 'UP' and adx > 20:
            regime = _make_regime(
                regime='BREAKOUT',
                regime_cn='突破行情 🚀',
                adx=adx, atr_pct=atr_pct, trend_dir=trend_dir,
                allowed=['momentum', 'breakout'],
                confidence_adj=15,
                position_scale=1.2,
                suggestion=(
                    "🚀 突破行情！最佳進場視窗已開啟。\n"
                    "  ▸ 優先執行「動能策略」和「突破策略」\n"
                    "  ▸ 可適度放大倉位 (1.2×)\n"
                    "  ▸ 停損可稍放寬 (ATR×1.8)"
                )
            )

        # 趨勢多頭：ADX > 25, 站上 MA20, 斜率向上
        elif adx > 25 and current > ma20 and trend_dir == 'UP':
            regime = _make_regime(
                regime='TRENDING_UP',
                regime_cn='趨勢多頭 📈',
                adx=adx, atr_pct=atr_pct, trend_dir=trend_dir,
                allowed=['momentum', 'breakout', 'pullback'],
                confidence_adj=10,
                position_scale=1.0,
                suggestion=(
                    "📈 多頭趨勢確立。\n"
                    "  ▸ 回檔買、突破買、動能買均可執行\n"
                    "  ▸ 每次進場後持倉時間可拉長\n"
                    "  ▸ 停損設在 MA5 之下"
                )
            )

        # 趨勢空頭：ADX > 25, 跌破 MA20, 斜率向下
        elif adx > 25 and current < ma20 and trend_dir == 'DOWN':
            regime = _make_regime(
                regime='TRENDING_DOWN',
                regime_cn='趨勢空頭 📉',
                adx=adx, atr_pct=atr_pct, trend_dir=trend_dir,
                allowed=[],   # 禁止所有做多
                confidence_adj=-30,
                position_scale=0.0,
                suggestion=(
                    "📉 空頭趨勢確立，禁止做多！\n"
                    "  ▸ 所有新買入信號均忽略\n"
                    "  ▸ 現有持倉考慮縮減\n"
                    "  ▸ 等待 MA5 重新向上再評估"
                )
            )

        # 高波動：ATR% > 3.5%，但無明確方向
        elif atr_pct > 3.5:
            regime = _make_regime(
                regime='VOLATILE',
                regime_cn='高波動震盪 ⚡',
                adx=adx, atr_pct=atr_pct, trend_dir=trend_dir,
                allowed=['vwap_bounce'],  # 只允許反彈策略
                confidence_adj=-10,
                position_scale=0.5,
                suggestion=(
                    "⚡ 高波動震盪期，方向不明確。\n"
                    "  ▸ 倉位縮減至正常的 50%\n"
                    "  ▸ 只做「VWAP 反彈」短線\n"
                    "  ▸ 停損設嚴，快進快出"
                )
            )

        # 盤整：ADX 低，窄幅震盪
        else:
            regime = _make_regime(
                regime='RANGING',
                regime_cn='盤整區間 ↔️',
                adx=adx, atr_pct=atr_pct, trend_dir=trend_dir,
                allowed=['pullback', 'vwap_bounce'],
                confidence_adj=0,
                position_scale=0.7,
                suggestion=(
                    "↔️ 盤整行情，等待突破方向。\n"
                    "  ▸ 只做回檔買和 VWAP 反彈\n"
                    "  ▸ 停利縮短（ATR×1.5 即走）\n"
                    "  ▸ 等待 ADX > 25 的突破再加大"
                )
            )

        _regime_cache = regime
        _regime_cache_time = datetime.now()

        logger.info(
            f"🔭 [市場機制] 判斷為「{regime['regime_cn']}」| "
            f"ADX={adx:.1f} | ATR%={atr_pct:.1f}% | "
            f"趨勢方向: {trend_dir}"
        )

        return regime

    except Exception as e:
        logger.error(f"市場機制偵測失敗: {e}")
        return _default_regime(str(e))


def _make_regime(
    regime: str, regime_cn: str, adx: float, atr_pct: float,
    trend_dir: str, allowed: List[str],
    confidence_adj: int, position_scale: float, suggestion: str
) -> Dict:
    return {
        'regime': regime,
        'regime_cn': regime_cn,
        'adx': adx,
        'volatility_pct': atr_pct,
        'trend_dir': trend_dir,
        'allowed_strategies': allowed,
        'confidence_adj': confidence_adj,
        'position_scale': position_scale,
        'suggestion': suggestion,
        'detected_at': datetime.now().isoformat()
    }


def _default_regime(reason: str) -> Dict:
    return _make_regime(
        regime='NEUTRAL', regime_cn='中性/未知',
        adx=0, atr_pct=0, trend_dir='FLAT',
        allowed=['pullback', 'breakout', 'momentum', 'vwap_bounce'],
        confidence_adj=0, position_scale=1.0,
        suggestion=f"⚙️ 無法判斷市場機制 ({reason})，使用預設設定"
    )
