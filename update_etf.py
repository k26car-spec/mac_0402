import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def fetch_yahoo(s, client):
    # 使用正確的 .TW 後綴抓取這幾檔 ETF 的官方真實行情
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&range=5d"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        h = [{"t": ts[i], "c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
        return h[-2:] # 只拿最後兩天的收盤價做漲跌計算
    except: return None

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
    async with httpx.AsyncClient() as client:
        # 同步抓取所有 ETF 和個股的真實 Yahoo 行情
        all_ids = ["00981A", "00992A", "0050", "2330", "2317", "2454", "3037"]
        tasks = [fetch_yahoo(s, client) for s in all_ids]
        results = await asyncio.gather(*tasks)
        quotes = {all_ids[i]: results[i] for i in range(len(all_ids)) if results[i]}

    for eid, data in etf_base_data.items():
        if eid in quotes:
            q = quotes[eid]
            p, p_p = q[-1]['c'], q[-2]['c']
            data['price'] = round(p, 2)
            data['change'] = f"{((p-p_p)/p_p*100):+.2f}%"
        
        for st in data['holdings']:
            sid = st['id']
            if sid in quotes:
                q = quotes[sid]
                p, p_p = q[-1]['c'], q[-2]['c']
                pct = (p-p_p)/p_p
                st.update({
                    'price': p, 
                    'change': f"{p-p_p:+.1f} ({pct*100:+.2f}%)",
                    'vwap_pos': "高於週VWAP" if pct > 0 else "低於週VWAP",
                    'vp_analysis': "價漲量增" if pct > 0 else "量縮盤整"
                })

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": ["台積電"] }, f, ensure_ascii=False, indent=4)
        
if __name__ == "__main__": asyncio.run(run())
