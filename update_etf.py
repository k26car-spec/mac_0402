import asyncio
import re
import json
import httpx
from datetime import datetime

data_file = "docs/data.json"
NEW_STOCKS = ["3037", "2344", "2368", "2449", "7769"]

etf_base_data = {
    '00981A': {
        'name': '統一台股增長', 'price': 27.80, 'change': '+4.43%', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護', 'tech': '高於週VWAP'},
            {'id': '2454', 'name': '聯發科', 'weight': 5.20, 'chips': '法人買超', 'tech': '築底起飛'},
            {'id': '2383', 'name': '台光電', 'weight': 4.80, 'chips': '主動認養', 'tech': '強勢噴發'},
            {'id': '3653', 'name': '健策', 'weight': 4.50, 'chips': '籌碼集中', 'tech': '高檔震盪'},
            {'id': '3017', 'name': '奇鋐', 'weight': 4.30, 'chips': 'AI伺服器', 'tech': '量增突破'},
            {'id': '2345', 'name': '智邦', 'weight': 4.10, 'chips': '投信連買', 'tech': '仰角攻擊'},
            {'id': '3324', 'name': '雙鴻', 'weight': 3.90, 'chips': '散熱大廠', 'tech': '盤整向上'},
            {'id': '2308', 'name': '台達電', 'weight': 3.50, 'chips': '長線佈局', 'tech': '突破頸線'},
            {'id': '2317', 'name': '鴻海', 'weight': 3.20, 'chips': '外資吸納', 'tech': '上升通道'},
            {'id': '3661', 'name': '世芯-KY', 'weight': 2.80, 'chips': '高價領頭', 'tech': '回測5日線'},
            {'id': '3443', 'name': '創意', 'weight': 2.50, 'chips': '融券回補', 'tech': '底部反轉'},
            {'id': '2449', 'name': '京元電子', 'weight': 2.30, 'chips': '低接買盤', 'tech': '站穩季線'},
            {'id': '3037', 'name': '欣興', 'weight': 2.10, 'chips': '投信回歸', 'tech': '整理末端'},
            {'id': '3189', 'name': '景碩', 'weight': 1.90, 'chips': '低位築底', 'tech': '黃金交叉'},
            {'id': '8046', 'name': '南電', 'weight': 1.80, 'chips': '空頭止跌', 'tech': '底部放量'},
            {'id': '1519', 'name': '華城', 'weight': 1.60, 'chips': '重電題材', 'tech': '沿均線上攻'},
            {'id': '1513', 'name': '中興電', 'weight': 1.50, 'chips': '政策受惠', 'tech': '回測月線'},
            {'id': '2603', 'name': '長榮', 'weight': 1.40, 'chips': '高股息誘因', 'tech': '橫向整理'},
            {'id': '1216', 'name': '統一', 'weight': 1.30, 'chips': '防禦型標的', 'tech': '緩步墊高'},
            {'id': '2881', 'name': '富邦金', 'weight': 1.20, 'chips': '金融領頭', 'tech': '盤堅向上'},
            {'id': '2376', 'name': '技嘉', 'weight': 1.10, 'chips': '投信承接', 'tech': '區間震盪'},
            {'id': '3231', 'name': '緯創', 'weight': 1.00, 'chips': '洗清籌碼', 'tech': '破底翻'},
            {'id': '2382', 'name': '廣達', 'weight': 0.90, 'chips': '穩健流入', 'tech': '多頭排列'},
            {'id': '3034', 'name': '聯詠', 'weight': 0.85, 'chips': '法人觀望', 'tech': '下探支撐'},
            {'id': '3008', 'name': '大立光', 'weight': 0.80, 'chips': '守穩千元', 'tech': '長期築底'}
        ]
    },
    '00992A': {
        'name': '群益科技創新', 'price': 16.93, 'change': '+1.62%', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼', 'tech': '高於週VWAP'},
            {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼', 'tech': '多頭排列'},
            {'id': '3105', 'name': '穩懋', 'weight': 4.50, 'chips': '跌深反彈', 'tech': '帶量長紅'},
            {'id': '6223', 'name': '旺矽', 'weight': 4.20, 'chips': '融資減肥', 'tech': '回測支撐'},
            {'id': '3037', 'name': '欣興', 'weight': 3.80, 'chips': '法人回補', 'tech': '站穩三線'},
            {'id': '6515', 'name': '穎崴', 'weight': 3.50, 'chips': '特定買盤', 'tech': '三角收斂'}
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
            {'id': '3037', 'name': '欣興', 'weight': 1.25, 'chips': '新進成員', 'tech': '高權重加碼'},
            {'id': '2344', 'name': '華邦電', 'weight': 0.85, 'chips': '新進成員', 'tech': '底部反彈'},
            {'id': '2368', 'name': '金像電', 'weight': 0.70, 'chips': '新進成員', 'tech': '強勢補漲'},
            {'id': '3017', 'name': '奇鋐', 'weight': 1.11, 'chips': '散熱大廠', 'tech': '高檔震盪'},
            {'id': '2345', 'name': '智邦', 'weight': 1.10, 'chips': '交換器熱', 'tech': '仰角拉升'},
            {'id': '2382', 'name': '廣達', 'weight': 0.99, 'chips': '力撐權值', 'tech': '季線支撐'},
            {'id': '2303', 'name': '聯電', 'weight': 0.90, 'chips': '低檔買盤', 'tech': '黃金交叉'},
            {'id': '2881', 'name': '富邦金', 'weight': 0.85, 'chips': '金融領頭', 'tech': '盤堅向上'},
            {'id': '2882', 'name': '國泰金', 'weight': 0.80, 'chips': '投信回補', 'tech': '站回月線'},
            {'id': '2412', 'name': '中華電', 'weight': 0.75, 'chips': '避險資金專區', 'tech': '防禦守勢'},
            {'id': '2891', 'name': '中信金', 'weight': 0.70, 'chips': '官股穩盤', 'tech': '緩步墊高'},
            {'id': '5871', 'name': '中租-KY', 'weight': 0.65, 'chips': '獲利穩健', 'tech': '箱型震盪'},
            {'id': '2886', 'name': '兆豐金', 'weight': 0.60, 'chips': '官股平穩', 'tech': '緩步墊高'},
            {'id': '1303', 'name': '南亞', 'weight': 0.55, 'chips': '低檔佈局', 'tech': '築底期'},
            {'id': '2002', 'name': '中鋼', 'weight': 0.50, 'chips': '景氣復甦', 'tech': '橫向整理'},
            {'id': '1301', 'name': '台塑', 'weight': 0.45, 'chips': '集團佈局', 'tech': '低位震盪'},
            {'id': '1216', 'name': '統一', 'weight': 0.40, 'chips': '法人認養', 'tech': '盤堅向上'},
            {'id': '2884', 'name': '玉山金', 'weight': 0.35, 'chips': '散戶最愛', 'tech': '均線糾結'},
            {'id': '2357', 'name': '華碩', 'weight': 0.30, 'chips': 'AI PC題材', 'tech': '帶量噴發'},
            {'id': '2892', 'name': '第一金', 'weight': 0.25, 'chips': '穩定配息', 'tech': '緩漲格局'},
            {'id': '2885', 'name': '元大金', 'weight': 0.25, 'chips': '證券龍頭', 'tech': '創波段高'},
            {'id': '2880', 'name': '華南金', 'weight': 0.22, 'chips': '獲利穩健', 'tech': '盤整向上'},
            {'id': '3045', 'name': '台灣大', 'weight': 0.20, 'chips': '防禦標的', 'tech': '窄幅整理'},
            {'id': '2887', 'name': '台新金', 'weight': 0.18, 'chips': '底部起漲', 'tech': '均線多頭'},
            {'id': '2890', 'name': '永豐金', 'weight': 0.16, 'chips': '多頭排列', 'tech': '沿五日線'},
            {'id': '3008', 'name': '大立光', 'weight': 0.15, 'chips': '低檔買盤', 'tech': '長期築底'},
            {'id': '3037', 'name': '欣興', 'weight': 0.14, 'chips': 'ABF回溫', 'tech': '底部反彈'},
            {'id': '3034', 'name': '聯詠', 'weight': 0.13, 'chips': '法人吸納', 'tech': '盤間震盪'},
            {'id': '2395', 'name': '研華', 'weight': 0.12, 'chips': '工業控制', 'tech': '緩步墊高'},
            {'id': '2379', 'name': '瑞昱', 'weight': 0.11, 'chips': '網通龍頭', 'tech': '橫向整理'},
            {'id': '3231', 'name': '緯創', 'weight': 0.10, 'chips': 'AI代工', 'tech': '破底翻紅'},
            {'id': '2474', 'name': '可成', 'weight': 0.09, 'chips': '定存股首選', 'tech': '箱型震盪'},
            {'id': '4904', 'name': '遠傳', 'weight': 0.08, 'chips': '電信防禦', 'tech': '穩健攀升'},
            {'id': '5876', 'name': '上海商銀', 'weight': 0.08, 'chips': '低檔盤整', 'tech': '等待量增'},
            {'id': '4938', 'name': '和碩', 'weight': 0.07, 'chips': '組裝大廠', 'tech': '緩步墊高'},
            {'id': '8046', 'name': '南電', 'weight': 0.07, 'chips': '底部成型', 'tech': '低檔震盪'},
            {'id': '6488', 'name': '環球晶', 'weight': 0.06, 'chips': '矽晶圓熱', 'tech': '挑戰季線'},
            {'id': '2408', 'name': '南亞科', 'weight': 0.06, 'chips': '記憶體修復', 'tech': '回測支撐'},
            {'id': '2301', 'name': '光寶科', 'weight': 0.05, 'chips': '雲端電源', 'tech': '底部盤整'},
            {'id': '9910', 'name': '豐泰', 'weight': 0.05, 'chips': '消費復甦', 'tech': '打底區'},
            {'id': '9904', 'name': '寶成', 'weight': 0.04, 'chips': '資產開發', 'tech': '低檔整理'},
            {'id': '2101', 'name': '南港', 'weight': 0.04, 'chips': '輪胎龍頭', 'tech': '帶量突破'},
            {'id': '2356', 'name': '英業達', 'weight': 0.04, 'chips': '伺服器熱', 'tech': '高檔震盪'},
            {'id': '2347', 'name': '聯強', 'weight': 0.03, 'chips': '通路龍頭', 'tech': '高息守護'},
            {'id': '2883', 'name': '凱基金', 'weight': 0.03, 'chips': '金控佈局', 'tech': '底部翻紅'},
            {'id': '2207', 'name': '和泰車', 'weight': 0.02, 'chips': '車市龍頭', 'tech': '緩步墊高'}
        ]
    }
}

async def fetch_yahoo_kline(symbol, suffix, client):
    full_symbol = f"{symbol}{suffix}" if "." not in symbol else symbol
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{full_symbol}?interval=1d&range=2mo"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = await client.get(url, headers=headers, timeout=15.0)
        data = resp.json()
        if data and 'chart' in data and data['chart']['result']:
            res = data['chart']['result'][0]
            ts, q = res['timestamp'], res['indicators']['quote'][0]
            h = []
            for i in range(len(ts)):
                if q['close'][i] is not None and q['volume'][i] is not None:
                    h.append({"t": ts[i], "o": q['open'][i], "c": q['close'][i], "v": q['volume'][i]})
            return h[-35:]
    except: return None

async def update_prices():
    all_s = set()
    for eid, data in etf_base_data.items():
        tick = "0050.TW" if eid=="0050" else (eid+".TW")
        all_s.add(tick)
        for s in data['holdings']: all_s.add(s['id'])
            
    quotes = {}
    async with httpx.AsyncClient() as client:
        for s in list(all_s):
            res = await fetch_yahoo_kline(s, "" if "." in s else ".TW", client)
            if not res and "." not in s: res = await fetch_yahoo_kline(s, ".TWO", client)
            if res: quotes[s] = res

    for eid, data in etf_base_data.items():
        tick = "0050.TW" if eid=="0050" else (eid+".TW")
        if tick in quotes:
            q = quotes[tick]; data['price'] = round(q[-1]['c'], 2)
            chg = (q[-1]['c'] - q[-2]['c']) / q[-2]['c'] * 100
            data['change'] = f"{chg:+.2f}%"

        for st in data['holdings']:
            if st['id'] in quotes:
                q = quotes[st['id']]
                p, prev_p = q[-1]['c'], q[-2]['c']
                chg_p = (p - prev_p) / prev_p * 100
                st.update({'price': p, 'change': f"{chg_p:+.2f}%", 'history': q})
                avg_v = sum(d['v'] for d in q[-5:]) / 5
                v_ratio = q[-1]['v'] / avg_v if avg_v > 0 else 1
                if chg_p > 0.5: vp = "價漲量增" if v_ratio > 1.1 else "價漲量縮"
                elif chg_p < -0.5: vp = "價跌量增" if v_ratio > 1.1 else "價跌量縮"
                else: vp = "量縮整理"
                st['vp_analysis'] = vp
                st['is_new'] = st['id'] in NEW_STOCKS

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(etf_base_data, f, ensure_ascii=False, indent=4)
    print("🎊 數據全數恢復完成")

if __name__ == "__main__": asyncio.run(update_prices())
