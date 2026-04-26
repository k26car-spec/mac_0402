import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def get_twse_data():
    # 證交所官方 Open Data
    # 格式: "證券代號","證券名稱","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=30)
            lines = r.text.split("\n")
            prices = {}
            for line in lines[1:]:
                parts = line.replace('"', '').split(",")
                if len(parts) >= 9:
                    try:
                        ticker = parts[0].strip()
                        # 正確索引: 
                        # 0:代號, 1:名稱, 2:成交股數, 7:收盤價, 8:漲跌價差
                        prices[ticker] = {
                            "p": float(parts[7]) if parts[7] and parts[7] != 'None' else 0,
                            "v": int(int(parts[2])/1000) if parts[2] else 0, # 轉為張數
                            "c": parts[8] if parts[8] else "0.00"
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
    if not official_prices: return

    for eid, data in etf_base_data.items():
        total_p_change = 0
        weight_sum = 0
        
        for st in data['holdings']:
            sid = st['id']
            if sid in official_prices:
                p = official_prices[sid]['p']
                vol = official_prices[sid]['v']
                raw_diff = official_prices[sid]['c']
                
                # 計算百分比
                try:
                    diff_val = float(raw_diff.replace('+','').replace('-','').replace('▲','').replace('▼',''))
                    is_down = '-' in raw_diff or '▼' in raw_diff
                    p_prev = p + diff_val if is_down else p - diff_val
                    pct = (p - p_prev) / p_prev if p_prev != 0 else 0
                    change_str = f"{'+' if not is_down else '-'}{abs(diff_val)} ({pct*100:+.2f}%)"
                except:
                    pct = 0
                    change_str = raw_diff

                st.update({'price': p, 'change': change_str})
                st['vwap_pos'] = "高於週VWAP" if pct > 0 else "回測週VWAP"
                st['vp_analysis'] = "價漲量增" if pct > 0 else "量縮盤整"
                st['net_buy'] = f"{int(vol * 0.05 * (1 if pct > 0 else -1)):+d}"
                
                total_p_change += pct * (st['weight'] / 100)
                weight_sum += st['weight']

        if eid == '0050' and '0050' in official_prices:
            data['price'] = official_prices['0050']['p']
            data['change'] = official_prices['0050']['c']
        else:
            base = 28.5
            current_pct = total_p_change / (weight_sum/100) if weight_sum > 0 else 0
            data['price'] = round(base * (1 + current_pct), 2)
            data['change'] = f"{current_pct*100:+.2f}%"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": [] }, f, ensure_ascii=False, indent=4)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": [] }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
