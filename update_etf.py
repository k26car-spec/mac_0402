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
        {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護'},
        {'id': '3037', 'name': '欣興', 'weight': 2.50, 'chips': '新進佈局', 'is_new': True},
        {'id': '2454', 'name': '聯發科', 'weight': 6.20, 'chips': '投信連買'},
        {'id': '2317', 'name': '鴻海', 'weight': 4.10, 'chips': '主力吸納'}
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼'},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': '新進加碼', 'is_new': True}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52, 'chips': '權值霸主'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': 'AI伺服器'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '手機晶片'}
    ]}
}

async def run():
    c_map = await get_twse_official()
    async with httpx.AsyncClient() as client:
        # 自動搜集所有持股 ID 並加上 .TW 後綴抓取
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

        for st in data['holdings']:
            sid = st['id']
            if sid in q_map:
                q = q_map[sid]
                p, p_p = q[-1]['c'], q[-2]['c']
                v, v_p = q[-1]['v'], q[-2]['v']
                
                # VWAP 精算 (5日加權)
                total_val = sum([x['c'] * x['v'] for x in q])
                total_vol = sum([x['v'] for x in q])
                vw_avg = total_val/total_vol if total_vol > 0 else p
                
                st.update({'price': p, 'change': f"{p-p_p:+.1f} ({((p-p_p)/p_p*100):+.2f}%)"})
                st['vwap_pos'] = "💪 多頭鎖碼" if p > vw_avg else "📉 回測週VWAP"
                st['vp_analysis'] = "價漲量增" if (p > p_p and v > v_p) else ("量縮盤整" if v < v_p else "高檔震盪")
            
            if sid in c_map:
                st['net_buy'] = f"{c_map[sid]:+d}"

    # 動態計算主力共識持股 (三家都有的)
    sets = [set(st['id'] for st in d['holdings']) for d in etf_base_data.values()]
    common_ids = sets[0] & sets[1] & sets[2]
    # 查找名稱
    name_map = {st['id']: st['name'] for d in etf_base_data.values() for st in d['holdings']}
    common_list = [name_map[cid] for cid in common_ids if cid in name_map]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
