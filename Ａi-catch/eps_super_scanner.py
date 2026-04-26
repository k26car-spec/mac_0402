import yfinance as yf
import pandas as pd
import numpy as np
import sys
import os
import requests
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# 全域中文股票名稱快取
STOCK_NAMES_CACHE: dict = {}

# 上市/上櫃自動辨識快取
_SUFFIX_CACHE: dict = {}   # symbol -> 'TW' | 'TWO'


# ══════════════════════════════════════════════
#  五大產業分類標籤
# ══════════════════════════════════════════════
INDUSTRY_MAP = {
    # CPO（共封裝光學 / 光連接）— 已核實代碼
    "CPO": [
        "2454",  # 聯發科
        "3037",  # 欣興
        "3044",  # 健鼎
        "6669",  # 緯穎（400G/800G 連接器）
        "4977",  # 眾達電通
        "6770",  # 力積電
        "3706",  # 神達（光模組）
        "6415",  # 矽力-KY
        "3596",  # 智易
        "6285",  # 啟碁
        "2308",  # 台達電（CPO 電源）
        "3661",  # 昆盈科
        "2356",  # 英飛
        "4938",  # 和碩
    ],
    # PCB（印刷電路板）— 移除已下市：6452/3269/2384
    "PCB": [
        "3037",  # 欣興
        "3044",  # 健鼎
        "2313",  # 華通
        "8046",  # 南電
        "3189",  # 景碩
        "2367",  # 燿華
        "6153",  # 嘉聯益
        "4927",  # 泰鼎
        "3042",  # 晶技
        "3005",  # 神基
        "6491",  # 晶宇
        "3376",  # 新日興
        "4916",  # 事欣科
        "2316",  # 楠梓電
        "3708",  # 上緯投控
        "8249",  # 菱光
        "2355",  # 敬鵬
    ],
    # 記憶體（DRAM / NAND / HBM）— 移除 3014（無效）
    "記憶體/HBM": [
        "2303",  # 聯電
        "2344",  # 華邦電
        "3260",  # 威剛（.TWO）
        "6770",  # 力積電
        "5269",  # 祥碩
        "3711",  # 日月光（HBM 封裝）
        "2330",  # 台積電（HBM 堆疊）
        "2454",  # 聯發科
        "4967",  # 十銓
        "2408",  # 南亞科
    ],
    # 低軌衛星（Starlink / LEO）— 移除 3369/5323（已下市/無效）
    "低軌衛星": [
        "3443",  # 創意
        "6285",  # 啟碁
        "4906",  # 正文
        "3533",  # 嘉澤
        "4977",  # 眾達電通
        "6669",  # 緯穎
        "3596",  # 智易
        "3706",  # 神達
        "2312",  # 金寶
        "2317",  # 鴻海
        "6488",  # 環球晶（.TWO）
        "3094",  # 聯傑
        "2357",  # 華碩
    ],
    # ABF 載板 — 移除已下市：6452/2334
    "ABF載板": [
        "3037",  # 欣興
        "8046",  # 南電
        "3189",  # 景碩
        "2303",  # 聯電
        "4927",  # 泰鼎
        "3044",  # 健鼎（ABF）
        "6491",  # 晶宇
        "3376",  # 新日興
    ],
}

def get_industry_tags(symbol: str) -> list:
    """回傳該股票屬於哪些主題產業"""
    tags = [ind for ind, syms in INDUSTRY_MAP.items() if symbol in syms]
    return tags


# ══════════════════════════════════════════════
#  yfinance 輔助函式
# ══════════════════════════════════════════════
def get_yf_ticker(symbol: str):
    """
    自動辨識上市(.TW) / 上櫃(.TWO)。
    使用 redirect_stderr 壓制 yfinance HTTP 404 錯誤雜訊。
    回傳 (ticker物件, suffix字串)。
    """
    import io, contextlib

    if symbol in _SUFFIX_CACHE:
        suffix = _SUFFIX_CACHE[symbol]
        return yf.Ticker(f"{symbol}.{suffix}"), suffix

    # 先試上市（壓制 stderr）
    with contextlib.redirect_stderr(io.StringIO()):
        ticker_tw = yf.Ticker(f"{symbol}.TW")
        info_tw   = ticker_tw.info
    if info_tw.get('currentPrice') or info_tw.get('regularMarketPrice'):
        _SUFFIX_CACHE[symbol] = 'TW'
        return ticker_tw, 'TW'

    # fallback 上櫃
    with contextlib.redirect_stderr(io.StringIO()):
        ticker_two = yf.Ticker(f"{symbol}.TWO")
        info_two   = ticker_two.info
    if info_two.get('currentPrice') or info_two.get('regularMarketPrice'):
        _SUFFIX_CACHE[symbol] = 'TWO'
        return ticker_two, 'TWO'

    # 兩種都失敗 → 預設 .TW，上層 analyze_super_stock 會 return None
    _SUFFIX_CACHE[symbol] = 'TW'
    return ticker_tw, 'TW'


def get_stock_name(symbol: str) -> str:
    """查詢中文股票名稱（快取 → 後端 API → yfinance）"""
    global STOCK_NAMES_CACHE
    if symbol in STOCK_NAMES_CACHE:
        return STOCK_NAMES_CACHE[symbol]
    try:
        resp = requests.get(
            f"http://localhost:8000/api/stock-analysis/stock-name/{symbol}", timeout=3)
        if resp.status_code == 200:
            name = resp.json().get('name', '')
            if name and not name.isupper():
                STOCK_NAMES_CACHE[symbol] = name
                return name
    except:
        pass
    try:
        ticker, _ = get_yf_ticker(symbol)
        info = ticker.info
        name = info.get('shortName') or info.get('longName', '')
        if name:
            STOCK_NAMES_CACHE[symbol] = name
            return name
    except:
        pass
    return symbol


# ══════════════════════════════════════════════
#  四大指標輔助計算
# ══════════════════════════════════════════════
def calc_ma_trend_score(close: pd.Series) -> dict:
    """
    均線多頭排列評分
    條件：MA5 > MA10 > MA20 且股價在 MA20 之上
    回傳 passed(bool), score(0~4), detail(str)
    """
    ma5  = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    cp   = close.iloc[-1]
    checks = {
        "MA5>MA10":  float(ma5.iloc[-1]) > float(ma10.iloc[-1]),
        "MA10>MA20": float(ma10.iloc[-1]) > float(ma20.iloc[-1]),
        "價>MA20":   cp > float(ma20.iloc[-1]),
        "價>MA10":   cp > float(ma10.iloc[-1]),
    }
    score = sum(checks.values())
    return {
        "passed": score >= 3,
        "score": score,
        "detail": "多頭排列✅" if score >= 3 else f"均線排列不足({score}/4)"
    }


def calc_volume_pattern_score(close: pd.Series, volume: pd.Series) -> dict:
    """
    突破爆量 + 回測縮量評分
    - 近 60 日中有至少 1 根「爆量上漲日」（量 > 均量 1.5 倍且漲幅 > 1%）
    - 最近 5 日均量 < 20 日均量（縮量回測）
    """
    vol_ma20 = volume.rolling(20).mean()
    pct_chg  = close.pct_change()

    recent_60v  = volume[-60:]
    recent_60vm = vol_ma20[-60:]
    recent_60r  = pct_chg[-60:]

    # 爆量上漲日
    breakout = (recent_60v > recent_60vm * 1.5) & (recent_60r > 0.01)
    has_breakout = breakout.any()

    # 縮量回測
    vol5  = float(volume[-5:].mean())
    vol20 = float(vol_ma20.iloc[-1])
    is_pullback_quiet = (vol5 < vol20) if vol20 > 0 else False

    score = int(has_breakout) + int(is_pullback_quiet)
    return {
        "passed": has_breakout,   # 至少有爆量突破才算通過
        "score": score,
        "has_breakout": has_breakout,
        "pullback_quiet": is_pullback_quiet,
        "detail": (
            "爆量突破✅縮量回測✅" if has_breakout and is_pullback_quiet else
            "爆量突破✅(回測量未縮)" if has_breakout else
            "無爆量突破❌"
        )
    }


def calc_position_score(close: pd.Series, high: pd.Series) -> dict:
    """
    位階分析：近 52 週新高 + 上方套牢壓力輕
    """
    w52_high = high.rolling(252, min_periods=60).max().iloc[-1]
    cp = close.iloc[-1]
    dist_to_52w = ((cp - w52_high) / w52_high) * 100  # 0=創新高，負數=距高點距離

    near_high    = dist_to_52w >= -5.0   # 距 52 週高 5% 以內
    at_new_high  = dist_to_52w >= -1.0   # 實際創新高

    return {
        "passed": near_high,
        "at_new_high": at_new_high,
        "dist_to_52w": round(dist_to_52w, 1),
        "w52_high": round(w52_high, 2),
        "detail": (
            "🏆 52週新高！" if at_new_high else
            f"距52週高{dist_to_52w:.1f}%（上方壓力輕）" if near_high else
            f"距52週高{dist_to_52w:.1f}%（位階偏低）"
        )
    }


# ══════════════════════════════════════════════
#  主要分析函式（整合四大指標）
# ══════════════════════════════════════════════
def analyze_super_stock(symbol: str) -> dict:
    """分析單檔股票：MA10強勢 + EPS成長 + 四大指標評分"""
    try:
        ticker, suffix = get_yf_ticker(symbol)
        info = ticker.info

        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        target_price  = info.get('targetMeanPrice', 0)
        forward_eps   = info.get('forwardEps', 0)
        trailing_eps  = info.get('trailingEps', 0)

        # ── 法人評級 ──
        rec_mean    = info.get('recommendationMean', 3.0)
        rec_key     = info.get('recommendationKey', 'hold')
        num_analysts= info.get('numberOfAnalystOpinions', 0)
        target_high = info.get('targetHighPrice', target_price)
        target_low  = info.get('targetLowPrice', target_price)

        REC_MAP = {
            'strong_buy':   '🔥 強力買進',
            'buy':          '📈 買進',
            'hold':         '➡️ 持有',
            'underperform': '⚠️ 表現落後',
            'sell':         '🔴 賣出',
        }
        rec_label = REC_MAP.get(rec_key, f'({rec_key})')
        analyst_bullish = rec_mean <= 2.5

        if not current_price or target_price <= 0:
            return None

        roi_potential = ((target_price - current_price) / current_price) * 100
        eps_growth = 0
        if trailing_eps > 0 and forward_eps > 0:
            eps_growth = ((forward_eps - trailing_eps) / trailing_eps) * 100

        # ── 歷史股價（1年，供四大指標計算）──
        hist = ticker.history(period="1y")
        if len(hist) < 60:
            return None

        close  = hist['Close']
        high_s = hist['High']
        low_s  = hist['Low']
        volume = hist['Volume']

        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        recent_ma10_series = close.rolling(10).mean()

        # KD (9日)
        low_min  = low_s.rolling(9).min()
        high_max = high_s.rolling(9).max()
        rsv = 100 * (close - low_min) / (high_max - low_min + 1e-8)
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        current_k = k.iloc[-1]
        distance_to_ma10 = ((current_price - ma10) / ma10) * 100

        # ── MA10 強勢度（近 60 日）──
        recent_close = close[-60:]
        recent_ma10  = recent_ma10_series[-60:]
        above_ma10_days  = sum(recent_close > recent_ma10)
        above_ma10_ratio = (above_ma10_days / 60) * 100
        passes_ma10 = above_ma10_ratio >= 65

        # ══ 四大指標評分 ══
        ma_trend   = calc_ma_trend_score(close)         # ①均線多頭排列
        vol_pat    = calc_volume_pattern_score(close, volume)  # ②量能突破+回測縮量
        position   = calc_position_score(close, high_s)  # ④位階新高

        # ③法人指標：連買訊號用分析師評級代替（yfinance 無日級機構買賣資料）
        analyst_score = {
            "passed": analyst_bullish,
            "score": 2 if rec_mean <= 1.8 else 1 if rec_mean <= 2.5 else 0,
            "detail": (
                f"{rec_label}（{num_analysts}位，均值{rec_mean:.1f}）"
                if num_analysts > 0 else
                "無法人評級資料"
            )
        }

        # ── 四大指標通過數 ──
        big4_results = {
            "均線多頭排列": ma_trend,
            "量能突破縮量": vol_pat,
            "法人看漲共識": analyst_score,
            "52週高位置": position,
        }
        big4_passed = sum(1 for v in big4_results.values() if v["passed"])

        # ── 核心篩選：MA10強勢 + 至少通過 2 大指標 ──
        passes_roi     = roi_potential > 5
        passes_analyst = analyst_bullish

        if passes_ma10 and big4_passed >= 2 and (passes_roi or passes_analyst):

            # AI 建倉區間
            entry_zone_high = ma10 * 1.015
            entry_zone_low  = ma10 * 0.985
            short_term_target = ma10 * 1.15
            stop_loss = max(ma20, ma10 * 0.97)

            if distance_to_ma10 < 3 and current_k < 65:
                action = "🔥 買進信號：回測 MA10 且 KD 未過熱"
            elif distance_to_ma10 > 8:
                action = "⏳ 等待拉回：乖離過大，等回測 MA10"
            else:
                action = "👀 觀察中：可分批建倉，注意量能"

            # 產業標籤
            industry_tags = get_industry_tags(symbol)

            return {
                'symbol':       symbol,
                'price':        round(current_price, 2),
                'target':       round(target_price, 2),
                'target_high':  round(target_high, 2) if target_high else round(target_price, 2),
                'target_low':   round(target_low, 2)  if target_low  else round(target_price, 2),
                'roi':          round(roi_potential, 1),
                'eps_growth':   round(eps_growth, 1) if eps_growth else 'N/A',
                'ma10_val':     round(ma10, 2),
                'ma10_strength':round(above_ma10_ratio, 1),
                'dist_to_ma10': round(distance_to_ma10, 2),
                'kd_k':         round(current_k, 1),
                'entry_low':    round(entry_zone_low, 2),
                'entry_high':   round(entry_zone_high, 2),
                'short_target': round(short_term_target, 2),
                'stop_loss':    round(stop_loss, 2),
                'action':       action,
                'name':         info.get('shortName', symbol),
                # 法人評級
                'rec_label':    rec_label,
                'rec_mean':     round(rec_mean, 1),
                'num_analysts': num_analysts,
                'passes_roi':   passes_roi,
                'passes_analyst': passes_analyst,
                # 四大指標
                'big4_passed':  big4_passed,
                'big4_results': {k: v['detail'] for k, v in big4_results.items()},
                'ma_trend_ok':  ma_trend['passed'],
                'vol_pat_ok':   vol_pat['passed'],
                'analyst_ok':   analyst_score['passed'],
                'position_ok':  position['passed'],
                'dist_52w':     position['dist_to_52w'],
                'at_new_high':  position['at_new_high'],
                # 產業標籤
                'industry_tags': industry_tags,
            }

    except Exception as e:
        pass

    return None


# ══════════════════════════════════════════════
#  動態載入台灣科技股清單
# ══════════════════════════════════════════════
def load_tw_tech_stocks() -> list:
    """從 TWSE OpenAPI 動態抓取全部上市股票，篩出科技類股。"""
    global STOCK_NAMES_CACHE
    import requests, warnings
    warnings.filterwarnings('ignore')

    TECH_NAME_KEYWORDS = [
        "電", "導體", "積體", "光", "網", "技", "科", "訊", "晶",
        "板", "路", "記憶", "感測", "顯示", "模組", "元件", "電路",
    ]

    def is_tech_code(code: str) -> bool:
        if not code.isdigit() or len(code) != 4:
            return False
        n = int(code)
        return (
            2300 <= n <= 2499 or
            3000 <= n <= 3799 or
            4800 <= n <= 4999 or
            5200 <= n <= 5499 or
            6100 <= n <= 6999
        )

    symbols = set()

    # 加入五大產業的所有股票（優先確保掃描）
    for syms in INDUSTRY_MAP.values():
        symbols.update(syms)

    # TWSE OpenAPI
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                            verify=False, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                code = str(item.get('Code', '')).strip()
                name = str(item.get('Name', '')).strip()
                if not code.isdigit() or len(code) != 4:
                    continue
                if is_tech_code(code) or any(kw in name for kw in TECH_NAME_KEYWORDS):
                    symbols.add(code)
                    if name:
                        STOCK_NAMES_CACHE[code] = name
            result = sorted(symbols)
            print(f"✅ 從 TWSE STOCK_DAY_ALL 共取得 {len(result)} 檔科技類股")
            return result
    except Exception as e:
        print(f"⚠️ TWSE API 失敗: {e}")

    # 備用清單
    print("📋 使用內建備用科技股清單")
    fallback = symbols | {
        "2330", "2454", "2303", "3711", "3034", "2379", "2344", "2337",
        "6770", "3661", "2408", "3443", "3529", "2369", "2449", "3653",
        "6239", "2438", "3042", "3697", "3702", "6415", "3406", "3044",
        "6531", "3035", "6442", "3036", "2351", "6698", "6669", "3046",
        "2317", "3037", "2313", "8046", "3706", "2327", "6153", "2368",
        "2367", "3189", "3094", "2314", "2382", "3231", "2356", "3714",
        "3481", "2409", "3592", "3015", "3059", "2393", "2448", "2399",
        "2412", "2498", "6176", "4906", "2357", "2377", "3008", "2301",
        "4938", "3673", "2353", "2347", "3533", "3669", "6443", "5269",
        "6488", "3491", "6263", "3552", "2376", "2308",
    }
    try:
        resp = requests.get("http://localhost:8000/api/watchlist/today", timeout=3)
        if resp.status_code == 200:
            for item in resp.json().get('watchlist', []):
                code = str(item.get('symbol', ''))
                if is_tech_code(code):
                    fallback.add(code)
    except:
        pass

    result = sorted(fallback)
    print(f"✅ 備用清單共 {len(result)} 檔科技類股")
    return result


# ══════════════════════════════════════════════
#  HTML 報告生成（整合四大指標 + 產業標籤）
# ══════════════════════════════════════════════
INDUSTRY_COLORS = {
    "CPO":      "#3b82f6",   # 藍
    "PCB":      "#8b5cf6",   # 紫
    "記憶體/HBM": "#ef4444", # 紅
    "低軌衛星": "#10b981",   # 綠
    "ABF載板":  "#f59e0b",   # 橘
}

def _tag_badge(tag: str) -> str:
    color = INDUSTRY_COLORS.get(tag, "#64748b")
    return (
        f'<span style="display:inline-block;padding:2px 8px;background:{color}18;'
        f'color:{color};border:1px solid {color}44;border-radius:12px;'
        f'font-size:11px;font-weight:bold;margin-right:4px;">{tag}</span>'
    )

def _indicator_row(name: str, passed: bool, detail: str) -> str:
    icon  = "✅" if passed else "❌"
    color = "#16a34a" if passed else "#dc2626"
    return (
        f'<tr><td style="padding:4px 0;font-size:13px;color:#334155;">'
        f'{icon} <b>{name}：</b><span style="color:{color};">{detail}</span>'
        f'</td></tr>'
    )

def generate_html_report(results: list) -> str:
    """生成含四大指標 + 產業標籤的 HTML 報告"""
    rows_html = ""
    for r in results:
        zh_name = get_stock_name(r['symbol'])
        if zh_name.isupper() or zh_name == r['symbol']:
            zh_name = r.get('name', r['symbol']).split(' ')[0]
        sym_name = f"{r['symbol']} {zh_name}"
        action_color = (
            "#16a34a" if "買進" in r['action'] else
            "#dc2626" if "等待" in r['action'] else
            "#ca8a04"
        )

        # 產業標籤 HTML
        tags_html = "".join(_tag_badge(t) for t in r.get('industry_tags', []))
        if tags_html:
            tags_html = f'<div style="margin-bottom:8px;">{tags_html}</div>'

        # 四大指標列
        b4 = r.get('big4_results', {})
        indicators_html = "".join([
            _indicator_row("①均線多頭排列",  r.get('ma_trend_ok', False),  b4.get("均線多頭排列",  "-")),
            _indicator_row("②量能突破縮量",  r.get('vol_pat_ok', False),   b4.get("量能突破縮量",  "-")),
            _indicator_row("③法人看漲共識",  r.get('analyst_ok', False),   b4.get("法人看漲共識",  "-")),
            _indicator_row("④52週高位置",    r.get('position_ok', False),  b4.get("52週高位置",    "-")),
        ])
        big4_passed = r.get('big4_passed', 0)
        big4_color  = "#16a34a" if big4_passed >= 3 else "#ca8a04" if big4_passed == 2 else "#dc2626"

        rows_html += f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;margin-bottom:20px;border-left:4px solid {action_color};border-collapse:collapse;box-shadow:0 2px 4px rgba(0,0,0,0.08);">
          <tr><td colspan="2" style="padding:16px 20px 6px 20px;">
            <span style="font-size:18px;font-weight:bold;color:#1e293b;">■ {sym_name}</span>
            &nbsp;<span style="font-size:12px;color:{big4_color};font-weight:bold;">四大指標通過 {big4_passed}/4</span>
          </td></tr>
          <tr><td colspan="2" style="padding:0 20px 8px 20px;">{tags_html}</td></tr>
          <tr>
            <td style="padding:4px 20px;font-size:14px;color:#475569;width:50%;">💰 現價: <b>${r['price']}</b></td>
            <td style="padding:4px 20px;font-size:14px;color:#475569;width:50%;">🎯 法人目標: <b>${r['target']}</b> <span style="color:#dc2626;">(+{r['roi']}%)</span></td>
          </tr>
          <tr>
            <td style="padding:4px 20px;font-size:14px;color:#475569;">📈 EPS 預估成長: <b style="color:#dc2626;">+{r['eps_growth']}%</b></td>
            <td style="padding:4px 20px;font-size:14px;color:#475569;">🛡️ MA10 強度(60日): <b>{r['ma10_strength']}%</b></td>
          </tr>
          <tr>
            <td style="padding:4px 20px 8px 20px;font-size:14px;color:#475569;">📊 乖離MA10: <b>{r['dist_to_ma10']:+g}%</b></td>
            <td style="padding:4px 20px 8px 20px;font-size:14px;color:#475569;">📈 KD(K值): <b>{r['kd_k']}</b></td>
          </tr>
          <!-- 四大指標區塊 -->
          <tr><td colspan="2" style="padding:0 20px 8px 20px;">
            <table width="100%" cellpadding="8" cellspacing="0" style="background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0;">
              <tr><td style="font-size:13px;font-weight:bold;color:#166534;border-bottom:1px solid #bbf7d0;">
                🔎 四大關鍵指標評分
              </td></tr>
              {indicators_html}
            </table>
          </td></tr>
          <!-- AI 建倉建議 -->
          <tr><td colspan="2" style="padding:0 20px 16px 20px;">
            <table width="100%" cellpadding="10" cellspacing="0" style="background:#f8fafc;border-radius:8px;">
              <tr><td style="font-size:13px;color:#334155;border-bottom:1px solid #e2e8f0;">
                🎯 <b>【AI 建倉區間】</b>：${r['entry_low']} ~ ${r['entry_high']} (靠近MA10=${r['ma10_val']})
              </td></tr>
              <tr><td style="font-size:13px;color:#334155;border-bottom:1px solid #e2e8f0;">
                💸 <b>【建議賣點】</b>：短線波段 ${r['short_target']} / 長線法人目標 ${r['target']}
              </td></tr>
              <tr><td style="font-size:13px;color:#334155;border-bottom:1px solid #e2e8f0;">
                🛡️ <b>【防守停損】</b>：破 ${r['stop_loss']} 出場
              </td></tr>
              <tr><td style="text-align:center;font-weight:bold;font-size:14px;color:{action_color};background:{action_color}18;border-radius:6px;">
                👉 AI 今日建議：{r['action']}
              </td></tr>
            </table>
          </td></tr>
        </table>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family:Arial,sans-serif;background:#f1f5f9;padding:20px;margin:0;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
        <table width="680" cellpadding="0" cellspacing="0">

          <!-- Header -->
          <tr><td style="background:linear-gradient(135deg,#1e40af,#3b82f6);color:white;padding:24px;text-align:center;border-radius:16px;margin-bottom:24px;">
            <div style="font-size:22px;font-weight:bold;margin-bottom:6px;">🤖 AI 每日強勢股報告</div>
            <div style="opacity:0.9;font-size:14px;">【四大指標 × 五大產業 × EPS高成長 × MA10超強勢】</div>
            <div style="font-size:12px;margin-top:6px;opacity:0.8;">{datetime.now().strftime('%Y-%m-%d')}</div>
          </td></tr>

          <tr><td height="16"></td></tr>

          <!-- 產業圖例 -->
          <tr><td style="background:white;border-radius:10px;padding:14px 18px;margin-bottom:16px;border:1px solid #e2e8f0;">
            <div style="font-size:13px;font-weight:bold;color:#1e293b;margin-bottom:8px;">📊 本次掃描五大產業主題</div>
            <div>{"".join(_tag_badge(t) for t in INDUSTRY_MAP.keys())}</div>
          </td></tr>

          <!-- 四大指標說明 -->
          <tr><td height="12"></td></tr>
          <tr><td style="background:#fff8f1;border-left:4px solid #f97316;padding:14px 16px;border-radius:8px;color:#9a3412;font-size:13px;line-height:1.7;">
            🔎 <b>四大關鍵指標說明：</b><br>
            ① <b>均線多頭排列</b>：MA5>MA10>MA20，股價在月線之上<br>
            ② <b>量能突破縮量</b>：近60日出現爆量突破，回測時縮量（健康）<br>
            ③ <b>法人看漲共識</b>：投信/外資分析師評級偏向買進（rec_mean≤2.5）<br>
            ④ <b>52週新高位置</b>：股價距52週高點5%以內，上方套牢壓力輕<br>
            💡 <b>如何配合 LSTM</b>：當股票落入【AI建倉區間】且 LSTM 也看漲，此時進場勝率最高！
          </td></tr>

          <tr><td height="16"></td></tr>

          <!-- 股票列表 -->
          {rows_html if rows_html else "<tr><td style='text-align:center;padding:40px;background:white;border-radius:12px;'>今日無符合條件之股票。</td></tr>"}

          <!-- Footer -->
          <tr><td style="text-align:center;color:#64748b;font-size:12px;padding-top:20px;">
            AI Stock Intelligence 自動化報告系統 | 四大指標 × 五大產業掃描
          </td></tr>

        </table>
        </td></tr></table>
    </body>
    </html>
    """
    return html


# ══════════════════════════════════════════════
#  Email 發送
# ══════════════════════════════════════════════
def send_email_report(results: list):
    """將報告寄出"""
    backend_path = os.path.join(os.path.dirname(__file__), 'backend-v3')
    if backend_path not in sys.path:
        sys.path.append(backend_path)

    try:
        from app.services.trade_email_notifier import trade_notifier
        html_content = generate_html_report(results)
        buy_count = sum(1 for r in results if "買進" in r['action'])
        b4_full   = sum(1 for r in results if r.get('big4_passed', 0) >= 3)
        date_str  = datetime.now().strftime('%m/%d')
        subject = (
            f"🤖 AI 強勢股報告 ({date_str}) "
            f"| 買入信號 {buy_count} 檔 "
            f"| 四大全通過 {b4_full} 檔"
        )
        success = trade_notifier._send_email(subject, html_content)
        if success:
            print("✅ 成功發送 AI 分析報告 Email！")
        else:
            print("❌ Email 發送失敗，請檢查設定。")
    except Exception as e:
        print(f"⚠️ 無法發送 Email：{e}")


# ══════════════════════════════════════════════
#  主程式
# ══════════════════════════════════════════════
def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI 每日強勢股掃描（四大指標 + 五大產業）")
    parser.add_argument("--email",    action="store_true", help="掃描完後自動發送 Email 報告")
    parser.add_argument("--industry", default="all",
                        help="只掃特定產業：CPO / PCB / 記憶體/HBM / 低軌衛星 / ABF載板 / all")
    args = parser.parse_args()

    print("=" * 90)
    print("🤖 AI 每日強勢股功課：【四大指標 × 五大產業 × EPS成長 + MA10超強勢】")
    print(f"📅 日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if args.industry != "all":
        print(f"🏷️  指定產業：{args.industry}")
    print("=" * 90)

    # 決定掃描清單
    if args.industry != "all" and args.industry in INDUSTRY_MAP:
        test_symbols = sorted(set(INDUSTRY_MAP[args.industry]))
        print(f"📋 {args.industry} 產業共 {len(test_symbols)} 支股票")
    else:
        test_symbols = load_tw_tech_stocks()
        test_symbols = sorted(set(test_symbols))

    print(f"\n📡 正在掃描 {len(test_symbols)} 檔候選股票...\n")
    results = []

    for sym in test_symbols:
        res = analyze_super_stock(sym)
        if res:
            results.append(res)

    if not results:
        print("今日沒有找到符合條件的股票。")
        if args.email:
            send_email_report([])
        return

    # 排序：先按四大指標通過數，再按報酬率
    results.sort(key=lambda x: (x.get('big4_passed', 0), x['roi']), reverse=True)

    # ── 終端機顯示 ──
    for r in results:
        zh_name = get_stock_name(r['symbol'])
        if zh_name.isupper() or zh_name == r['symbol']:
            zh_name = r.get('name', r['symbol']).split(' ')[0]
        sym_name = f"{r['symbol']} {zh_name}"

        basis = []
        if r.get('passes_roi'):      basis.append("目標價有空間")
        if r.get('passes_analyst'):  basis.append("分析師看漲")
        basis_str = " + ".join(basis) if basis else "-"

        tags   = r.get('industry_tags', [])
        tag_str = f" [{' / '.join(tags)}]" if tags else ""
        b4 = r.get('big4_results', {})

        print(f"\n■ {sym_name}{tag_str}  ★四大指標通過 {r.get('big4_passed',0)}/4")
        print(f"  💰 現價: ${r['price']} | 法人目標: ${r['target']} ({r['roi']:+.1f}%)")
        print(f"     ↳ 目標區間: ${r.get('target_low','?')} ~ ${r.get('target_high','?')}  |  {r.get('rec_label','?')}  ({r.get('num_analysts',0)} 位分析師)")
        print(f"  📈 EPS 預估成長: +{r['eps_growth']}% | MA10 強度(60日): {r['ma10_strength']}%")
        print(f"  📊 乖離MA10: {r['dist_to_ma10']:+g}% | KD(K值): {r['kd_k']}  ▶ 依據：{basis_str}")
        print(f"  🔎 四大指標：")
        for k, v in b4.items():
            icon = "✅" if (
                (k == "均線多頭排列" and r.get('ma_trend_ok')) or
                (k == "量能突破縮量" and r.get('vol_pat_ok')) or
                (k == "法人看漲共識" and r.get('analyst_ok')) or
                (k == "52週高位置"   and r.get('position_ok'))
            ) else "❌"
            print(f"     {icon} {k}：{v}")
        print(f"  🎯 【AI建倉區間】: ${r['entry_low']} ~ ${r['entry_high']} (MA10=${r['ma10_val']})")
        print(f"  💸 【建議賣點】短線 ${r['short_target']} / 長線目標 ${r['target']}")
        print(f"  🛡️ 【防守停損】破 ${r['stop_loss']} 出場")
        print(f"  👉 【AI 今日建議】: {r['action']}")
        print("-" * 90)

    # 統計摘要
    print(f"\n📊 掃描摘要：")
    print(f"   符合條件共 {len(results)} 檔  |  四大指標全通過：{sum(1 for r in results if r.get('big4_passed',0)>=3)} 檔")
    print(f"   🔥 買進信號：{sum(1 for r in results if '買進' in r['action'])} 檔  |  ⏳ 等待拉回：{sum(1 for r in results if '等待' in r['action'])} 檔")
    # 產業分布
    from collections import Counter
    all_tags = [t for r in results for t in r.get('industry_tags', [])]
    if all_tags:
        tag_count = Counter(all_tags)
        print(f"   🏷️  產業分布：{dict(tag_count)}")

    print("\n💡 最佳策略：四大指標全通過 + LSTM 看漲 + 落入【AI建倉區間】= 最高勝率進場點")

    # ── 儲存 JSON 供前端 Dashboard 讀取（掃描後自動更新）──
    _save_json_report(results, args.industry)

    if args.email:
        print("\n📧 正在生成 HTML 報告並準備發送 Email...")
        send_email_report(results)


def _save_json_report(results: list, scan_industry: str = "all"):
    """將掃描結果序列化為 JSON，儲存到 static/eps_report.json"""
    import json
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    os.makedirs(static_dir, exist_ok=True)
    out_path = os.path.join(static_dir, 'eps_report.json')

    clean = []
    for r in results:
        zh_name = get_stock_name(r['symbol'])
        if zh_name.isupper() or zh_name == r['symbol']:
            zh_name = r.get('name', r['symbol']).split(' ')[0]
        b4 = r.get('big4_results', {})
        clean.append({
            "id":            r['symbol'],
            "name":          zh_name,
            "industry_tags": r.get('industry_tags', []),
            "indicators":    r.get('big4_passed', 0),
            "price":         r['price'],
            "target":        r['target'],
            "target_low":    r.get('target_low', r['target']),
            "target_high":   r.get('target_high', r['target']),
            "roi":           r['roi'],
            "eps_growth":    str(r['eps_growth']),
            "ma10_val":      r['ma10_val'],
            "ma10_strength": r['ma10_strength'],
            "bias":          r['dist_to_ma10'],
            "kd":            r['kd_k'],
            "entry_low":     r['entry_low'],
            "entry_high":    r['entry_high'],
            "short_target":  r['short_target'],
            "stop_loss":     r['stop_loss'],
            "action":        r['action'],
            "suggestion": (
                "買進信號" if "買進" in r['action'] else
                "等待拉回" if "等待" in r['action'] else "觀察中"
            ),
            "rec_label":     r.get('rec_label', '-'),
            "num_analysts":  r.get('num_analysts', 0),
            "ma_trend_ok":   bool(r.get('ma_trend_ok', False)),
            "vol_pat_ok":    bool(r.get('vol_pat_ok', False)),
            "analyst_ok":    bool(r.get('analyst_ok', False)),
            "position_ok":   bool(r.get('position_ok', False)),
            "dist_52w":      float(r.get('dist_52w', 0)),
            "at_new_high":   bool(r.get('at_new_high', False)),
            "big4_detail":   b4,
        })

    payload = {
        "generated_at":  datetime.now().strftime('%Y-%m-%d %H:%M'),
        "scan_industry": scan_industry,
        "total":         len(clean),
        "buy_signals":   sum(1 for r in clean if r['suggestion'] == '買進信號'),
        "full_pass":     sum(1 for r in clean if r['indicators'] >= 3),
        "stocks":        clean,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"💾 戰情室 JSON 已更新：{out_path}  ({len(clean)} 檔)")


if __name__ == "__main__":
    main()
