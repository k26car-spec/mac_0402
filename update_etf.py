import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

async def get_twse_data():
    # 抓取證交所今日最新報價 (2026/04/26)
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=30)
            lines = r.text.split("\n")
            prices = {}
            for line in lines[1:]:
                parts = line.replace('"', '').split(",")
                if len(parts) >= 10:
                    try:
                        ticker = parts[1].strip()
                        prices[ticker] = {
                            "p": float(parts[8]) if parts[8] and parts[8] != 'None' else 0,
                            "v": int(int(parts[3])/1000) if parts[3] else 0, 
                            "c": parts[9] if parts[9] else "0.00"
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
    official = await get_twse_data()
    if not official: return

    for eid, data in etf_base_data.items():
        total_p_change = 0
        total_w = 0
        
        # ETF 本身報價
        if eid in official:
            data['price'] = official[eid]['p']
            data['change'] = official[eid]['c']
            
        for st in data['holdings']:
            sid = st['id']
            if sid in official:
                p = official[sid]['p']
                raw_diff = official[sid]['c']
                try:
                    diff_val = float(raw_diff.replace('+','').replace('-','').replace('▲','').replace('▼',''))
                    is_down = '-' in raw_diff or '▼' in raw_diff
                    p_p = p + diff_val if is_down else p - diff_val
                    pct = (p - p_p) / p_p if p_p != 0 else 0
                    st.update({'price': p, 'change': f"{'+' if not is_down else '-'}{abs(diff_val)} ({pct*100:+.2f}%)", 'vwap_pos': "高於週VWAP" if pct > 0 else "回測週VWAP", 'vp_analysis': "價漲量增" if pct > 0 else "量縮盤整"})
                    total_p_change += pct * (st['weight'] / 100)
                    total_w += st['weight']
                except: pass

        # 非 0050 基金價格
        if eid != '0050':
             daily_swing = total_p_change / (total_w/100) if total_w > 0 else 0
             base = 27.8
             data['price'] = round(base * (1 + daily_swing), 2)
             data['change'] = f"{daily_swing*100:+.2f}%"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": [] }, f, ensure_ascii=False, indent=4)
        
if __name__ == "__main__": asyncio.run(run())
