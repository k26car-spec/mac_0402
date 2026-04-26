import asyncio
import json
import httpx
import os

data_file = "docs/data.json"

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護'},
        {'id': '2454', 'name': '聯發科', 'weight': 6.20, 'chips': '投信連買'},
        {'id': '2317', 'name': '鴻海', 'weight': 4.10, 'chips': '主力吸納'},
        {'id': '2383', 'name': '台光電', 'weight': 4.80, 'chips': '主動認養'},
        {'id': '3653', 'name': '健策', 'weight': 4.50, 'chips': '籌碼集中'},
        {'id': '3017', 'name': '奇鋐', 'weight': 4.30, 'chips': '散熱領先'},
        {'id': '2345', 'name': '智邦', 'weight': 3.80, 'chips': '投信連買'},
        {'id': '3037', 'name': '欣興', 'weight': 2.50, 'chips': '法人回補'},
        {'id': '6223', 'name': '旺矽', 'weight': 2.20, 'chips': '測試介面'},
        {'id': '2368', 'name': '金像電', 'weight': 2.10, 'chips': 'PCB首選'},
        {'id': '2449', 'name': '京元電', 'weight': 2.00, 'chips': '封測大廠'},
        {'id': '6669', 'name': '緯穎', 'weight': 1.80, 'chips': '伺服器代工'},
        {'id': '2382', 'name': '廣達', 'weight': 1.60, 'chips': 'AI主幹'},
        {'id': '3231', 'name': '緯創', 'weight': 1.50, 'chips': '法人佈局'},
        {'id': '2301', 'name': '光寶科', 'weight': 1.20, 'chips': '電源轉型'}
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼'},
        {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼'},
        {'id': '3105', 'name': '穩懋', 'weight': 4.50, 'chips': '跌深反彈'},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': '載板龍頭'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.10, 'chips': '晶片設計'},
        {'id': '2317', 'name': '鴻海', 'weight': 2.80, 'chips': 'AI賦能'},
        {'id': '2368', 'name': '金像電', 'weight': 2.50, 'chips': 'PCB龍頭'},
        {'id': '6223', 'name': '旺矽', 'weight': 2.20, 'chips': '投信新歡'},
        {'id': '3017', 'name': '奇鋐', 'weight': 2.00, 'chips': '液冷技術'},
        {'id': '2383', 'name': '台光電', 'weight': 1.80, 'chips': 'CCL首選'},
        {'id': '3653', 'name': '健策', 'weight': 1.60, 'chips': '均熱片'}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52, 'chips': '權值霸主'},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': 'AI伺服器'},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '手機晶片'},
        {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '電源領先'},
        {'id': '2303', 'name': '聯電', 'weight': 1.85, 'chips': '成熟產能'},
        {'id': '3711', 'name': '日月光', 'weight': 1.58, 'chips': '封測首選'},
        {'id': '2881', 'name': '富邦金', 'weight': 1.62, 'chips': '金控龍頭'},
        {'id': '2882', 'name': '國泰金', 'weight': 1.51, 'chips': '壽險獲利'},
        {'id': '2891', 'name': '中信金', 'weight': 1.12, 'chips': '獲利穩健'},
        {'id': '2412', 'name': '中華電', 'weight': 1.05, 'chips': '防禦守勢'},
        {'id': '2886', 'name': '兆豐金', 'weight': 0.92, 'chips': '官股穩定'},
        {'id': '5880', 'name': '合庫金', 'weight': 0.88, 'chips': '金融穩健'},
        {'id': '2884', 'name': '玉山金', 'weight': 0.81, 'chips': '消金優勢'},
        {'id': '2892', 'name': '第一金', 'weight': 0.78, 'chips': '公股領頭'},
        {'id': '1303', 'name': '南亞', 'weight': 0.75, 'chips': '塑化龍頭'},
        {'id': '2002', 'name': '中鋼', 'weight': 0.72, 'chips': '鋼鐵霸主'},
        {'id': '1216', 'name': '統一', 'weight': 0.68, 'chips': '食品龍頭'},
        {'id': '2357', 'name': '華碩', 'weight': 0.65, 'chips': 'PC復甦'},
        {'id': '2382', 'name': '廣達', 'weight': 0.63, 'chips': '伺服器王'},
        {'id': '3231', 'name': '緯創', 'weight': 0.60, 'chips': 'AI代工'},
        {'id': '1301', 'name': '台塑', 'weight': 0.58, 'chips': '塑膠大廠'},
        {'id': '1326', 'name': '台化', 'weight': 0.55, 'chips': '台塑三寶'},
        {'id': '2885', 'name': '元大金', 'weight': 0.52, 'chips': '證券霸主'},
        {'id': '2379', 'name': '瑞昱', 'weight': 0.50, 'chips': '網通晶片'},
        {'id': '9910', 'name': '豐泰', 'weight': 0.48, 'chips': '球鞋代工'},
        {'id': '2603', 'name': '長榮', 'weight': 0.45, 'chips': '航運龍頭'},
        {'id': '2609', 'name': '陽明', 'weight': 0.42, 'chips': '貨櫃三雄'},
        {'id': '2615', 'name': '萬海', 'weight': 0.38, 'chips': '近洋航運'},
        {'id': '3008', 'name': '大立光', 'weight': 0.45, 'chips': '光學龍頭'},
        {'id': '3045', 'name': '台灣大', 'weight': 0.40, 'chips': '電信穩健'},
        {'id': '2912', 'name': '統一超', 'weight': 0.42, 'chips': '零售霸主'},
        {'id': '1101', 'name': '台泥', 'weight': 0.38, 'chips': '水泥龍頭'},
        {'id': '2408', 'name': '南亞科', 'weight': 0.35, 'chips': 'DRAM大廠'},
        {'id': '2883', 'name': '開發金', 'weight': 0.32, 'chips': '壽險佈局'},
        {'id': '2395', 'name': '研華', 'weight': 0.30, 'chips': '工業電腦'},
        {'id': '6505', 'name': '台塑化', 'weight': 0.28, 'chips': '能源龍頭'},
        {'id': '4938', 'name': '和碩', 'weight': 0.25, 'chips': '代工轉型'},
        {'id': '3034', 'name': '聯詠', 'weight': 0.28, 'chips': '驅動IC'},
        {'id': '2887', 'name': '台新金', 'weight': 0.26, 'chips': '金融整併'},
        {'id': '1504', 'name': '東元', 'weight': 0.22, 'chips': '電機領先'},
        {'id': '2207', 'name': '和泰車', 'weight': 0.24, 'chips': '車市龍頭'},
        {'id': '2618', 'name': '長榮航', 'weight': 0.23, 'chips': '航空復甦'},
        {'id': '3037', 'name': '欣興', 'weight': 0.25, 'chips': '載板龍頭'}
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
    for d in etf_base_data.values():
        for st in d['holdings']: all_s.add(st['id'])
    
    quotes = {}
    async with httpx.AsyncClient() as client:
        tasks = [fetch_yahoo(s, client) for s in list(all_s)]
        results = await asyncio.gather(*tasks)
        for i, s in enumerate(list(all_s)):
            if results[i]: quotes[s] = results[i]

    for eid, data in etf_base_data.items():
        data['price'] = 27.80
        data['change'] = "+4.43%"
        
        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, p_p = q[-1]['c'], q[-2]['c']
                st.update({'price': p, 'change': f"{((p-p_p)/p_p*100):+.2f}%", 'history': q})
                vol, vol_p = q[-1]['v'], q[-2]['v']
                st['vwap_pos'] = "高於週VWAP" if p > sum(x['c'] for x in q[-5:])/5 else "低於週VWAP"
                st['vp_analysis'] = "價漲量增" if (p > p_p and vol > vol_p) else "量縮盤整"
                force = (p - p_p) / p_p * (vol / 100000) * 10 
                st['net_buy'] = f"{int(force):+d}"

    id_map = {}
    for d in etf_base_data.values():
        for st in d['holdings']: id_map[st['id']] = st['name']
    
    set1, set2, set3 = {s['id'] for s in etf_base_data['00981A']['holdings']}, {s['id'] for s in etf_base_data['00992A']['holdings']}, {s['id'] for s in etf_base_data['0050']['holdings']}
    common_ids = list(set1 & set2 & set3)
    common_list = [id_map[cid] for cid in common_ids if cid in id_map]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": common_list }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
