import asyncio
import json
import httpx
import os

data_file = "docs/data.json"
ETF_SCALES = { '00981A': 1925, '00992A': 468, '0050': 4500 }
NEW_STOCKS = ["3037", "2344", "2368", "2449", "7769"]

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護'},
        {'id': '2454', 'name': '聯發科', 'weight': 5.20, 'chips': '法人買超'},
        {'id': '2383', 'name': '台光電', 'weight': 4.80, 'chips': '主動認養'},
        {'id': '3653', 'name': '健策', 'weight': 4.50, 'chips': '籌碼集中'},
        {'id': '3017', 'name': '奇鋐', 'weight': 4.30, 'chips': 'AI伺服器'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.20, 'chips': '外資吸納'},
        {'id': '2345', 'name': '智邦', 'weight': 2.80, 'chips': '投信連買'},
        {'id': '3037', 'name': '欣興', 'weight': 2.20, 'chips': '法人回補'}
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼'},
        {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼'},
        {'id': '3105', 'name': '穩懋', 'weight': 4.50, 'chips': '跌深反彈'},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': 'ABF龍頭'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.10, 'chips': '晶片設計'}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '63.17%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52, 'chips': '權值霸主'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': 'AI伺服器'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '手機晶片'},
        {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '電源領先'},
        {'id': '2303', 'name': '聯電', 'weight': 1.85, 'chips': '成熟製程'},
        {'id': '3711', 'name': '日月光', 'weight': 1.58, 'chips': '封測首選'},
        {'id': '2881', 'name': '富邦金', 'weight': 1.62, 'chips': '金控龍頭'},
        {'id': '2882', 'name': '國泰金', 'weight': 1.51, 'chips': '壽險獲利'},
        {'id': '2412', 'name': '中華電', 'weight': 1.05, 'chips': '防禦守勢'},
        {'id': '2891', 'name': '中信金', 'weight': 0.98, 'chips': '獲利穩健'},
        {'id': '3037', 'name': '欣興', 'weight': 1.25, 'chips': '載板龍頭'},
        {'id': '2344', 'name': '華邦電', 'weight': 0.85, 'chips': '新進成員'},
        {'id': '2368', 'name': '金像電', 'weight': 0.70, 'chips': '新進成員'},
        {'id': '2449', 'name': '京元電', 'weight': 0.65, 'chips': '新進成員'},
        {'id': '7769', 'name': '崇越', 'weight': 0.55, 'chips': '新進成員'},
        {'id': '2886', 'name': '兆豐金', 'weight': 0.92, 'chips': '官股穩定'},
        {'id': '5871', 'name': '中租', 'weight': 0.85, 'chips': '融資龍頭'},
        {'id': '2884', 'name': '玉山金', 'weight': 0.81, 'chips': '消金穩健'},
        {'id': '1303', 'name': '南亞', 'weight': 0.78, 'chips': '塑化龍頭'},
        {'id': '2002', 'name': '中鋼', 'weight': 0.75, 'chips': '鋼鐵霸主'},
        {'id': '2357', 'name': '華碩', 'weight': 0.70, 'chips': 'PC復甦'},
        {'id': '2382', 'name': '廣達', 'weight': 0.65, 'chips': '伺服器王'},
        {'id': '3231', 'name': '緯創', 'weight': 0.60, 'chips': 'AI代工'},
        {'id': '2395', 'name': '研華', 'weight': 0.55, 'chips': '工業電腦'},
        {'id': '4938', 'name': '和碩', 'weight': 0.58, 'chips': '代工轉型'},
        {'id': '2885', 'name': '元大金', 'weight': 0.55, 'chips': '證券龍頭'},
        {'id': '2892', 'name': '第一金', 'weight': 0.53, 'chips': '公股領頭'}
    ]}
}

async def fetch_yahoo(s, client):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&range=2mo"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=15)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        h = [{"t": ts[i], "c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
        return h[-35:]
    except: return None

async def run():
    all_s = set()
    for d in etf_base_data.values():
        for st in d['holdings']: all_s.add(st['id'])
    
    quotes = {}
    async with httpx.AsyncClient() as client:
        for s in list(all_s):
            res = await fetch_yahoo(s, client)
            if not res: res = await fetch_yahoo(s.replace(".TW", ".TWO"), client)
            if res: quotes[s] = res

    # 計算全體共同持股
    set1 = {s['id'] for s in etf_base_data['00981A']['holdings']}
    set2 = {s['id'] for s in etf_base_data['00992A']['holdings']}
    set3 = {s['id'] for s in etf_base_data['0050']['holdings']}
    common_ids = list(set1 & set2 & set3)
    common_names = []
    for cid in common_ids:
        for st in etf_base_data['0050']['holdings']:
            if st['id'] == cid: common_names.append(st['name']); break

    for eid, data in etf_base_data.items():
        scale_bn = ETF_SCALES[eid] * 100000000
        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, p_p = q[-1]['c'], q[-2]['c']
                st.update({'price': p, 'change': f"{((p-p_p)/p_p*100):+.2f}%", 'history': q})
                net = int(((scale_bn * (st['weight']/100)) / p - (scale_bn * 0.9992 * (st['weight']/100)) / p_p) / 1000)
                st['net_buy'] = f"{net:+d}"
                st['is_new'] = st['id'] in NEW_STOCKS
                st['vp_analysis'] = "價漲量增" if (p > p_p and q[-1]['v'] > q[-2]['v']) else "量縮盤整"
                st['tech'] = "站穩月線" if p > sum(x['c'] for x in q[-20:])/20 else "區間震盪"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_names }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
