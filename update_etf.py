import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def fetch_yahoo_full(s, client):
    # 同時抓取收盤價與成交量歷史
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&range=5d"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        # 回傳資料列表: [{"c": 價, "v": 量}, ...]
        return [{"c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
    except: return None

async def get_twse_official():
    # 籌碼來源
    chip_url = "https://www.twse.com.tw/fund/T86?response=open_data"
    async with httpx.AsyncClient() as client:
        res_c = await client.get(chip_url, timeout=30)
        chips = {}
        for line in res_c.text.split("\n")[1:]:
            parts = line.replace('"', '').split(",")
            if len(parts) >= 11:
                try:
                    chips[parts[0].strip()] = int(int(parts[10])/1000) # 投信買賣超張數
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
        all_ids = ["00981A", "00992A", "0050", "2330", "2317", "2454", "3037"]
        tasks = [fetch_yahoo_full(s, client) for s in all_ids]
        results = await asyncio.gather(*tasks)
        q_map = {all_ids[i]: results[i] for i in range(len(all_ids)) if results[i]}

    for eid, data in etf_base_data.items():
        if eid in q_map:
            q = q_map[eid]
            data['price'] = round(q[-1]['c'], 2)
            data['change'] = f"{((q[-1]['c']-q[-2]['c'])/q[-2]['c']*100):+.2f}%"

        for st in data['holdings']:
            sid = st['id']
            if sid in q_map:
                q = q_map[sid]
                # 取得真實兩日價量
                p, p_p = q[-1]['c'], q[-2]['c']
                v, v_p = q[-1]['v'], q[-2]['v']
                
                st.update({'price': p, 'change': f"{p-p_p:+.1f} ({((p-p_p)/p_p*100):+.2f}%)"})
                
                # 量價真實分析
                if p > p_p and v > v_p: st['vp_analysis'] = "價漲量增"
                elif p < p_p and v > v_p: st['vp_analysis'] = "價跌量增"
                elif v < v_p: st['vp_analysis'] = "量縮盤整"
                else: st['vp_analysis'] = "價量平穩"
                
                # VWAP 真實分析: 價格 > 均價 
                avg_p = sum([x['c'] for x in q]) / len(q)
                st['vwap_pos'] = "高於週VWAP" if p > avg_p else "低於週VWAP"
            
            # 真實投信買賣超
            if sid in c_map:
                st['net_buy'] = f"{c_map[sid]:+d}"

    # 寫入資料
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": ["台積電"] }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
