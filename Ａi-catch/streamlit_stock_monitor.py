
"""
📈 潛力股監控儀表板 (Unified)
整合原有儀表板與新版掃描器
"""

import streamlit as st
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import sys
import os
import json
import streamlit.components.v1 as components

# 添加專案路徑
PROJECT_ROOT = "/Users/Mac/Documents/ETF/AI/Ａi-catch"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 導入富邦客戶端
from fubon_client import fubon_client

# 🆕 導入台股名稱映射工具
from tw_stock_name_mapper import get_stock_name, tw_stock_mapper

# ==================== 配置 ====================
st.set_page_config(
    page_title="潛力股監控儀表板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 通用資料獲取函數 ====================
@st.cache_data(ttl=60)
def get_stock_data(symbols):
    """從富邦 API 獲取即時股票數據"""
    if not symbols: return {}
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def fetch_data():
        if not fubon_client.is_connected:
            await fubon_client.connect()
        quotes = await fubon_client.batch_get_quotes(symbols)
        return quotes
    
    try:
        return loop.run_until_complete(fetch_data())
    except Exception as e:
        st.error(f"獲取數據失敗: {e}")
        return {}
    finally:
        loop.close()

@st.cache_data(ttl=300)
def get_historical_data(symbol, days=90):
    """獲取歷史數據用於計算成長率"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def fetch_history():
        if not fubon_client.is_connected:
            await fubon_client.connect()
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        return await fubon_client.get_candles(symbol, from_date, to_date, timeframe="D")
    
    try:
        return loop.run_until_complete(fetch_history()) or []
    except:
        return []
    finally:
        loop.close()

def calculate_growth_rate(candles, period_days):
    """計算指定期間的成長率"""
    if not candles or len(candles) < 2: return 0.0
    try:
        latest = float(candles[-1]['close'])
        idx = -1 - period_days
        if abs(idx) > len(candles): idx = 0
        old = float(candles[idx]['close'])
        return round(((latest - old) / old) * 100, 2) if old > 0 else 0.0
    except:
        return 0.0

def calculate_ma(candles, period):
    """計算均線"""
    if not candles or len(candles) < period: return 0.0
    try:
        closes = [float(c['close']) for c in candles[-period:]]
        return round(sum(closes) / len(closes), 2)
    except:
        return 0.0

def calculate_vol_ma(candles, period):
    """計算均量"""
    if not candles or len(candles) < period: return 0
    try:
        vols = [float(c['volume']) for c in candles[-period:]]
        return int(sum(vols) / len(vols))
    except:
        return 0

import random

# ==================== MOCK DATA GENERATOR ====================
def _generate_mock_data(symbol):
    """Generate realistic mock data when API fails"""
    base_price = random.uniform(50, 800)
    chg = random.uniform(-5, 9.9)
    price = base_price * (1 + chg/100)
    
    # Generate mock history for indicators
    mock_ma5 = price * random.uniform(0.98, 1.02)
    mock_ma10 = price * random.uniform(0.95, 1.05)
    mock_ma20 = price * random.uniform(0.90, 1.10)
    mock_ma60 = price * random.uniform(0.85, 1.15)
    
    return {
        "code": symbol,
        "name": get_stock_name(symbol) or symbol,
        "price": round(price, 1),
        "chgpct": round(chg, 2),
        "ma5": round(mock_ma5, 1),
        "ma10": round(mock_ma10, 1), 
        "ma20": round(mock_ma20, 1),
        "ma60": round(mock_ma60, 1),
        "vol": random.randint(1000, 50000),
        "mv5": random.randint(1000, 50000), 
        "mv20": random.randint(1000, 50000),
        "wgrow": round(random.uniform(-2, 5), 1),
        "mgrow": round(random.uniform(-5, 10), 1), 
        "bgrow": round(random.uniform(-10, 20), 1),
        "is_mock": True
    }

# ==================== NEW SCANNER LOGIC ====================

SCAN_LIST_FAST = [
    '2330','2317','2454','2382','2308','2303','3711','2881','2882','2412',
    '2886','2891','2892','2884','2885','2002','1301','1303','1326','2207',
    '2357','2379','2395','3034','6505','2408','8021','8103','2313','3563',
    '3380','3466','3450','3518','6669','6770','3231','2618','3045','6488',
    '2049','4938','3037','2376','2327','6415','3481','2474','2337','2441',
    '2347','5483','6547','3702','2345','2353','2360','4904'
]





import asyncio
import time
import re
from datetime import datetime, timedelta
import streamlit as st


# ════════════════════════════════════════════
#  代號過濾：跳過 API 不支援的品種
# ════════════════════════════════════════════
def is_valid_stock(code: str) -> bool:
    """
    回傳 True = 正常股票，可以抓K線
    回傳 False = 跳過（ETF/特別股/REITs/新股）
    """
    # 含字母 → 特別股 (1101B)、REITs (01001T)、基金 (020038)
    if re.search(r'[A-Za-z]', code):
        return False
    # 6位以上數字 → 新型ETF (020038)
    if len(code) > 5:
        return False
    return True


# ════════════════════════════════════════════
#  核心 async 函式（全程單一 loop）
# ════════════════════════════════════════════
async def _scan_async(fubon_client, target_list: list, progress_cb=None) -> dict:

    # 過濾不支援品種
    supported = [c for c in target_list if is_valid_stock(c)]
    skipped   = [c for c in target_list if not is_valid_stock(c)]
    if skipped:
        print(f"[Filter] 跳過 {len(skipped)} 支不支援品種: {skipped[:5]}...")

    total = len(supported)
    data_map = {}

    # ── 連線 ────────────────────────────────
    await fubon_client.connect()

    # ── 階段1：批次報價 ──────────────────────
    BATCH_SIZE = 3
    all_quotes = {}
    chunks = [supported[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    for idx, chunk in enumerate(chunks):
        if progress_cb:
            progress_cb(idx / len(chunks) * 0.35)
        try:
            result = await fubon_client.batch_get_quotes(chunk)
            if result:
                all_quotes.update({k: v for k, v in result.items() if v})
        except Exception as e:
            print(f"[Quotes] chunk {idx} failed: {e}")
        await asyncio.sleep(1.2)

    print(f"[Quotes] {len(all_quotes)}/{total} 支有報價")

    # ── 階段2：K線 + 指標 ────────────────────
    from_date = (datetime.now() - timedelta(days=130)).strftime('%Y-%m-%d')
    to_date   = datetime.now().strftime('%Y-%m-%d')

    fail_streak = 0  # 連續失敗計數，超過門檻就重連

    for i, code in enumerate(supported):
        if progress_cb:
            progress_cb(0.35 + (i+1)/total * 0.65)

        quote = all_quotes.get(code)
        if not quote or not quote.get('price'):
            continue

        # ── 自動重試，最多3次 ──────────────
        hist = []
        for attempt in range(3):
            try:
                # 連續失敗5次以上 → 重連
                if fail_streak >= 5:
                    print(f"[Reconnect] 連續失敗 {fail_streak} 次，重新連線...")
                    await fubon_client.connect()
                    fail_streak = 0
                    await asyncio.sleep(2.0)

                hist = await fubon_client.get_candles(code, from_date, to_date, "D") or []

                if hist:
                    fail_streak = 0
                    break  # 成功，跳出重試
                else:
                    print(f"[{code}] 空K線 (attempt {attempt+1})")
                    await asyncio.sleep(1.5 * (attempt+1))

            except Exception as e:
                print(f"[{code}] K線失敗 attempt {attempt+1}: {e}")
                fail_streak += 1
                await asyncio.sleep(1.5 * (attempt+1))

        await asyncio.sleep(1.0)  # 每支間隔

        # ── 計算指標 ──────────────────────
        closes  = [float(c['close'])  for c in hist if c.get('close')]
        volumes = [float(c['volume']) for c in hist if c.get('volume')]

        def ma(n): return round(sum(closes[-n:])/n, 2) if len(closes) >= n else 0.0
        def mv(n): return round(sum(volumes[-n:])/n, 0) if len(volumes) >= n else 0.0

        price = float(quote.get('price', 0))
        chg   = float(quote.get('change_percent', 0))
        name  = quote.get('name', code)
        
        # Name Fallback
        if not name or name == code:
             # Try mapper
             mapped = get_stock_name(code)
             if mapped and mapped != code: name = mapped
             
             # Try API fetch if still code (as a last resort inside this loop)
             if not name or name == code:
                 try:
                     api_name = await fubon_client.get_stock_name(code)
                     if api_name: name = api_name
                 except: pass
        if not name: name = code
        
        # Zero Change Fix
        if chg == 0 and quote.get('prev_close') and price > 0:
             prev = float(quote.get('prev_close'))
             if prev > 0:
                 chg = round((price - prev) / prev * 100, 2)
                 
        # Growth Rate Calculation
        wgrow = calculate_growth_rate(hist, 5)
        mgrow = calculate_growth_rate(hist, 20)
        bgrow = calculate_growth_rate(hist, 60)

        data_map[code] = {
            'code': code, 'name': name,
            'price': price, 'chgpct': chg,
            'vol':  int(quote.get('volume', 0)),
            'ma5':  ma(5),  'ma10': ma(10),
            'ma20': ma(20), 'ma60': ma(60),
            'mv5':  mv(5),  'mv20': mv(20),
            'wgrow': wgrow, 'mgrow': mgrow, 'bgrow': bgrow, # Compatibility
            'bars': len(closes),  # 除錯用
        }

    return data_map


# ════════════════════════════════════════════
#  對外接口（Streamlit 呼叫這個）
# ════════════════════════════════════════════
def prepare_scanner_data(target_list: list) -> dict:
    """取代原本的 prepare_scanner_data，drop-in 替換"""

    progress = st.progress(0)
    status   = st.empty()

    def cb(val):
        progress.progress(min(float(val), 1.0))
        pct = int(val * 100)
        status.text(f"{'📡 報價中' if pct < 35 else '📊 K線+計算中'}... {pct}%")

    # ── 全程單一 loop ──────────────────────
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data_map = {}
    try:
        data_map = loop.run_until_complete(
            _scan_async(fubon_client, target_list, cb)
        )
    except Exception as e:
        st.error(f"掃描錯誤: {e}")
    finally:
        loop.close()

    progress.progress(1.0)

    # 結果統計
    valid   = sum(1 for d in data_map.values() if d.get('ma60', 0) > 0)
    no_ma   = sum(1 for d in data_map.values() if d.get('ma60', 0) == 0)
    skipped = len([c for c in target_list if not is_valid_stock(c)])

    status.text(
        f"✅ 完成｜MA有效: {valid} 支｜MA=0: {no_ma} 支｜"
        f"跳過ETF/特別股: {skipped} 支"
    )
    if no_ma > 0:
        st.warning(f"⚠️ {no_ma} 支股票數據不足 (MA=0)，已過濾。")
        
    return data_map




# ==================== HTML TEMPLATE ====================

HTML_Template_Start = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>潛力股起漲偵測儀 v3 (Pro)</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

:root {
  --bg:      #070a10;
  --bg2:     #0c1018;
  --bg3:     #111622;
  --bg4:     #171e2e;
  --border:  #1c2438;
  --border2: #263048;
  --accent:  #f0b429;
  --accent2: #e8520a;
  --green:   #10d49a;
  --red:     #f04060;
  --blue:    #4080ff;
  --text:    #dde3f0;
  --text2:   #7a8aaa;
  --text3:   #4a5a7a;
  --mono:    'JetBrains Mono', monospace;
  --sans:    'Noto Sans TC', sans-serif;
  --glow:    0 0 20px rgba(240,180,41,0.15);
}

*{margin:0;padding:0;box-sizing:border-box;}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}

/* Ambient glow */
body::after {
  content:'';
  position:fixed;
  width:600px; height:600px;
  background: radial-gradient(circle, rgba(240,180,41,0.04) 0%, transparent 70%);
  top:-200px; right:-200px;
  pointer-events:none; z-index:0;
}

.container { max-width:1100px; margin:0 auto; padding:20px 14px; position:relative; z-index:1; }

/* ── Header ─────────────────── */
.header { margin-bottom:28px; text-align:center; }
.header h1 { font-size:28px; font-weight:900; letter-spacing:4px; margin-bottom:6px; background:linear-gradient(135deg,var(--text),#fff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.badge-pro { display:inline-block; padding:3px 8px; border-radius:4px; background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#000; font-family:var(--mono); font-weight:700; font-size:10px; vertical-align:middle; margin-left:8px; }
.subtitle { font-family:var(--mono); font-size:11px; color:var(--text2); letter-spacing:3px; }

/* ── Tabs ─────────────────── */
.main-tabs { display:flex; gap:6px; margin-bottom:24px; justify-content:center; }
.main-tab {
  padding:10px 24px; border-radius:20px;
  border:1px solid var(--border); background:var(--bg2);
  color:var(--text2); font-size:13px; cursor:pointer; transition:all .2s;
  font-family:var(--mono); display:flex; align-items:center; gap:8px;
}
.main-tab:hover { border-color:var(--text2); color:var(--text); }
.main-tab.active { border-color:var(--accent); color:var(--accent); background:rgba(240,180,41,0.08); box-shadow:0 0 15px rgba(240,180,41,0.1); }

/* ── Sections ─────────────────── */
.section { display:none; animation:fadeIn .4s ease; }
.section.active { display:block; }
@keyframes fadeIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }

/* ── Search Bar ─────────────────── */
.search-box {
  background:var(--bg2); border:1px solid var(--border);
  border-radius:12px; padding:20px; text-align:center;
  max-width:600px; margin:0 auto 30px auto;
}
.search-input-wrap {
  position:relative; display:flex; align-items:center;
  background:var(--bg3); border:1px solid var(--border2);
  border-radius:8px; padding:4px 14px;
  transition:border-color .2s;
}
.search-input-wrap:focus-within { border-color:var(--accent); }
.search-input-wrap input {
  flex:1; background:transparent; border:none; outline:none;
  color:var(--text); font-size:15px; padding:10px 0;
  font-family:var(--sans);
}

/* ── Result Card ─────────────────── */
.rcard {
  background:var(--bg2); border:1px solid var(--border);
  border-radius:12px; padding:20px;
  margin-bottom:14px; position:relative; overflow:hidden;
  transition:transform .2s, box-shadow .2s;
}
.rcard:hover { transform:translateY(-2px); box-shadow:0 6px 20px rgba(0,0,0,0.3); }
.rcard.S { border-color:rgba(16,212,154,0.45); background:linear-gradient(135deg,rgba(16,212,154,0.06),var(--bg2) 60%); }
.rcard.A { border-color:rgba(240,180,41,0.4); background:linear-gradient(135deg,rgba(240,180,41,0.05),var(--bg2) 60%); }

.rcard-top { display:flex; gap:18px; align-items:flex-start; margin-bottom:16px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:14px; }
.donut { width:70px; height:70px; position:relative; flex-shrink:0; }
.donut svg { transform:rotate(-90deg); width:100%; height:100%; }
.donut-num {
  position:absolute; inset:0;
  display:flex; align-items:center; justify-content:center;
  font-family:var(--mono); font-size:18px; font-weight:700;
}

.rcard-info { flex:1; min-width:0; }
.rcard-name { font-size:20px; font-weight:700; display:flex; align-items:baseline; gap:10px; padding-right: 50px; }
.rcard-code { font-family:var(--mono); font-size:14px; color:var(--text2); font-weight:400; }
.rcard-meta { font-family:var(--mono); font-size:13px; color:var(--text2); display:flex; gap:12px; align-items:center; margin-top:6px; }
.price-val { font-size:16px; color:var(--text); font-weight:700; }
.up { color:var(--red); } .dn { color:var(--green); }
.rcard-ma { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }
.ma-pill { padding:3px 8px; border-radius:4px; font-size:11px; font-family:var(--mono); font-weight:700; opacity:0.9; }

.grade-box {
  position:absolute; top:20px; right:20px;
  width:40px; height:40px; border-radius:8px;
  display:flex; align-items:center; justify-content:center;
  font-family:var(--mono); font-size:20px; font-weight:900;
}
.grade-box.S { background:rgba(16,212,154,0.18); color:var(--green); border:1px solid var(--green); box-shadow:0 0 15px rgba(16,212,154,0.2); }
.grade-box.A { background:rgba(240,180,41,0.18); color:var(--accent); border:1px solid var(--accent); box-shadow:0 0 15px rgba(240,180,41,0.2); }
.grade-box.B { background:rgba(64,128,255,0.15); color:var(--blue); border:1px solid var(--blue); }
.grade-box.C { background:rgba(240,64,96,0.1); color:var(--red); border:1px solid var(--red); }

.sig-row { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:14px; }
.sig { background:var(--bg3); border-radius:8px; padding:10px; text-align:center; border:1px solid rgba(255,255,255,0.03); }
.sig-icon { font-size:18px; margin-bottom:4px; }
.sig-name { font-size:10px; color:var(--text2); margin-bottom:2px; }
.sig-val { font-family:var(--mono); font-size:14px; font-weight:700; }
.sig-val.ok { color:var(--green); } .sig-val.md { color:var(--accent); } .sig-val.no { color:var(--red); }

.verdict {
  background:var(--bg3); border-radius:8px; padding:12px 16px;
  font-size:12px; line-height:1.7; color:var(--text2);
  border-left:3px solid var(--accent); position:relative;
}
.verdict strong { color:var(--text); }

/* ── Watchlist ─────────────────── */
.wl-item {
  background:var(--bg2); border:1px solid var(--border);
  border-radius:10px; padding:14px 18px;
  margin-bottom:10px; display:flex; align-items:center; gap:16px;
  transition:all .2s;
}
.wl-item:hover { border-color:var(--border2); background:var(--bg3); }
.wl-grade { width:32px; height:32px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-weight:900; font-family:var(--mono); flex-shrink:0; }
.wl-grade.S { background:rgba(16,212,154,0.2); color:var(--green); }
.wl-grade.A { background:rgba(240,180,41,0.2); color:var(--accent); }
.wl-body { flex:1; }
.wl-name { font-size:15px; font-weight:700; margin-bottom:2px; }
.wl-meta { font-family:var(--mono); font-size:11px; color:var(--text2); }

/* ── Utilities ────────────────── */
.btn { border:none; padding:6px 14px; border-radius:6px; font-size:12px; cursor:pointer; font-weight:700; transition:all .2s; }
.btn-ghost { background:transparent; border:1px solid var(--border2); color:var(--text2); }
.btn-ghost:hover { boder-color:var(--text); color:var(--text); background:var(--bg4); }
.btn-add { color:var(--green); border-color:rgba(16,212,154,0.3); }
.btn-add:hover { background:rgba(16,212,154,0.1); border-color:var(--green); }

.status-bar { margin-bottom:16px; display:flex; gap:10px; flex-wrap:wrap; }
.badge { background:var(--bg3); padding:4px 10px; border-radius:20px; font-size:11px; color:var(--text2); border:1px solid var(--border); display:flex; gap:6px; }
.badge .v { color:var(--text); font-weight:700; font-family:var(--mono); }

/* Spinner */
.loading { text-align:center; padding:40px; color:var(--text2); font-family:var(--mono); font-size:12px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>全台股 AI 偵測儀 <div class="badge-pro">PRO v3.0</div></h1>
    <div class="subtitle">AUTOMATED MARKET SCANNER & ANALYSIS</div>
  </div>

  <div class="main-tabs">
    <div class="main-tab active" onclick="switchTab('manual')" id="tab-btn-manual">🔍 智能搜尋</div>
    <div class="main-tab" onclick="switchTab('scan')" id="tab-btn-scan">🔭 全域掃描</div>
    <div class="main-tab" onclick="switchTab('watchlist')" id="tab-btn-watchlist">⭐ 監控名單</div>
  </div>

  <!-- Manual Tab -->
  <div id="tab-manual" class="section active">
    <!-- Search Box is Visual Only, logic driven by Streamlit -->
    <div class="search-box">
      <div style="font-size:13px;color:var(--text2);margin-bottom:12px;">輸入股票代號以進行深度分析</div>
      <div class="search-input-wrap">
        <span style="font-size:18px;margin-right:10px">🔍</span>
        <input type="text" id="search-code" placeholder="請使用上方白色輸入框查詢..." readonly style="opacity:0.7;cursor:not-allowed">
      </div>
    </div>
    <div id="search-result"></div>
  </div>

  <!-- Scan Tab -->
  <div id="tab-scan" class="section">
    <div style="text-align:center;margin-bottom:20px;color:var(--text2);font-size:12px">
      請使用頂部控制台按鈕 (快速/標準/完整) 啟動掃描任務
    </div>
    <div id="scan-log" style="text-align:center;font-family:var(--mono);font-size:12px;color:var(--accent);margin-bottom:16px;min-height:20px"></div>
    <div id="scan-results"></div>
  </div>

  <!-- Watchlist Tab -->
  <div id="tab-watchlist" class="section">
    <div class="status-bar" style="justify-content:space-between">
      <div id="wl-stats" style="display:flex;gap:8px"></div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-ghost" onclick="exportWL()">📤 匯出</button>
        <button class="btn btn-ghost" onclick="clearWL()" style="color:var(--red);border-color:rgba(255,71,87,0.3)">清空</button>
      </div>
    </div>
    <div id="watchlist-area"></div>
  </div>
</div>

"""

HTML_Template_Script = """
<script>
// INJECTED DATA
const PRELOADED_DATA = /* DATA_PLACEHOLDER */;
const PRELOADED_MODE = '/* MODE_PLACEHOLDER */';

// ════════════════════════════════
//  SCORING ENGINE
// ════════════════════════════════
function computeScore(d) {
  let s = 0, sigs = {};

  // ① 均線多頭排列 (30)
  const maOk = d.ma5>d.ma10 && d.ma10>d.ma20 && d.ma20>d.ma60;
  const pAbove = d.price>d.ma5 && d.price>d.ma10 && d.price>d.ma20 && d.price>d.ma60;
  let ms = 0;
  if(maOk) ms+=20; else if(d.ma5>d.ma10 && d.ma5>d.ma20) ms+=10;
  if(pAbove) ms+=8; if(d.ma5>d.ma20) ms+=2;
  s+=ms;
  sigs.ma={score:ms,max:30,label:'均線排列',icon:'📐',
    cls:ms>=20?'ok':ms>=10?'md':'no',
    tip:maOk?'完整多頭排列✓':d.ma5>d.ma10?'短線向上':'未排列'};

  // ② 量能 (30)
  const vr = d.mv20>0 ? d.mv5/d.mv20 : 1;
  const mv5up = d.mv5>d.mv20;
  let vs=0;
  if(mv5up) vs+=15;
  if(vr>=2) vs+=15; else if(vr>=1.5) vs+=10; else if(vr>=1.2) vs+=5;
  s+=vs;
  sigs.vol={score:vs,max:30,label:'量能爆發',icon:'📊',
    cls:vs>=20?'ok':vs>=10?'md':'no',
    tip:`MV5/MV20=${vr.toFixed(1)}x`};

  // ③ 成長加速 (25)
  const acc = d.bgrow>d.mgrow && d.mgrow>d.wgrow;
  const allP = d.wgrow>0 && d.mgrow>0 && d.bgrow>0;
  let gs=0;
  if(acc) gs+=15; if(allP) gs+=5; if(d.mgrow>=5||d.bgrow>=10) gs+=5;
  s+=gs;
  sigs.grow={score:gs,max:25,label:'成長加速',icon:'📈',
    cls:gs>=18?'ok':gs>=10?'md':'no',
    tip:`週${d.wgrow}→月${d.mgrow}→雙月${d.bgrow}%`};

  // ④ 均線擴散 (15)
  const lag60 = d.ma60>0?(d.price-d.ma60)/d.ma60*100:0;
  const gap20 = d.ma20>0?(d.ma5-d.ma20)/d.ma20*100:0;
  let ds=0;
  if(lag60>10&&lag60<100) ds+=8; else if(lag60>5) ds+=4;
  if(gap20>5&&gap20<30) ds+=7; else if(gap20>2) ds+=3;
  s+=ds;
  sigs.spread={score:ds,max:15,label:'均線擴散',icon:'📡',
    cls:ds>=12?'ok':ds>=6?'md':'no',
    tip:`距MA60:+${lag60.toFixed(0)}%`};

  const grade = s>=80?'S':s>=65?'A':s>=45?'B':'C';
  const gc    = grade==='S'?'var(--green)':grade==='A'?'var(--accent)':grade==='B'?'var(--blue)':'var(--red)';
  return {total:s, grade, gc, sigs, lag60, gap20, vr};
}

function genVerdict(d, r) { 
  const lines = [];
  if(r.grade==='S') lines.push(`<strong>🚀 極強起漲訊號！</strong> 評分${r.total}，四大訊號均到位。`);
  else if(r.grade==='A') lines.push(`<strong>⭐ 強勢潛力股</strong>，評分${r.total}，主要訊號已出現。`);
  else if(r.grade==='B') lines.push(`<strong>👀 值得觀察</strong>，評分${r.total}，部分訊號成立。`);
  else lines.push(`<strong>⏳ 尚未起漲</strong>，評分${r.total}，訊號不足。`);

  if(r.sigs.ma.score>=20) lines.push('✅ 均線完整多頭排列。');

  if(r.sigs.vol.score>=20) lines.push(`✅ 量能爆發（${r.vr.toFixed(1)}x）。`);
  if(r.sigs.grow.score>=15) lines.push('✅ 營收/股價成長加速中。');
  

  // 乖離率判斷 (Refined Logic)
  const bias = d.ma20 > 0 ? (d.price - d.ma20)/d.ma20*100 : 0;
  // 量能分數轉換 (>=25分即符合有量)
  const volScore = r.sigs.vol.score;
  const isStrong = r.grade === 'S' || r.grade === 'A';

  if(isStrong && volScore >= 25) {
      if(bias >= -2 && bias <= 3) {
          lines.push(`<strong>🎯 完美買點：</strong> 有量有價 + 低成本 (${bias.toFixed(2)}%)`);
      } else if (bias > 3 && bias <= 8) {
          lines.push(`<strong>🚀 強勢動能：</strong> 趨勢持續，適合分批 (${bias.toFixed(2)}%)`);
      } else if (bias > 8) {
          lines.push(`<strong>⚠️ 過熱噴發：</strong> 乖離過大，勿追高 (${bias.toFixed(2)}%)`);
      } else {
          lines.push(`<strong>📉 轉弱警訊：</strong> 量大但跌破均線 (${bias.toFixed(2)}%)`);
      }
  } else if (isStrong) {
      lines.push(`<strong>☁️ 虛漲警訊：</strong> 有價無量，動能不足 (${bias.toFixed(2)}%)`);
  } else {
      lines.push(`<strong>💤 觀望：</strong> 不符合潛力特徵 (${bias.toFixed(2)}%)`);
  }
  
  return lines.join('<br>');
}

function renderCard(d, r, showAdd=true) {
  const C = 2*Math.PI*24, off = C*(1-r.total/100);
  const chgCls = (d.chgpct||0)>=0?'up':'dn';
  const chgSign = (d.chgpct||0)>=0?'+':'';
  const maPills = [
    {l:'MA5',v:d.ma5,c:'rgba(240,180,41,0.2)',t:'var(--accent)'},
    {l:'MA10',v:d.ma10,c:'rgba(64,128,255,0.2)',t:'var(--blue)'},
    {l:'MA20',v:d.ma20,c:'rgba(16,212,154,0.15)',t:'var(--green)'},
    {l:'MA60',v:d.ma60,c:'rgba(255,255,255,0.06)',t:'var(--text2)'},
  ].filter(m=>m.v>0).map(m=>`<span class="ma-pill" style="background:${m.c};color:${m.t}">${m.l}:${m.v}</span>`).join('');

  const addBtn = showAdd
    ? `<button class="btn btn-ghost btn-add" style="margin-top:10px" onclick='addToWatchlist(${JSON.stringify({...d,score:r.total,grade:r.grade})})'>＋ 加入監控名單</button>`
    : '';

  return `
<div class="rcard ${r.grade}">
  <div class="grade-box ${r.grade}">${r.grade}</div>
  <div class="rcard-top">
    <div class="donut">
      <svg width="70" height="70" viewBox="0 0 60 60">
        <circle cx="30" cy="30" r="24" fill="none" stroke="var(--border2)" stroke-width="4"/>
        <circle cx="30" cy="30" r="24" fill="none" stroke="${r.gc}" stroke-width="4"
          stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" stroke-linecap="round"/>
      </svg>
      <div class="donut-num" style="color:${r.gc}">${r.total}</div>
    </div>
    <div class="rcard-info">
      <div class="rcard-name">
        ${d.name} <span class="rcard-code">${d.code}</span>
        <span class="price-val" style="margin-left:auto;color:${chgCls==='up'?'var(--red)':'var(--green)'}">¥${d.price}</span>
        <span class="${chgCls}" style="font-size:14px;font-weight:700">${chgSign}${(d.chgpct||0).toFixed(2)}%</span>
      </div>
      <div class="rcard-ma">${maPills}</div>
    </div>
  </div>
  <div class="sig-row">
    ${Object.values(r.sigs).map(sg=>`
      <div class="sig" title="${sg.tip}">
        <div class="sig-icon">${sg.icon}</div>
        <div class="sig-name">${sg.label}</div>
        <div class="sig-val ${sg.cls}">${sg.score}/${sg.max}</div>
      </div>`).join('')}
  </div>
  <div class="verdict">${genVerdict(d,r)}</div>
  ${addBtn}
</div>`;
}

function switchTab(tab) {
  ['manual','scan','watchlist'].forEach(t=>{
    const el = document.getElementById('tab-'+t);
    const btn = document.getElementById('tab-btn-'+t);
    if(el) { el.classList.remove('active'); el.style.display = t===tab?'block':'none'; }
    if(btn) btn.classList.toggle('active', t===tab);
    if(t===tab) setTimeout(()=>el.classList.add('active'),10);
  });
  if(tab==='watchlist') renderWatchlist();
}

function searchStock() {
  const code = document.getElementById('search-code').value.trim();
  if(!code) return;
  if(PRELOADED_DATA && PRELOADED_DATA[code]) {
    const d = PRELOADED_DATA[code];
    const r = computeScore(d);
    document.getElementById('search-result').innerHTML = renderCard(d,r,true);
  } else {
    document.getElementById('search-result').innerHTML = `<div style="padding:40px;text-align:center;color:var(--text2)">⚠️ 找不到 ${code} 的數據，請確認代號正確或嘗試重新搜尋。</div>`;
  }
}

function startScan() {
  const list = Object.values(PRELOADED_DATA);
  if(!list.length) return;
  
  const results = [];
  document.getElementById('scan-log').innerHTML = `正在分析 ${list.length} 支即時運算數據...`;
  
  list.forEach(d => {
    const r = computeScore(d);
    if(r.total >= 0) { results.push({d,r}); }
  });
  
  results.sort((a,b) => b.r.total - a.r.total);

  const sCount = results.filter(x=>x.r.grade==='S').length;
  const aCount = results.filter(x=>x.r.grade==='A').length;

  document.getElementById('scan-results').innerHTML = `
    <div class="status-bar" style="justify-content:center; gap:8px;">
      <div class="badge"><span>總數</span><span class="v">${results.length}</span></div>
      <div class="badge" style="border-color:var(--green);color:var(--green)"><span>S級</span><span class="v">${sCount}</span></div>
      <div class="badge" style="border-color:var(--accent);color:var(--accent)"><span>A級</span><span class="v">${aCount}</span></div>
      <button class="btn btn-ghost" onclick="exportScanResults()" style="height:26px;padding:0 12px;margin-left:8px;border-color:var(--accent);color:var(--accent)">📥 匯出報表</button>
    </div>
    ${results.map(i => renderCard(i.d, i.r)).join('')}
  `;
  document.getElementById('scan-log').closest('.section').scrollTop = 0;
}

function exportScanResults() {
  const list = Object.values(PRELOADED_DATA);
  if(!list.length) { alert('沒有數據可匯出'); return; }
  
  const results = list.map(d => ({d, r: computeScore(d)})).sort((a,b) => b.r.total - a.r.total);
  
  let csv = '\\uFEFF代號,名稱,現價,漲跌幅,評分,等級,MA5,MA10,MA20,MA60,均線排列,量能,成長,乖離率,操作建議\\n';
  results.forEach(item => {
    const d = item.d;
    const r = item.r;
    
    // 乖離率與操作建議 (Refined Logic)
    const bias = d.ma20 > 0 ? ((d.price - d.ma20)/d.ma20*100).toFixed(2) : 0;
    const isStrong = r.grade === 'S' || r.grade === 'A';
    const volScore = r.sigs.vol.score;
    let action = '';
    
    if(isStrong && volScore >= 25) {
        if(bias >= -2 && bias <= 3) {
            action = '🎯 完美買點 (有量有價+低成本)';
        } else if (bias > 3 && bias <= 8) {
            action = '🚀 強勢動能 (適合分批)';
        } else if (bias > 8) {
            action = '⚠️ 過熱噴發 (勿追高)';
        } else {
            action = '📉 轉弱警訊';
        }
    } else if (isStrong) {
        action = '☁️ 虛漲 (有價無量)';
    } else {
        action = '💤 觀望';
    }
    
    csv += `${d.code},${d.name},${d.price},${d.chgpct}%,${r.total},${r.grade},${d.ma5},${d.ma10},${d.ma20},${d.ma60},${r.sigs.ma.score},${r.sigs.vol.score},${r.sigs.grow.score},${bias}%,${action}\\n`;
  });
  
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `scan_report_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// Watchlist Logic
function loadWL(){ try { return JSON.parse(localStorage.getItem('wl_v3')||'[]'); } catch(e){ return []; } }
function saveWL(list){ try { localStorage.setItem('wl_v3', JSON.stringify(list)); } catch(e){} renderWatchlist(); }
function addToWatchlist(d){
  const list=loadWL();
  if(list.find(i=>i.code===d.code)){ alert('已在名單中！'); return; }
  list.push({...d, addedAt:new Date().toLocaleDateString('zh-TW')});
  saveWL(list);
  alert('✨ 已加入監控名單！');
}
function clearWL(){ if(confirm('確定清空所有名單？')) saveWL([]); }
function exportWL() {
  const list=loadWL();
  if(!list.length){alert('名單是空的');return;}
  const csv = '\\uFEFF代號,名稱,評分,等級,加入時間\\n' + list.map(i=>`${i.code},${i.name},${i.score},${i.grade},${i.addedAt}`).join('\\n');
  const a = document.createElement('a');
  a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download='stocks_watchlist.csv';
  a.click();
}

function renderWatchlist(){
  const list=loadWL();
  const area=document.getElementById('watchlist-area');
  
  const grades=['S','A','B','C'].map(g=>({g,n:list.filter(i=>i.grade===g).length}));
  document.getElementById('wl-stats').innerHTML = grades.filter(x=>x.n).map(x=>`
    <div class="badge"><span>${x.g}級</span><span class="v">${x.n}</span></div>`).join('');

  if(!list.length){ area.innerHTML='<div class="loading">📝 監控名單是空的<br>請從掃描結果中點擊「加入」</div>'; return; }
  
  area.innerHTML = list.map(item=>`
    <div class="wl-item">
      <div class="wl-grade ${item.grade||'C'}">${item.grade||'?'}</div>
      <div class="wl-body">
        <div class="wl-name">${item.name} <span style="font-weight:400;color:var(--text2);font-size:12px;margin-left:4px">${item.code}</span></div>
        <div class="wl-meta">¥${item.price||'--'} | 評分 ${item.score} | 加入: ${item.addedAt}</div>
      </div>
      <div>
         <a href="https://tw.stock.yahoo.com/quote/${item.code}" target="_blank"><button class="btn btn-ghost">圖表</button></a>
         <button class="btn btn-ghost" style="color:var(--red);border:none" onclick="saveWL(loadWL().filter(i=>i.code!='${item.code}'))">✕</button>
      </div>
    </div>
  `).join('');
}

// Auto Init
if(PRELOADED_MODE === 'scan') {
  switchTab('scan');
  startScan();
} else if (PRELOADED_MODE === 'manual') {
  switchTab('manual');
  const keys = Object.keys(PRELOADED_DATA);
  if(keys.length === 1) {
     document.getElementById('search-code').value = keys[0];
     searchStock();
  }
}
</script>
</body>
</html>
"""

# ==================== MAIN LOGIC ====================

# Layout Containers
search_container = st.container()
html_container = st.container()

with search_container:
    # Layout selection
    st.markdown("### 🔍 股票 AI 偵測")
    
    # 搜尋區
    col_search_1, col_search_2 = st.columns([3, 1])
    with col_search_1:
        search_input = st.text_input("輸入股票代號", label_visibility="collapsed", placeholder="輸入代號 (如 2330)...", key="main_search")
    with col_search_2:
        search_btn = st.button("🚀 立即分析", type="primary", use_container_width=True)

    st.markdown("---")
    
    # 掃描區
    st.markdown("#### 🔭 全市場掃描")
    col_scan_1, col_scan_2, col_scan_3 = st.columns(3)
    
    with col_scan_1:
        scan_fast_btn = st.button("⚡ 快速掃描 (60支)", use_container_width=True, help="鎖定權值股與熱門股，約需 30 秒")
    with col_scan_2:
        scan_std_btn = st.button("📊 標準掃描 (150支)", use_container_width=True, help="擴大範圍至中型潛力股，約需 2 分鐘")
    with col_scan_3:
        scan_full_btn = st.button("🌐 完整掃描 (全部)", use_container_width=True, help="掃描所有上市櫃股票，時間較長，約需 10 分鐘以上")

    if 'scanner_data' not in st.session_state:
        st.session_state.scanner_data = {}
    if 'scanner_mode' not in st.session_state:
        st.session_state.scanner_mode = "manual"

    # Handle Search
    if search_btn and search_input:
        with st.spinner(f"正在連線富邦 API 獲取 {search_input} 數據..."):
            st.session_state.scanner_data = {} 
            new_data = prepare_scanner_data([search_input])
            if new_data:
                st.session_state.scanner_data = new_data
                st.session_state.scanner_mode = "manual"
            else:
                st.error(f"❌ 找不到股票 {search_input}")

    # Handle Scans
    target_list = []
    
    if scan_fast_btn:
        target_list = SCAN_LIST_FAST
        st.session_state.scanner_mode = "scan"
        
    elif scan_std_btn:
        # 嘗試擴充標準清單
        try:
             all_sym = tw_stock_mapper.get_all_symbols() # 嘗試獲取所有
             # Filter out '00' ETFs
             all_sym = [s for s in all_sym if not s.startswith('00')]
             # 如果成功，取前 150 個 (加上快速清單去重)
             if all_sym:
                 target_list = list(set(SCAN_LIST_FAST + all_sym[:150]))
             else:
                 target_list = SCAN_LIST_FAST # Fallback
        except:
             target_list = SCAN_LIST_FAST
        st.session_state.scanner_mode = "scan"
        

    elif scan_full_btn:
        # 完整掃描 - 改為真正的完整掃描 (所有上市櫃股票)
        try:
            # 1. 嘗試從 API 獲取所有股票清單 (如果 mapper 允許)
            all_sym = tw_stock_mapper.get_all_symbols()
            
            # 2. 如果數量太少 (例如少於 500)，可能是因為 mapper 只有部分資料，嘗試合併預定義列表
            # 通常台股上市櫃約 1700-1800 支
            
            # 手動補充重要的科技權值股，以防 mapper 遺漏
            tech_weights = [
                '2330', '2317', '2454', '2308', '2303', '2382', '2357', '2301', '3231', '3008',
                '2379', '3711', '3037', '3034', '2353', '2327', '2324', '4938', '6669', '3443',
                '3035', '3017', '2368', '2412', '3045', '4904', '2337', '2371', '1216', '1101'
            ]
            
            # 合併並去重
            full_list = all_sym if all_sym else []
            full_list.extend(tech_weights)
            full_list = sorted(list(set(full_list)))
            
            # 3. 過濾非股票代碼 (ETF 00開頭, 權證等) - 這裡再次把關，雖然 prepare_scanner 也有做
            full_list = [s for s in full_list if not s.startswith('00') and len(s) == 4]
            
            if full_list:
                # 這裡不再限制 500 支，但給予使用者提示
                st.warning(f"⚠️ 啟動全市場掃描，共 {len(full_list)} 支股票。預計耗時較長，請耐心等待 (約 15-20 分鐘)。")
                target_list = full_list
            else:
                target_list = SCAN_LIST_FAST
                st.error("無法獲取股票清單，切換為快速掃描。")
                
        except Exception as e:
            st.error(f"獲取清單失敗: {e}")
            target_list = SCAN_LIST_FAST
        st.session_state.scanner_mode = "scan"
            
    if target_list:
        with st.spinner(f"正在掃描 {len(target_list)} 支股票..."):
            data = prepare_scanner_data(target_list)
            st.session_state.scanner_data = data
    
with html_container:
    # 這裡我們稍微修改 HTML 模板中的 input 為唯讀，或者添加提示
    # 因為搜尋實際上是透過 Streamlit 觸發的
    

    # Inject data 
    try:
        # Prevent JSON serialization errors with NaN/Inf values
        import math
        def sanitize_json(obj):
            if isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return 0.0
            elif isinstance(obj, dict):
                return {k: sanitize_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_json(i) for i in obj]
            return obj
            

        json_data = json.dumps(sanitize_json(st.session_state.scanner_data), ensure_ascii=False) # Ensure ASCII false to support Chinese
    except Exception as e:
        print(f"JSON Error: {e}")
        json_data = "{}"
        
    mode_str = st.session_state.scanner_mode
    
    # 這裡我們不使用 quotes 包裹 JSON 字串，而是直接替換成物件字面量，避開 JSON.parse 的問題
    # 在 HTML_Template_Script 中，我們原本是 JSON.parse('/* DATA_PLACEHOLDER */');
    # 現在我們將它修改為 /* DATA_PLACEHOLDER */; 直接讓 JS 解析物件
    
    # 修改 Template Script 確保格式正確
    script_content = HTML_Template_Script.replace("JSON.parse('/* DATA_PLACEHOLDER */')", "/* DATA_PLACEHOLDER */")
    script_content = script_content.replace("/* DATA_PLACEHOLDER */", json_data)
    script_content = script_content.replace("/* MODE_PLACEHOLDER */", mode_str)
    
    final_html = HTML_Template_Start + script_content

    # Add visual cue script

    if mode_str == 'manual' and st.session_state.scanner_data:
        current_code = list(st.session_state.scanner_data.keys())[0]
        final_html = final_html.replace(
            "</body>", 
            f"""
            <script>
            setTimeout(function(){{
                const el = document.getElementById('search-code');
                if(el) {{
                    el.value = '{current_code}';
                    el.setAttribute('readonly', true); // Make it readonly to encourage using Streamlit input
                    el.style.opacity = '0.7';
                    el.placeholder = '請使用上方白色搜尋框';
                    searchStock();
                }}
                const res = document.getElementById('search-result');
            }}, 200);
            </script>
            </body>
            """
        )
    
    components.html(final_html, height=1200, scrolling=True)

