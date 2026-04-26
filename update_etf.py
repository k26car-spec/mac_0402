import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def fetch_yahoo_full(s, client):
    # 自動嘗試 .TW (上市) 與 .TWO (上櫃)
    suffixes = [".TW", ".TWO"]
    if "00981A" in s or "00992A" in s: suffixes = [".TW"] # ETF類通常是 .TW
    
    for suffix in suffixes:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}{suffix}?interval=1d&range=5d"
        try:
            r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
            if r.status_code != 200: continue
            res = r.json()['chart']['result'][0]
            ts, q = res['timestamp'], res['indicators']['quote'][0]
            return [{"c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
        except: continue
    return None

async def get_twse_official():
    # 注意: T86 只包含上市。上櫃需要另外抓 TWT38U。為了穩定，我們先回傳上市籌碼，上櫃則在腳本內處理
    url = "https://www.twse.com.tw/fund/T86?response=open_data"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=30)
            chips = {}
            for line in res.text.split("\n")[1:]:
                parts = line.replace('"', '').split(",")
                if len(parts) >= 11:
                    chips[parts[0].strip()] = int(int(parts[10])/1000)
            return chips
    except: return {}

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55},
        {'id': '3037', 'name': '欣興', 'weight': 2.50, 'is_new': True},
        {'id': '2454', 'name': '聯發科', 'weight': 6.20},
        {'id': '2317', 'name': '鴻海', 'weight': 4.10},
        {'id': '2383', 'name': '台光電', 'weight': 4.80},
        {'id': '3017', 'name': '奇鋐', 'weight': 4.30},
        {'id': '2449', 'name': '京元電', 'weight': 2.00, 'is_new': True},
        {'id': '6223', 'name': '旺矽', 'weight': 2.20},
        {'id': '2368', 'name': '金像電', 'weight': 2.10},
        {'id': '2345', 'name': '智邦', 'weight': 1.80},
        {'id': '3653', 'name': '健策', 'weight': 1.60},
        {'id': '6669', 'name': '緯穎', 'weight': 1.40}
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 20.00},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'is_new': True},
        {'id': '6669', 'name': '緯穎', 'weight': 4.80},
        {'id': '3105', 'name': '穩懋', 'weight': 4.50},
        {'id': '2454', 'name': '聯發科', 'weight': 3.20},
        {'id': '2317', 'name': '鴻海', 'weight': 2.90},
        {'id': '2368', 'name': '金像電', 'weight': 2.50}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23},
        {'id': '2308', 'name': '台達電', 'weight': 3.93},
        {'id': '2303', 'name': '聯電', 'weight': 1.85},
        {'id': '2881', 'name': '富邦金', 'weight': 1.62},
        {'id': '2882', 'name': '國泰金', 'weight': 1.51},
        {'id': '3037', 'name': '欣興', 'weight': 1.25, 'is_new': True}
    ]}
}

async def run():
    c_map = await get_twse_official()
    async with httpx.AsyncClient() as client:
        all_sids = set(["00981A", "00992A", "0050"])
        for d in etf_base_data.values():
            for st in d['holdings']: all_sids.add(st['id'])
        
        id_list = list(all_sids)
        tasks = [fetch_yahoo_full(sid, client) for sid in id_list]
        responses = await asyncio.gather(*tasks)
        q_map = {id_list[i]: res for i, res in enumerate(responses) if res}

    for eid, data in etf_base_data.items():
        if eid in q_map:
            q = q_map[eid]
            data['price'] = round(q[-1]['c'], 2)
            data['change'] = f"{((q[-1]['c']-q[-2]['c'])/q[-2]['c']*100):+.2f}%"

        for st in data.get('holdings', []):
            sid = st['id']
            if sid in q_map:
                q = q_map[sid]
                p, p_p = q[-1]['c'], q[-2]['c']
                v, v_p = q[-1]['v'], q[-2]['v']
                total_val = sum([x['c'] * x['v'] for x in q])
                total_vol = sum([x['v'] for x in q])
                vw_avg = total_val/total_vol if total_vol > 0 else p
                
                st.update({'price': p, 'change': f"{p-p_p:+.1f} ({((p-p_p)/p_p*100):+.2f}%)"})
                st['vwap_pos'] = "💪 多頭鎖碼" if p > vw_avg else "📉 回測週VWAP"
                st['vp_analysis'] = "價漲量增" if (p > p_p and v > v_p) else ("量縮盤整" if v < v_p else "高檔震盪")
            
            if sid in c_map:
                st['net_buy'] = f"{c_map[sid]:+d}"
                st['chips'] = "投信認養" if c_map[sid] > 100 else ("投信調節" if c_map[sid] < -100 else "法人橫盤")

    sets = [set(st['id'] for st in d['holdings']) for d in etf_base_data.values()]
    common_ids = sets[0] & sets[1] & sets[2]
    all_h = [st for d in etf_base_data.values() for st in d['holdings']]
    name_map = {st['id']: st['name'] for st in all_h}
    common_list = [name_map[cid] for cid in common_ids if cid in name_map]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
