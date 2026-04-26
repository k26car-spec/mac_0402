import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def fetch_yahoo_full(s, client):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&range=5d"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        return [{"c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
    except: return None

async def get_twse_official():
    chip_url = "https://www.twse.com.tw/fund/T86?response=open_data"
    async with httpx.AsyncClient() as client:
        res_c = await client.get(chip_url, timeout=30)
        chips = {}
        for line in res_c.text.split("\n")[1:]:
            parts = line.replace('"', '').split(",")
            if len(parts) >= 11:
                try: chips[parts[0].strip()] = int(int(parts[10])/1000)
                except: continue
        return chips

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
        {'id': '3711', 'name': '日月光', 'weight': 1.58},
        {'id': '2881', 'name': '富邦金', 'weight': 1.62},
        {'id': '2882', 'name': '國泰金', 'weight': 1.51},
        {'id': '2891', 'name': '中信金', 'weight': 1.12},
        {'id': '2412', 'name': '中華電', 'weight': 1.05},
        {'id': '2886', 'name': '兆豐金', 'weight': 0.92},
        {'id': '2884', 'name': '玉山金', 'weight': 0.81},
        {'id': '3037', 'name': '欣興', 'weight': 1.25, 'is_new': True},
        {'id': '2382', 'name': '廣達', 'weight': 0.63},
        {'id': '3231', 'name': '緯創', 'weight': 0.60},
        {'id': '2603', 'name': '長榮', 'weight': 0.45},
        {'id': '3008', 'name': '大立光', 'weight': 0.45},
        {'id': '2885', 'name': '元大金', 'weight': 0.42},
        {'id': '2912', 'name': '統一超', 'weight': 0.41},
        {'id': '2892', 'name': '第一金', 'weight': 0.40},
        {'id': '5880', 'name': '合庫金', 'weight': 0.38},
        {'id': '1303', 'name': '南亞', 'weight': 0.35},
        {'id': '1216', 'name': '統一', 'weight': 0.34},
        {'id': '2880', 'name': '華南金', 'weight': 0.32},
        {'id': '2357', 'name': '華碩', 'weight': 0.30},
        {'id': '2002', 'name': '中鋼', 'weight': 0.28},
        {'id': '2883', 'name': '凱基金', 'weight': 0.26},
        {'id': '2379', 'name': '瑞昱', 'weight': 0.25},
        {'id': '1101', 'name': '台泥', 'weight': 0.24},
        {'id': '2887', 'name': '台新金', 'weight': 0.23},
        {'id': '2408', 'name': '南亞科', 'weight': 0.22},
        {'id': '2395', 'name': '研華', 'weight': 0.21},
        {'id': '6505', 'name': '台塑化', 'weight': 0.20},
        {'id': '3034', 'name': '聯詠', 'weight': 0.19},
        {'id': '4938', 'name': '和碩', 'weight': 0.18}
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
            # 初始化預設值以免 undefined
            st.update({'price': 0, 'change': '-', 'net_buy': '0', 'vwap_pos': '計算中', 'vp_analysis': '觀望', 'chips': '法人橫盤'})
            
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
                nb = c_map[sid]
                st['net_buy'] = f"{nb:+d}"
                st['chips'] = "投信認養" if nb > 100 else ("投信調節" if nb < -100 else "法人橫盤")

    sets = [set(st['id'] for st in d['holdings']) for d in etf_base_data.values()]
    common_ids = sets[0] & sets[1] & sets[2]
    all_h = [st for d in etf_base_data.values() for st in d['holdings']]
    name_map = {st['id']: st['name'] for st in all_h}
    common_list = [name_map[cid] for cid in common_ids if cid in name_map]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
