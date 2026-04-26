import asyncio
import re
import json
import httpx
from datetime import datetime

html_file = "index.html"
# 0050 近期新進成分股名單
NEW_STOCKS = ["3037", "2344", "2368", "2449", "7769"]

etf_base_data = {
    '00981A': {
        'name': '統一台股增長', 'price': 27.80, 'change': '+4.43%', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護', 'tech': '高於週VWAP'},
            {'id': '2454', 'name': '聯發科', 'weight': 5.20, 'chips': '法人買超', 'tech': '築底起飛'},
            {'id': '2383', 'name': '台光電', 'weight': 4.80, 'chips': '主動認養', 'tech': '強勢噴發'},
            {'id': '3017', 'name': '奇鋐', 'weight': 4.30, 'chips': 'AI伺服器', 'tech': '量增突破'},
            {'id': '2345', 'name': '智邦', 'weight': 4.10, 'chips': '投信連買', 'tech': '仰角攻擊'},
            {'id': '3324', 'name': '雙鴻', 'weight': 3.90, 'chips': '散熱大廠', 'tech': '盤整向上'},
            {'id': '2308', 'name': '台達電', 'weight': 3.50, 'chips': '長線佈局', 'tech': '突破頸線'},
            {'id': '2317', 'name': '鴻海', 'weight': 3.20, 'chips': '外資吸納', 'tech': '上升通道'}
        ]
    },
    '00992A': {
        'name': '群益科技創新', 'price': 16.93, 'change': '+1.62%', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼', 'tech': '高於週VWAP'},
            {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼', 'tech': '多頭排列'},
            {'id': '3105', 'name': '穩懋', 'weight': 4.50, 'chips': '跌深反彈', 'tech': '帶量長紅'},
            {'id': '6223', 'name': '旺矽', 'weight': 4.20, 'chips': '融資減肥', 'tech': '回測支撐'},
            {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': '法人回補', 'tech': '站穩三線'},
            {'id': '6515', 'name': '穎崴', 'weight': 3.50, 'chips': '特定買盤', 'tech': '三角收斂'}
        ]
    },
    '0050': {
        'name': '元大台灣50', 'price': 195.0, 'change': '+1.2%', 'scale': '4,500 億', 'topWeight': '63.17%', 'vwap': '權值護盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 63.17, 'chips': '外資認養', 'tech': '權值霸主'},
            {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '主力連掃', 'tech': '多頭排列'},
            {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '法人加位', 'tech': '低檔反彈'},
            {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': '大戶佈局', 'tech': '季線支撐'},
            {'id': '3711', 'name': '日月光投控', 'weight': 1.58, 'chips': '封測龍頭', 'tech': '帶量突破'},
            {'id': '3037', 'name': '欣興', 'weight': 1.20, 'chips': 'ABF龍頭', 'tech': '新進成員'},
            {'id': '2344', 'name': '華邦電', 'weight': 0.80, 'chips': '記憶體熱', 'tech': '新進成員'},
            {'id': '2368', 'name': '金像電', 'weight': 0.60, 'chips': '伺服器版', 'tech': '新進成員'},
            {'id': '2449', 'name': '京元電子', 'weight': 0.60, 'chips': '測試熱門', 'tech': '新進成員'}
        ]
    }
}

async def fetch_yahoo_kline(symbol, suffix, client):
    full_symbol = f"{symbol}{suffix}" if "." not in symbol else symbol
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{full_symbol}?interval=1d&range=2mo"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = await client.get(url, headers=headers, timeout=15.0)
        data = resp.json()
        if data and 'chart' in data and data['chart']['result']:
            res = data['chart']['result'][0]
            ts, q = res['timestamp'], res['indicators']['quote'][0]
            h = []
            for i in range(len(ts)):
                if q['close'][i] is not None and q['volume'][i] is not None:
                    h.append({"t": ts[i], "o": q['open'][i], "c": q['close'][i], "v": q['volume'][i]})
            return h[-35:]
    except: return None

async def update_prices():
    all_s = set()
    for eid, data in etf_base_data.items():
        tick = "0050.TW" if eid=="0050" else f"{eid[:5]}.TW"
        all_s.add(tick)
        for s in data['holdings']: all_s.add(s['id'])
            
    quotes = {}
    async with httpx.AsyncClient() as client:
        for s in list(all_s):
            res = await fetch_yahoo_kline(s, "" if "." in s else ".TW", client)
            if not res and "." not in s: res = await fetch_yahoo_kline(s, ".TWO", client)
            if res: quotes[s] = res

    for eid, data in etf_base_data.items():
        tick = "0050.TW" if eid=="0050" else f"{eid[:5]}.TW"
        if tick in quotes:
            q = quotes[tick]; data['price'] = round(q[-1]['c'], 2)
            chg = (q[-1]['c'] - q[-2]['c']) / q[-2]['c'] * 100
            data['change'] = f"{chg:+.2f}%"

        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, prev_p = q[-1]['c'], q[-2]['c']
                chg_p = (p - prev_p) / prev_p * 100
                st.update({'price': p, 'change': f"{chg_p:+.2f}%", 'history': q})
                
                # 量價分析
                avg_v = sum(d['v'] for d in q[-5:]) / 5
                v_ratio = q[-1]['v'] / avg_v if avg_v > 0 else 1
                if chg_p > 0.5: vp = "價漲量增" if v_ratio > 1.1 else "價漲量縮"
                elif chg_p < -0.5: vp = "價跌量增" if v_ratio > 1.1 else "價跌量縮"
                else: vp = "量縮整理"
                st['vp_analysis'] = vp
                if st['id'] in NEW_STOCKS: st['is_new'] = True

    with open(html_file, "r") as f: content = f.read()
    new_js = f"const etfData = {json.dumps(etf_base_data, ensure_ascii=False, indent=4)};"
    updated = re.sub(r"const etfData = \{.*?\};", new_js, content, flags=re.DOTALL)
    with open(html_file, "w") as f: f.write(updated)
    print("🎊 數據更新與量價分析完成")

if __name__ == "__main__": asyncio.run(update_prices())
