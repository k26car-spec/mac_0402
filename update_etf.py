import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護'},
        {'id': '3037', 'name': '欣興', 'weight': 2.50, 'chips': '新進佈局', 'is_new': True}, # 標記為新進
        {'id': '2454', 'name': '聯發科', 'weight': 6.20, 'chips': '投信連買'},
        {'id': '2317', 'name': '鴻海', 'weight': 4.10, 'chips': '主力吸納'},
        {'id': '2383', 'name': '台光電', 'weight': 4.80, 'chips': '主動認養'},
        {'id': '3017', 'name': '奇鋐', 'weight': 4.30, 'chips': '散熱領先'},
        {'id': '2449', 'name': '京元電', 'weight': 2.00, 'chips': '新進補籌', 'is_new': True} # 標記為新進
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼'},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': '新進加碼', 'is_new': True}, # 標記為新進
        {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼'},
        {'id': '3105', 'name': '穩懋', 'weight': 4.50, 'chips': '跌深反彈'}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52, 'chips': '權值霸主'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': 'AI伺服器'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '手機晶片'},
        {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '電源領先'},
        {'id': '3037', 'name': '欣興', 'weight': 1.25, 'chips': '回歸名單', 'is_new': True} # 標記為新進
    ]}
}

async def fetch_yahoo(s, client):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&range=1mo"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        h = [{"t": ts[i], "c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
        return h[-30:]
    except: return None

async def run():
    all_s = set()
    # 我們也要抓 0050 的報價
    all_s.add("0050")
    for d in etf_base_data.values():
        for st in d['holdings']: all_s.add(st['id'])
    
    quotes = {}
    async with httpx.AsyncClient() as client:
        tasks = [fetch_yahoo(s, client) for s in list(all_s)]
        results = await asyncio.gather(*tasks)
        for i, s in enumerate(list(all_s)):
            if results[i]: quotes[s] = results[i]

    for eid, data in etf_base_data.items():
        # 如果是 0050，直接使用 real price；如果是主動型，則參考 0050 趨勢稍微動態化
        if "0050" in quotes:
            q_50 = quotes["0050"]
            p_50, p_p_50 = q_50[-1]['c'], q_50[-2]['c']
            if eid == "0050":
                data['price'] = p_50
                data['change'] = f"{((p_50-p_p_50)/p_p_50*100):+.2f}%"
            else:
                # 類推報價 (模擬連動)
                data['price'] = round(27.8 * (p_50 / p_p_50), 2)
                data['change'] = f"{((p_50-p_p_50)/p_p_50*100):+.2f}%"
        
        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, p_p = q[-1]['c'], q[-2]['c']
                st.update({'price': p, 'change': f"{((p-p_p)/p_p*100):+.2f}%", 'history': q})
                vol, vol_p = q[-1]['v'], q[-2]['v']
                st['vwap_pos'] = "高於週VWAP" if p > sum(x['c'] for x in q[-5:])/5 else "低於週VWAP"
                st['vp_analysis'] = "價漲量增" if (p > p_p and vol > vol_p) else "量縮盤整"
                force = (p - p_p) / p_p * (vol / 100000) * 10 
                st['net_buy'] = f"{int(force):+d}"

    id_map = {}
    for d in etf_base_data.values():
        for st in d['holdings']: id_map[st['id']] = st['name']
    
    set1, set2, set3 = {s['id'] for s in etf_base_data['00981A']['holdings']}, {s['id'] for s in etf_base_data['00992A']['holdings']}, {s['id'] for s in etf_base_data['0050']['holdings']}
    common_ids = list(set1 & set2 & set3)
    common_list = [id_map[cid] for cid in common_ids if cid in id_map]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
