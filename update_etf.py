import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def fetch_2024_price(s, client):
    # 強制指定 2024 年 10 月 25 日 左右的 TimeStamp (約 1729814400)
    # 我們抓取 2024 年 10 月初 到 10 月底的資料
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?period1=1727740800&period2=1730332800&interval=1d"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        h = [{"t": ts[i], "c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
        return h[-5:] # 傳回 2024 年 10 月底最後幾筆
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
        all_s = set()
        all_s.add("0050")
        for d in etf_base_data.values():
            for st in d['holdings']: all_s.add(st['id'])
        
        quotes = {}
        tasks = [fetch_2024_price(s, client) for s in list(all_s)]
        results = await asyncio.gather(*tasks)
        for i, s in enumerate(list(all_s)):
            if results[i]: quotes[s] = results[i]

    for eid, data in etf_base_data.items():
        total_p_change = 0
        weight_sum = 0
        
        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, p_p = q[-1]['c'], q[-2]['c']
                st.update({'price': p, 'change': f"{((p-p_p)/p_p*100):+.2f}%", 'history': q})
                vol, vol_p = q[-1]['v'], q[-2]['v']
                st['vwap_pos'] = "高於週VWAP" if p > sum(x['c'] for x in q[-5:])/5 else "回測週VWAP"
                st['vp_analysis'] = "價漲量增" if (p > p_p and vol > vol_p) else "量縮盤整"
                st['net_buy'] = f"{int(vol/1000):+d}"
                
                total_p_change += ((p - p_p) / p_p) * (st['weight'] / 100)
                weight_sum += st['weight']

        if eid == '0050' and '0050' in quotes:
             q_50 = quotes['0050']
             data['price'] = round(q_50[-1]['c'], 2)
             data['change'] = f"{((q_50[-1]['c']-q_50[-2]['c'])/q_50[-2]['c']*100):+.2f}%"
        else:
             base = 28.5
             daily_swing = total_p_change / (weight_sum/100) if weight_sum > 0 else 0
             data['price'] = round(base * (1 + daily_swing), 2)
             data['change'] = f"{daily_swing*100:+.2f}%"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": [] }, f, ensure_ascii=False, indent=4)
        
if __name__ == "__main__": asyncio.run(run())
