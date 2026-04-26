import asyncio
import re
import json
import httpx
from datetime import datetime

html_file = "index.html"

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
            {'id': '6515', 'name': '穎崴', 'weight': 3.50, 'chips': '特定買盤', 'tech': '三角收斂'},
            {'id': '2454', 'name': '聯發科', 'weight': 3.20, 'chips': '主力作多', 'tech': '穩步墊高'},
            {'id': '2382', 'name': '廣達', 'weight': 2.90, 'chips': '籌碼穩定', 'tech': '均線糾結'},
            {'id': '3231', 'name': '緯創', 'weight': 2.70, 'chips': '散戶退場', 'tech': '跌破月線'},
            {'id': '2376', 'name': '技嘉', 'weight': 2.50, 'chips': '法人首選', 'tech': '突破平台'},
            {'id': '3330', 'name': '光聖', 'weight': 2.20, 'chips': '光通訊熱', 'tech': '噴發創高'},
            {'id': '4510', 'name': '高力', 'weight': 2.00, 'chips': '節能題材', 'tech': '帶量上攻'},
            {'id': '3661', 'name': '世芯-KY', 'weight': 1.80, 'chips': '法人控盤', 'tech': '高檔震盪'},
            {'id': '2303', 'name': '聯電', 'weight': 1.60, 'chips': '低接支撐', 'tech': '低檔盤旋'},
            {'id': '3711', 'name': '日月光投控', 'weight': 1.50, 'chips': '內資佈局', 'tech': '緩步墊高'},
            {'id': '8299', 'name': '群聯', 'weight': 1.40, 'chips': '記憶體修復', 'tech': '站上季線'},
            {'id': '3529', 'name': '力旺', 'weight': 1.30, 'chips': 'IP大廠', 'tech': '創波段高'},
            {'id': '2308', 'name': '台達電', 'weight': 1.20, 'chips': '權值吸納', 'tech': '多頭排列'},
            {'id': '2345', 'name': '智邦', 'weight': 1.10, 'chips': '投信首選', 'tech': '仰角拉升'}
        ]
    },
    '0050': {
        'name': '元大台灣50', 'price': 195.0, 'change': '+1.2%', 'scale': '4,500 億', 'topWeight': '51.2%', 'vwap': '權值護盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 51.2, 'chips': '外資買超', 'tech': '歷史新高'},
            {'id': '2317', 'name': '鴻海', 'weight': 8.3, 'chips': 'AI題材', 'tech': '季線反彈'},
            {'id': '2454', 'name': '聯發科', 'weight': 4.1, 'chips': '法人卡位', 'tech': '底部翻揚'},
            {'id': '2382', 'name': '廣達', 'weight': 2.8, 'chips': '主力鎖碼', 'tech': '量增突破'},
            {'id': '2308', 'name': '台達電', 'weight': 2.6, 'chips': '長線佈局', 'tech': '站穩均線'},
            {'id': '2303', 'name': '聯電', 'weight': 2.4, 'chips': '低檔買盤', 'tech': '黃金交叉'},
            {'id': '3711', 'name': '日月光投控', 'weight': 1.9, 'chips': '拉回找買點', 'tech': '帶量突破'},
            {'id': '2881', 'name': '富邦金', 'weight': 1.7, 'chips': '金融龍頭', 'tech': '穩定向上'},
            {'id': '2882', 'name': '國泰金', 'weight': 1.5, 'chips': '投信青睞', 'tech': '站回月線'},
            {'id': '2412', 'name': '中華電', 'weight': 1.4, 'chips': '避險資金專區', 'tech': '防禦守勢'},
            {'id': '2891', 'name': '中信金', 'weight': 1.3, 'chips': '大戶承接', 'tech': '多頭排列'},
            {'id': '5871', 'name': '中租-KY', 'weight': 1.1, 'chips': '獲利穩健', 'tech': '箱型震盪'},
            {'id': '2886', 'name': '兆豐金', 'weight': 1.0, 'chips': '官股穩盤', 'tech': '緩步墊高'},
            {'id': '1303', 'name': '南亞', 'weight': 0.9, 'chips': '基本面復甦', 'tech': '底部築底'},
            {'id': '2002', 'name': '中鋼', 'weight': 0.8, 'chips': '春燕回來了', 'tech': '反彈格局'},
            {'id': '1301', 'name': '台塑', 'weight': 0.8, 'chips': '集團佈局', 'tech': '低檔震盪'},
            {'id': '1216', 'name': '統一', 'weight': 0.8, 'chips': '法人認養', 'tech': '盤堅向上'},
            {'id': '2884', 'name': '玉山金', 'weight': 0.7, 'chips': '散戶最愛', 'tech': '均線糾結'},
            {'id': '2357', 'name': '華碩', 'weight': 0.7, 'chips': 'AI PC題材', 'tech': '帶量噴發'},
            {'id': '2892', 'name': '第一金', 'weight': 0.6, 'chips': '穩定配息', 'tech': '緩漲格局'},
            {'id': '2885', 'name': '元大金', 'weight': 0.6, 'chips': '證券龍頭', 'tech': '創波段高'},
            {'id': '2880', 'name': '華南金', 'weight': 0.6, 'chips': '資產品質佳', 'tech': '盤整向上'},
            {'id': '3045', 'name': '台灣大', 'weight': 0.5, 'chips': '現金流強', 'tech': '防禦標的'},
            {'id': '2887', 'name': '台新金', 'weight': 0.5, 'chips': '獲利成長', 'tech': '底部起漲'},
            {'id': '2890', 'name': '永豐金', 'weight': 0.5, 'chips': '基本面強', 'tech': '多頭格局'},
            {'id': '3008', 'name': '大立光', 'weight': 0.5, 'chips': '潛望鏡紅利', 'tech': '打底完成'},
            {'id': '3037', 'name': '欣興', 'weight': 0.4, 'chips': '載板龍頭', 'tech': '低位反彈'},
            {'id': '3034', 'name': '聯詠', 'weight': 0.4, 'chips': '毛利回升', 'tech': '震盪上行'},
            {'id': '2395', 'name': '研華', 'weight': 0.4, 'chips': '工業控制', 'tech': '緩步墊高'},
            {'id': '2379', 'name': '瑞昱', 'weight': 0.4, 'chips': '網通強勢', 'tech': '挑戰新高'},
            {'id': '3231', 'name': '緯創', 'weight': 0.4, 'chips': 'AI代工', 'tech': '破底翻紅'},
            {'id': '2474', 'name': '可成', 'weight': 0.4, 'chips': '現金充沛', 'tech': '定存股首選'},
            {'id': '4904', 'name': '遠傳', 'weight': 0.3, 'chips': '電信三強', 'tech': '防守格局'},
            {'id': '5876', 'name': '上海商銀', 'weight': 0.3, 'chips': '利差優勢', 'tech': '低檔震盪'},
            {'id': '4938', 'name': '和碩', 'weight': 0.3, 'chips': '組裝大廠', 'tech': '緩步墊高'},
            {'id': '8046', 'name': '南電', 'weight': 0.3, 'chips': 'ABF回溫', 'tech': '底部成型'},
            {'id': '6488', 'name': '環球晶', 'weight': 0.3, 'chips': '矽晶圓熱', 'tech': '回測5日線'},
            {'id': '2408', 'name': '南亞科', 'weight': 0.3, 'chips': 'DRAM漲價', 'tech': '橫向整理'},
            {'id': '2301', 'name': '光寶科', 'weight': 0.3, 'chips': '雲端題材', 'tech': '回測季線'},
            {'id': '9910', 'name': '豐泰', 'weight': 0.2, 'chips': '消費復甦', 'tech': '打底區'},
            {'id': '9004', 'name': '寶成', 'weight': 0.2, 'chips': '低價龍頭', 'tech': '突破平台'},
            {'id': '2101', 'name': '南港', 'weight': 0.2, 'chips': '資產概念', 'tech': '強勢格局'},
            {'id': '2356', 'name': '英業達', 'weight': 0.2, 'chips': '伺服器熱', 'tech': '高檔震盪'},
            {'id': '2347', 'name': '聯強', 'weight': 0.2, 'chips': '通路王', 'tech': '高息保護'},
            {'id': '2324', 'name': '仁寶', 'weight': 0.2, 'chips': '投信低接', 'tech': '緩漲格局'},
            {'id': '2353', 'name': '宏碁', 'weight': 0.2, 'chips': 'PC復甦', 'tech': '震盪築底'},
            {'id': '9921', 'name': '巨大', 'weight': 0.2, 'chips': '自行車龍頭', 'tech': '庫存去化'},
            {'id': '6505', 'name': '台塑化', 'weight': 0.2, 'chips': '油價支撐', 'tech': '跌深反彈'},
            {'id': '1101', 'name': '台泥', 'weight': 0.2, 'chips': '綠能佈局', 'tech': '底部成型'}
        ]
    }
}

async def fetch_yahoo_kline(symbol, suffix, client):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}{suffix}?interval=1d&range=2mo"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = await client.get(url, headers=headers, timeout=5.0)
        data = resp.json()
        if data and 'chart' in data and data['chart']['result']:
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            history = []
            for i in range(len(timestamps)):
                o = quotes['open'][i]
                c = quotes['close'][i]
                h = quotes['high'][i]
                l = quotes['low'][i]
                v = quotes['volume'][i]
                if c is not None and o is not None and h is not None and l is not None and v is not None:
                    history.append({
                        "t": timestamps[i],
                        "o": round(o, 2),
                        "c": round(c, 2),
                        "hPrice": round(h, 2),
                        "lPrice": round(l, 2),
                        "v": v
                    })
            if not history: return None
            return history[-35:] if len(history) >= 35 else history
    except:
        return None
    return None

async def update_prices():
    all_symbols = set()
    for etf, data in etf_base_data.items():
        for stock in data['holdings']:
            all_symbols.add(stock['id'])
            
    print(f"📡 正在透過 Yahoo Finance API 抓取 {len(all_symbols)} 檔真實 K 線(2個月)...")
    
    quotes = {}
    async with httpx.AsyncClient() as client:
        symbol_list = list(all_symbols)
        chunk_size = 10
        for i in range(0, len(symbol_list), chunk_size):
            chunk = symbol_list[i:i+chunk_size]
            tasks = []
            for s in chunk:
                suffix = ".TW" if len(s) == 4 else ".TWO"
                tasks.append(fetch_yahoo_kline(s, suffix, client))
            
            results = await asyncio.gather(*tasks)
            for s, res in zip(chunk, results):
                if res:
                    quotes[s] = res
    
    updated_count = 0
    for etf_id, data in etf_base_data.items():
        for stock in data['holdings']:
            s_id = stock['id']
            if s_id in quotes:
                q = quotes[s_id]
                p = q[-1]['c']
                prev_p = q[-2]['c'] if len(q) > 1 else p
                chg_amt = p - prev_p
                chg_p = (chg_amt / prev_p) * 100
                chg_text = f"{chg_amt:+.1f} ({chg_p:+.2f}%)"
                chg_text = ("▲ " if chg_p >= 0 else "▼ ") + chg_text
                
                avg_vol = sum(day['v'] for day in q[-5:]) / 5 if len(q) >= 5 else q[-1]['v']
                vol_ratio = q[-1]['v'] / avg_vol if avg_vol > 0 else 1
                
                if chg_p > 0.5:
                    vp_status = "價漲量增: 攻擊動能強" if vol_ratio > 1.1 else "價漲量縮: 追價意願弱"
                elif chg_p < -0.5:
                    vp_status = "價跌量增: 恐慌性拋售" if vol_ratio > 1.1 else "價跌量縮: 尋求支撐中"
                else:
                    vp_status = "量縮整理: 觀望買盤支撐"
                
                stock['price'] = p
                stock['change'] = chg_text
                stock['vp_analysis'] = vp_status
                stock['history'] = q
                updated_count += 1

    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    new_data_js = f"const etfData = {json.dumps(etf_base_data, ensure_ascii=False, indent=4)};"
    updated_content = re.sub(r"const etfData = \{.*?\};", new_data_js, content, flags=re.DOTALL)
    
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    print(f"\n🎊 完成！成功更新 {updated_count} 檔股票資訊。")

if __name__ == "__main__":
    asyncio.run(update_prices())
