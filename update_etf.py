import asyncio
import re
import json
import httpx
from datetime import datetime

html_file = "index.html"
NEW_STOCKS = ["3037", "2344", "2368", "2449", "7769"]

etf_base_data = {
    '00981A': {
        'name': '統一台股增長', 'price': 27.80, 'change': '+4.43%', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護', 'tech': '高於週VWAP'},
            {'id': '2454', 'name': '聯發科', 'weight': 5.20, 'chips': '法人買超', 'tech': '築底起飛'}
        ]
    },
    '00992A': {
        'name': '群益科技創新', 'price': 16.93, 'change': '+1.62%', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼', 'tech': '高於週VWAP'},
            {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼', 'tech': '多頭排列'}
        ]
    },
    '0050': {
        'name': '元大台灣50', 'price': 195.0, 'change': '+1.2%', 'scale': '4,500 億', 'topWeight': '63.17%', 'vwap': '權值護盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 63.17, 'chips': '外資買超', 'tech': '權值霸主'},
            {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '主力連掃', 'tech': '多頭排列'},
            {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '法人卡位', 'tech': '低檔反彈'},
            {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': '大戶佈局', 'tech': '季線支撐'},
            {'id': '3711', 'name': '日月光投控', 'weight': 1.58, 'chips': '封測龍頭', 'tech': '帶量突破'},
            {'id': '3037', 'name': '欣興', 'weight': 1.20, 'chips': '投信新換', 'tech': '新進轉強'}
        ]
    }
}
# 這裡為了展示邏輯僅列出少數，實際腳本我會填入完整 51 檔

async def fetch_yahoo_kline(symbol, suffix, client):
    full_symbol = f"{symbol}{suffix}" if "." not in symbol else symbol
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{full_symbol}?interval=1d&range=2mo"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = await client.get(url, headers=headers, timeout=10.0)
        data = resp.json()
        if data and 'chart' in data and data['chart']['result']:
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            history = []
            for i in range(len(timestamps)):
                o, c, v = quotes['open'][i], quotes['close'][i], quotes['volume'][i]
                if all(x is not None for x in [o, c, v]):
                    history.append({"t": timestamps[i], "o": round(o, 2), "c": round(c, 2), "v": v})
            return history[-35:]
    except: return None

async def update_prices():
    # 建立完整 symbols 列表並抓取
    all_s = set()
    for eid, data in etf_base_data.items():
        all_s.add("0050.TW" if eid=="0050" else f"{eid[:5]}.TW")
        for s in data['holdings']: all_s.add(s['id'])
    
    quotes = {}
    async with httpx.AsyncClient() as client:
        for s in list(all_s):
            res = await fetch_yahoo_kline(s, "" if "." in s else ".TW", client)
            if not res and "." not in s: res = await fetch_yahoo_kline(s, ".TWO", client)
            if res: quotes[s] = res

    for eid, data in etf_base_data.items():
        s_ticker = "0050.TW" if eid=="0050" else f"{eid[:5]}.TW"
        if s_ticker in quotes:
            q = quotes[s_ticker]
            data['price'] = q[-1]['c']
            chg = (q[-1]['c'] - q[-2]['c']) / q[-2]['c'] * 100
            data['change'] = f"{chg:+.2f}%"

        for stock in data['holdings']:
            if stock['id'] in quotes:
                q = quotes[stock['id']]
                p, prev_p = q[-1]['c'], q[-2]['c']
                chg_p = (p - prev_p) / prev_p * 100
                stock.update({'price': p, 'change': f"{chg_p:+.2f}%", 'history': q})
                
                # [量價分析恢復]
                avg_v = sum(d['v'] for d in q[-5:]) / 5
                v_ratio = q[-1]['v'] / avg_v if avg_v > 0 else 1
                if chg_p > 0.5: vp = "價漲量增: 攻擊" if v_ratio > 1.1 else "價漲量縮: 弱勢"
                elif chg_p < -0.5: vp = "價跌量增: 拋售" if v_ratio > 1.1 else "價跌量縮: 支撐"
                else: vp = "量縮整理: 觀望"
                stock['vp_analysis'] = vp
                
                # [異動標記]
                if stock['id'] in NEW_STOCKS: stock['is_new'] = True

    with open(html_file, "r") as f: content = f.read()
    new_js = f"const etfData = {json.dumps(etf_base_data, ensure_ascii=False, indent=4)};"
    updated = re.sub(r"const etfData = \{.*?\};", new_js, content, flags=re.DOTALL)
    with open(html_file, "w") as f: f.write(updated)
    print("🎊 資料同步完成")

if __name__ == "__main__": asyncio.run(update_prices())
