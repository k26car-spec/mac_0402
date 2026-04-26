import asyncio
import json
import httpx
import os

data_file = "docs/data.json"
ETF_SCALES = { '00981A': 1925, '00992A': 468, '0050': 4500 }

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台績電', 'weight': 8.55, 'chips': '龍頭守護'},
        {'id': '2454', 'name': '聯發科', 'weight': 5.20, 'chips': '投信連買'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.20, 'chips': '主力吸納'}
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台績電', 'weight': 20.00, 'chips': '法人加碼'},
        {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼'},
        {'id': '3105', 'name': '穩懋', 'weight': 4.50, 'chips': '跌深反彈'},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': '主力進場'}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台績電', 'weight': 51.52, 'chips': '法人買超'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': '大戶守護'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '法人買超'},
        {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '主力連掃'},
        {'id': '3037', 'name': '欣興', 'weight': 1.25, 'chips': '法人回補'}
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
    for eid, d in etf_base_data.items():
        all_s.add(eid)
        for st in d['holdings']: all_s.add(st['id'])
    
    quotes = {}
    async with httpx.AsyncClient() as client:
        for s in list(all_s):
            res = await fetch_yahoo(s, client)
            if not res: res = await fetch_yahoo(s.replace(".TW", ".TWO"), client)
            if res: quotes[s] = res

    for eid, data in etf_base_data.items():
        if eid in quotes:
            q = quotes[eid]
            data['price'] = round(q[-1]['c'], 2)
            data['change'] = f"{((q[-1]['c']-q[-2]['c'])/q[-2]['c']*100):+.2f}%"
        
        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, p_p = q[-1]['c'], q[-2]['c']
                st.update({'price': p, 'change': f"{((p-p_p)/p_p*100):+.2f}%", 'history': q})
                vol, vol_p = q[-1]['v'], q[-2]['v']
                # 補齊表格顯示欄位
                st['vwap_pos'] = "高於週VWAP" if p > sum(x['c'] for x in q[-5:])/5 else "低於週VWAP"
                st['vp_analysis'] = "價漲量增" if (p > p_p and vol > vol_p) else "量縮盤整"
                force = (p - p_p) / p_p * (vol / 100000) * 10 
                st['net_buy'] = f"{int(force):+d}"

    # 計算全體共同持股 (主力共識)
    set1, set2, set3 = {s['id'] for s in etf_base_data['00981A']['holdings']}, {s['id'] for s in etf_base_data['00992A']['holdings']}, {s['id'] for s in etf_base_data['0050']['holdings']}
    common_ids = list(set1 & set2 & set3)
    common_names = []
    # 建立一個統一的名稱映射
    name_map = {}
    for d in etf_base_data.values():
        for st in d['holdings']: name_map[st['id']] = st['name']
    
    common_list = [name_map[cid] for cid in common_ids if cid in name_map]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
