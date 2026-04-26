"""
族群共振過濾器 (Sector Resonance Filter)
========================================
核心邏輯: 「跟著強勢族群走，避免單兵陷阱」

如果個股出現買入信號，但其所屬族群的平均漲跌幅為負，
則判定這是「假突破」或「短線出貨」風險，阻擋進場。

策略規則:
  - 族群平均漲幅 > +0.5%  → BULL，加分 +10，放行
  - 族群平均漲幅 -0.5% ~ +0.5% → NEUTRAL，不加不扣，放行
  - 族群平均漲幅 < -0.5%  → BEAR，扣分 -15，阻擋（除非個股信心度極高）
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ======================================================
# 台股主要族群對應表（代表性龍頭股清單）
# 使用 TWSE/TPEX 即时 MIS API 取價，更新快速
# ======================================================
SECTOR_GROUPS: Dict[str, List[str]] = {
    "記憶體": ["2337", "3260", "4256", "2344"],        # 旺宏、威剛、旺旺、華邦電
    "DRAM/儲存": ["2408", "3474", "5315"],             # 南亞科、華亞科、金橋
    "晶圓代工": ["2330", "2303", "5347"],              # 台積電、聯電、世界
    "IC設計": ["2454", "3034", "2379", "2388"],        # 聯發科、聯詠、瑞昱、威盛
    "封測": ["2449", "3711", "6239"],                  # 京元電、日月光、力成
    "被動元件": ["2327", "2330", "2352"],              # 國巨、台積電、佳世達
    "電源/電容": ["2315", "6214", "3036"],             # 神達、亞信、文曄
    "金融-銀行": ["2881", "2882", "2886", "2884"],     # 富邦金、國泰金、兆豐金、玉山金
    "光學/鏡頭": ["3037", "3036", "5483"],             # 欣興、文曄、中美晶
    "電動車/電池": ["5483", "6415", "1590"],           # 中美晶、矽力-KY、亞德客
    "伺服器/AI": ["2317", "3231", "6770"],             # 鴻海、緯創、力積電
}

# 股票代碼 → 所屬族群
def _build_symbol_sector_map() -> Dict[str, str]:
    mp = {}
    for sector, symbols in SECTOR_GROUPS.items():
        for s in symbols:
            mp[s] = sector
    return mp

SYMBOL_TO_SECTOR = _build_symbol_sector_map()

# ======================================================
# 快取：避免同一族群每次都重新爬取
# ======================================================
_sector_cache: Dict[str, Dict] = {}
_sector_cache_time: Dict[str, datetime] = {}
_CACHE_TTL_SECONDS = 180  # 3 分鐘快取


async def _fetch_price_mis(symbol: str) -> Optional[float]:
    """用 TWSE MIS API 取得個股即時價格（速度快，無限速）"""
    try:
        import httpx
        ex = "tse"  # 預設上市，上櫃用 otc
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex}_{symbol}.tw"
        async with httpx.AsyncClient(verify=False, timeout=4) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()
            if data.get("msgArray"):
                info = data["msgArray"][0]
                price = float(info.get("z") or info.get("o") or 0)
                prev  = float(info.get("y") or 0)
                if price > 0 and prev > 0:
                    return (price - prev) / prev * 100  # 回傳漲跌幅
    except Exception:
        pass

    # fallback: otc
    try:
        import httpx
        url2 = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=otc_{symbol}.tw"
        async with httpx.AsyncClient(verify=False, timeout=4) as client:
            resp = await client.get(url2, headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()
            if data.get("msgArray"):
                info = data["msgArray"][0]
                price = float(info.get("z") or info.get("o") or 0)
                prev  = float(info.get("y") or 0)
                if price > 0 and prev > 0:
                    return (price - prev) / prev * 100
    except Exception:
        pass
    return None


async def get_sector_condition(symbol: str) -> Dict:
    """
    獲取個股所屬族群的整體漲跌狀況。

    Returns:
        {
            'sector': str,          # 所屬族群名稱
            'avg_change': float,    # 族群平均漲跌幅
            'condition': str,       # 'BULL' / 'NEUTRAL' / 'BEAR'
            'score_adj': int,       # 信心度調整 (-15 ~ +10)
            'allow': bool,          # 是否允許進場
            'reason': str,
            'members_checked': int  # 實際查詢到的成員數
        }
    """
    sector = SYMBOL_TO_SECTOR.get(symbol)

    # 不在任何族群 → 不阻擋，但也不額外加分
    if not sector:
        return {
            'sector': '未分類',
            'avg_change': 0.0,
            'condition': 'NEUTRAL',
            'score_adj': 0,
            'allow': True,
            'reason': f'{symbol} 未分配族群，不做族群過濾',
            'members_checked': 0
        }

    # 快取命中
    now = datetime.now()
    if sector in _sector_cache and sector in _sector_cache_time:
        elapsed = (now - _sector_cache_time[sector]).total_seconds()
        if elapsed < _CACHE_TTL_SECONDS:
            cached = _sector_cache[sector]
            logger.debug(f"[族群快取] {sector}: avg={cached['avg_change']:.2f}%")
            return cached

    # 查詢同族群所有成員的即時漲跌幅（排除被查詢的個股本身）
    members = [s for s in SECTOR_GROUPS.get(sector, []) if s != symbol]
    changes = []

    tasks = [_fetch_price_mis(m) for m in members[:5]]  # 最多查 5 支
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, float):
            changes.append(r)

    if not changes:
        # 查不到 → 中性放行
        result = {
            'sector': sector,
            'avg_change': 0.0,
            'condition': 'NEUTRAL',
            'score_adj': 0,
            'allow': True,
            'reason': f'{sector} 族群數據不足，中性放行',
            'members_checked': 0
        }
        _sector_cache[sector] = result
        _sector_cache_time[sector] = now
        return result

    avg = sum(changes) / len(changes)

    if avg >= 0.5:
        condition = 'BULL'
        score_adj = 10
        allow = True
        reason = f"✅ [{sector}] 族群強勢 +{avg:.2f}%，共振加分"
    elif avg <= -0.5:
        condition = 'BEAR'
        score_adj = -15
        allow = False  # 預設阻擋
        reason = f"⚠️ [{sector}] 族群弱勢 {avg:.2f}%，疑似假突破，阻擋進場"
    else:
        condition = 'NEUTRAL'
        score_adj = 0
        allow = True
        reason = f"⚖️ [{sector}] 族群中性 {avg:.2f}%，不影響判斷"

    result = {
        'sector': sector,
        'avg_change': round(avg, 2),
        'condition': condition,
        'score_adj': score_adj,
        'allow': allow,
        'reason': reason,
        'members_checked': len(changes)
    }

    _sector_cache[sector] = result
    _sector_cache_time[sector] = now
    logger.info(f"[族群過濾] {symbol} → {sector} | 均漲跌 {avg:.2f}% | {condition}")
    return result
