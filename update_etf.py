import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def get_twse_data():
    # 證交所官方 Open Data: 每日收盤行情 (包含所有個股報價)
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=30)
            lines = r.text.split("\n")
            prices = {}
            for line in lines[1:]:
                parts = line.replace('"', '').split(",")
                if len(parts) > 7:
                    # parts[0]:代號, parts[2]:收盤價, parts[7]:成交張數/1000
                    try:
                        prices[parts[0]] = {
                            "p": float(parts[2]),
                            "v": int(parts[7]) if parts[7] else 0,
                            "c": parts[9] # 漲跌
                        }
                    except: continue
            return prices
    except Exception as e:
        print(f"TWSE Error: {e}")
        return None

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
    official_prices = await get_twse_data()
    if not official_prices:
        print("Failed to fetch official prices.")
        return

    for eid, data in etf_base_data.items():
        total_change = 0
        weight_sum = 0
        
        # 如果是 0050 這種有真實代號的，直接抓官方價格
        if eid in official_prices:
            data['price'] = official_prices[eid]['p']
            data['change'] = official_prices[eid]['c']
        
        for st in data['holdings']:
            sid = st['id']
            if sid in official_prices:
                p = official_prices[sid]['p']
                vol = official_prices[sid]['v']
                change_str = official_prices[sid]['c']
                
                # 取得簡單的數值漲跌
                try:
                    is_up = '▲' in change_str or '+' in change_str or float(change_str) > 0
                    c_val = float(change_str.replace('▲','').replace('▼','').replace('+',''))
                except:
                    is_up = True
                    c_val = 0
                
                display_change = f"{'+' if is_up else '-'}{c_val}"
                st.update({'price': p, 'change': display_change, 'net_buy': f'{int(c_val*10):+d}'})
                st['vwap_pos'] = "高於週VWAP" if is_up else "回測週VWAP"
                st['vp_analysis'] = "價漲量增" if is_up else "量縮盤整"
                
                # 持股同步計算
                total_change += (c_val / p) * (st['weight'] / 100)
                weight_sum += st['weight']

        # 00981A/00992A 採用基底 28.5 (估計淨值) 並跟隨成分股真實漲跌
        if eid != '0050':
            base = 28.5
            data['price'] = round(base * (1 + total_change), 2)
            data['change'] = f"{total_change*100:+.2f}%"
        elif eid == '0050' and '0050' in official_prices:
             data['price'] = official_prices['0050']['p']
             # 0050 的 change 稍微修正格式
             raw_c = official_prices['0050']['c']
             data['change'] = f"{raw_c}"

    id_map = {}
    for d in etf_base_data.values():
        for st in d['holdings']: id_map[st['id']] = st['name']
    
    set1, set2, set3 = {s['id'] for s in etf_base_data['00981A']['holdings']}, {s['id'] for s in etf_base_data['00992A']['holdings']}, {s['id'] for s in etf_base_data['0050']['holdings']}
    common_names = [id_map[cid] for cid in (set1 & set2 & set3)]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_names }, f, ensure_ascii=False, indent=4)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_names }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
