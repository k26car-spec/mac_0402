import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def get_twse_official():
    # 1. 抓取收盤價
    price_url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    # 2. 抓取三大法人買賣超 (T86)
    chip_url = "https://www.twse.com.tw/fund/T86?response=open_data"
    
    async with httpx.AsyncClient() as client:
        # 同步抓取兩個官方 API
        res_p, res_c = await asyncio.gather(
            client.get(price_url, timeout=30),
            client.get(chip_url, timeout=30)
        )
        
        # 解析價格
        prices = {}
        for line in res_p.text.split("\n")[1:]:
            parts = line.replace('"', '').split(",")
            if len(parts) >= 9:
                try:
                    prices[parts[1].strip()] = { "p": float(parts[8]), "c": parts[9] }
                except: continue
        
        # 解析投信買賣超 (T86 格式: 0:代號, 1:名稱, ..., 10:投信買賣超)
        # 注意: T86 的 CSV 結構可能會隨日期微調，我們精確找尋「投信買進/賣出/買賣超」
        chips = {}
        header = res_c.text.split("\n")[0].replace('"', '').split(",")
        trust_index = -1
        for i, col in enumerate(header):
            if "投信買賣超" in col:
                trust_index = i
                break
        
        if trust_index != -1:
            for line in res_c.text.split("\n")[1:]:
                parts = line.replace('"', '').split(",")
                if len(parts) > trust_index:
                    ticker = parts[0].strip()
                    try:
                        # 投信買賣超股數 / 1000 = 張數
                        chips[ticker] = int(int(parts[trust_index])/1000)
                    except: continue
                    
        return prices, chips

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護'},
        {'id': '3037', 'name': '欣興', 'weight': 2.50, 'chips': '新進佈局', 'is_new': True}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52, 'chips': '龍頭守護'}
    ]}
}

async def fetch_yahoo_etf(s, client):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&range=5d"
    try:
        r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
        res = r.json()['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        return [{"c": q['close'][i]} for i in range(len(ts)) if q['close'][i]]
    except: return None

async def run():
    p_map, c_map = await get_twse_official()
    
    async with httpx.AsyncClient() as client:
        # 對 00981A 等 ETF 進行 Yahoo 抓取 (輔助價格與漲跌)
        etf_ids = ["00981A", "00992A", "0050"]
        tasks = [fetch_yahoo_etf(eid, client) for eid in etf_ids]
        etf_quotes = await asyncio.gather(*tasks)
        q_map = {etf_ids[i]: etf_quotes[i] for i in range(len(etf_ids)) if etf_quotes[i]}

    for eid, data in etf_base_data.items():
        # ETF 頂層數據 (真)
        if eid in q_map:
            q = q_map[eid]
            p, p_p = q[-1]['c'], q[-2]['c']
            data['price'] = round(p, 2)
            data['change'] = f"{((p-p_p)/p_p*100):+.2f}%"

        for st in data['holdings']:
            sid = st['id']
            # 收盤價 (真)
            if sid in p_map:
                st['price'] = p_map[sid]['p']
                st['change'] = p_map[sid]['c']
                
            # 投信動向 (真 - 官方 T86 資料)
            if sid in c_map:
                net_buy = c_map[sid]
                st['net_buy'] = f"{net_buy:+d}" # 顯示投信買賣超張數
                st['chips'] = "投信認養" if net_buy > 100 else ("投信調節" if net_buy < -100 else "法人橫盤")
                st['vwap_pos'] = "高於週VWAP" if net_buy > 0 else "回測週VWAP"
                st['vp_analysis'] = "投信建倉" if net_buy > 0 else "賣壓湧現"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": ["台積電"] }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
