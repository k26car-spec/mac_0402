"""
盤前情報引擎 (Pre-Market Intelligence Engine)
============================================
每天 08:30 自動執行，分析美股夜盤訊號，
輸出「今日台股偏多/偏空/謹慎」的開盤前預判。

資料來源（全部免費公開 API）:
  - Yahoo Finance: TSM ADR / SOX 费城半導體 / NQ 那斯達克期貨
  - TWSE MIS:      台指期即時
  - FRED (選用):   美元指數 DXY

輸出格式:
  {
    "bias": "BULL" | "BEAR" | "NEUTRAL",
    "score": int,          # -100 ~ +100
    "confidence": float,   # 0 ~ 1
    "signals": [...],      # 各因子詳細
    "opening_strategy": str  # 今日建議操作策略
  }
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────
# 快取設定
# ────────────────────────────────────────────
_CACHE_FILE = os.path.join(os.path.dirname(__file__), '../../../data/premarket_cache.json')
_CACHE_TTL_HOURS = 2   # 盤前情報快取 2 小時


def _load_cache() -> Optional[Dict]:
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, 'r') as f:
                cached = json.load(f)
            ts = datetime.fromisoformat(cached.get('_cached_at', '2000-01-01'))
            if (datetime.now() - ts).total_seconds() < _CACHE_TTL_HOURS * 3600:
                return cached
    except Exception:
        pass
    return None


def _save_cache(data: Dict):
    try:
        data['_cached_at'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with open(_CACHE_FILE, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ────────────────────────────────────────────
# 各項指標爬取
# ────────────────────────────────────────────

async def _get_yf_change(ticker_symbol: str) -> Optional[float]:
    """用 yfinance 取得指定標的的最新漲跌幅"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="3d", auto_adjust=True)
        if len(hist) >= 2:
            prev  = float(hist['Close'].iloc[-2])
            last  = float(hist['Close'].iloc[-1])
            return (last - prev) / prev * 100
    except Exception as e:
        logger.debug(f"yfinance {ticker_symbol}: {e}")
    return None


async def fetch_premarket_signals() -> Dict:
    """
    並行抓取所有盤前指標，整合成偏多/偏空判斷。
    """
    # ── 試取快取 ──
    cached = _load_cache()
    if cached:
        logger.info("📦 使用盤前情報快取")
        return cached

    logger.info("🌐 開始抓取美股盤前情報...")

    # ── 並行爬取 ──
    tasks = {
        'TSM_ADR':  _get_yf_change('TSM'),       # 台積電 ADR
        'SOX':      _get_yf_change('^SOX'),       # 費城半導體
        'NQ':       _get_yf_change('NQ=F'),       # 那斯達克期貨
        'SP500':    _get_yf_change('^GSPC'),      # S&P 500
        'DXY':      _get_yf_change('DX-Y.NYB'),  # 美元指數 (反向：DXY 強 = 台股壓力)
        'VIX':      _get_yf_change('^VIX'),       # 恐慌指數 (反向)
    }

    results = {}
    for name, coro in tasks.items():
        try:
            results[name] = await asyncio.wait_for(coro, timeout=8)
        except Exception:
            results[name] = None

    # ── 打分邏輯 ──
    score = 0
    signals = []

    def add_signal(name: str, chg: Optional[float], weight: int,
                   label_up: str, label_dn: str, inverse: bool = False):
        nonlocal score
        if chg is None:
            signals.append({'name': name, 'change': None, 'impact': '無資料', 'points': 0})
            return

        direction = chg if not inverse else -chg
        pts = 0

        if direction > 1.5:
            pts = weight
        elif direction > 0.5:
            pts = weight // 2
        elif direction < -1.5:
            pts = -weight
        elif direction < -0.5:
            pts = -weight // 2

        score += pts
        impact = f"{'📈' if pts>0 else '📉' if pts<0 else '➡️'} {label_up if pts>0 else label_dn if pts<0 else '中性'}"
        signals.append({
            'name': name,
            'change': round(chg, 2),
            'impact': impact,
            'points': pts
        })

    add_signal('台積電ADR', results.get('TSM_ADR'), 25,
               '外資看好台積電', '外資看空台積電')
    add_signal('費城半導體SOX', results.get('SOX'), 30,
               '半導體族群強勢', '半導體族群弱勢')
    add_signal('那斯達克NQ期貨', results.get('NQ'), 20,
               '科技股資金湧入', '科技股資金流出')
    add_signal('標普SP500', results.get('SP500'), 10,
               '整體市場樂觀', '整體市場悲觀')
    add_signal('美元指數DXY', results.get('DXY'), 10,
               '美元強 → 台股承壓', '美元弱 → 台股受惠',
               inverse=True)   # DXY 強 = 台股壓力 → 反向
    add_signal('VIX恐慌指數', results.get('VIX'), 5,
               'VIX 升 → 市場恐慌', 'VIX 降 → 市場鎮定',
               inverse=True)   # VIX 高 = 恐慌 → 反向

    # ── 偏向判斷 ──
    if score >= 25:
        bias = 'BULL'
        confidence = min(0.95, 0.6 + score / 200)
        strategy = (
            "📈 強勁多頭偏向\n"
            "• 開盤前 5 分鐘可積極關注突破標的\n"
            "• 優先選半導體族群（SOX/TSM ADR 強勢帶動）\n"
            "• 09:30-10:00 黃金窗口積極進場"
        )
    elif score >= 10:
        bias = 'BULL'
        confidence = 0.5 + score / 100
        strategy = (
            "⭐ 溫和偏多\n"
            "• 等待開盤確認方向後再進場\n"
            "• 優先選擇 V 型反彈 + 有量標的\n"
            "• 09:30-09:45 確認站穩均線再考慮"
        )
    elif score <= -25:
        bias = 'BEAR'
        confidence = min(0.95, 0.6 + abs(score) / 200)
        strategy = (
            "🐻 強烈空頭偏向\n"
            "• 今日禁止開新多頭倉位\n"
            "• 現有持倉考慮縮減或設緊停損\n"
            "• 等待跌深反彈再評估"
        )
    elif score <= -10:
        bias = 'BEAR'
        confidence = 0.5 + abs(score) / 100
        strategy = (
            "⚠️ 溫和偏空\n"
            "• 降低今日倉位上限（最多開 2 倉）\n"
            "• 停損設緊一點（ATR × 1.0 而非 1.5）\n"
            "• 優先觀察，不強求進場"
        )
    else:
        bias = 'NEUTRAL'
        confidence = 0.5
        strategy = (
            "⚖️ 中性盤整\n"
            "• 等待市場方向明確後再行動\n"
            "• 適合做技術面回檔買，不做追漲\n"
            "• 嚴守 09:30 後才進場的原則"
        )

    report = {
        'bias': bias,
        'score': score,
        'confidence': round(confidence, 2),
        'signals': signals,
        'opening_strategy': strategy,
        'raw_changes': {k: (round(v, 2) if v is not None else None)
                        for k, v in results.items()},
        'generated_at': datetime.now().isoformat()
    }

    _save_cache(report)

    logger.info(
        f"🌅 盤前情報完成 | 偏向: {bias} | 分數: {score:+d} | 信心: {confidence:.0%}"
    )
    for s in signals:
        logger.info(f"   {s['name']}: {s.get('change', 'N/A')}% | {s['impact']} ({s['points']:+d}分)")

    return report


async def get_premarket_bias() -> str:
    """快速取得今日開盤偏向 (BULL/BEAR/NEUTRAL)"""
    try:
        report = await fetch_premarket_signals()
        return report.get('bias', 'NEUTRAL')
    except Exception:
        return 'NEUTRAL'


# ── 測試 ──
if __name__ == '__main__':
    import asyncio
    report = asyncio.run(fetch_premarket_signals())
    print(f"\n{'='*55}")
    print(f"  🌅 盤前情報報告  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")
    print(f"  偏向: {report['bias']}  |  分數: {report['score']:+d}  |  信心: {report['confidence']:.0%}")
    print(f"\n  各項指標:")
    for s in report['signals']:
        chg_str = f"{s['change']:+.2f}%" if s['change'] is not None else "N/A"
        print(f"    {s['name']:<20} {chg_str:<10} {s['impact']} ({s['points']:+d}分)")
    print(f"\n  今日策略建議:")
    for line in report['opening_strategy'].split('\n'):
        print(f"  {line}")
    print(f"{'='*55}\n")
