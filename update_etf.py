import asyncio
import json
import httpx
import os
from datetime import datetime

data_file = "docs/data.json"
NEW_STOCKS = ["3037", "2344", "2368", "2449", "7769"]
ETF_SCALES = { '00981A': 1925, '00992A': 468, '0050': 4500 }

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護'},
        {'id': '2454', 'name': '聯發科', 'weight': 5.20, 'chips': '法人買超'},
        {'id': '2383', 'name': '台光電', 'weight': 4.80, 'chips': '主動認養'},
        {'id': '3653', 'name': '健策', 'weight': 4.50, 'chips': '籌碼集中'},
        {'id': '3017', 'name': '奇鋐', 'weight': 4.30, 'chips': 'AI伺服器'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.20, 'chips': '外資吸納'},
        {'id': '2345', 'name': '智邦', 'weight': 2.80, 'chips': '投信連買'}
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼'},
        {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼'},
        {'id': '3105', 'name': '穩懋', 'weight': 4.50, 'chips': '跌深反彈'},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': '法人回補'}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '63.17%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 63.17, 'chips': '外資買超'},
        {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '主力連掃'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '法人卡位'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': '大戶佈局'},
        {'id': '3037', 'name': '欣興', 'weight': 1.25, 'chips': '新進成員'}
    ]}
}

async def fetch_yahoo(symbol, suffix, client):
    s = f"{symbol}{suffix}" if "." not in symbol else symbol
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?interval=1d&range=2mo"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        h = [{"t": ts[i], "c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
        return h[-35:]
    except: return None

async def run():
    all_s = set()
    for eid, d in etf_base_data.items():
        all_s.add("0050.TW" if eid=="0050" else (eid+".TW"))
        for st in d['holdings']: all_s.add(st['id'])
    
    quotes = {}
    async with httpx.AsyncClient() as client:
        for s in list(all_s):
            res = await fetch_yahoo(s, ".TW", client)
            if not res: res = await fetch_yahoo(s, ".TWO", client)
            if res: quotes[s] = res

    for eid, data in etf_base_data.items():
        scale_bn = ETF_SCALES[eid] * 100000000
        tick = "0050.TW" if eid=="0050" else (eid+".TW")
        if tick in quotes:
            q = quotes[tick]
            data['price'] = round(q[-1]['c'], 2)
            data['change'] = f"{((q[-1]['c']-q[-2]['c'])/q[-2]['c']*100):+.2f}%"

        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, p_prev = q[-1]['c'], q[-2]['c']
                st.update({'price': p, 'change': f"{((p-p_prev)/p_prev*100):+.2f}%", 'history': q})
                
                # 計算基金當日買賣張數 (估計值)
                today_s = (scale_bn * (st['weight']/100)) / p
                prev_s = (scale_bn * 0.9992 * (st['weight']/100)) / p_prev
                net = int((today_s - prev_s) / 1000)
                st['net_buy'] = f"{net:+d}" if net != 0 else "+0"
                
                st['is_new'] = st['id'] in NEW_STOCKS
                st['vp_analysis'] = "價漲量增" if (p > p_prev and q[-1]['v'] > q[-2]['v']) else "量縮盤整"
                st['tech'] = "站穩月線" if p > sum(x['c'] for x in q[-20:])/20 else "回測成交點"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(etf_base_data, f, ensure_ascii=False, indent=4)
    print(f"🎊 {data_file} 已更新買賣張數數據")

if __name__ == "__main__": asyncio.run(run())
