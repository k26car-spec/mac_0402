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
            {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '投信瘋買/大戶鎖碼', 'tech': '高於週VWAP', 'history': [2080, 2100, 2095, 2130, 2185]},
            {'id': '2383', 'name': '台光電', 'weight': 7.15, 'chips': '法人掃貨/籌碼集中', 'tech': '噴發段/乖離大', 'history': [510, 508, 520, 535, 542]},
            {'id': '3653', 'name': '健策', 'weight': 6.27, 'chips': '融資大減/法人吸', 'tech': '回測0.382', 'history': [1300, 1310, 1290, 1320, 1350]},
            {'id': '2308', 'name': '台達電', 'weight': 5.98, 'chips': '特定分點買超', 'tech': '突破整理區', 'history': [405, 410, 415, 420, 428.5]},
            {'id': '2345', 'name': '智邦', 'weight': 5.26, 'chips': '投信連十買', 'tech': '仰角攻擊', 'history': [650, 660, 680, 700, 712]},
            {'id': '3017', 'name': '奇鋐', 'weight': 5.23, 'chips': '主力回流', 'tech': '高檔震盪', 'history': [930, 940, 920, 950, 980]},
            {'id': '2317', 'name': '鴻海', 'weight': 4.80, 'chips': '外資被動流入', 'tech': '上升通道', 'history': [240, 238, 242, 240, 245]},
            {'id': '2454', 'name': '聯發科', 'weight': 4.50, 'chips': '法人觀望', 'tech': '季線附近', 'history': [1420, 1430, 1415, 1440, 1450]},
            {'id': '2881', 'name': '富邦金', 'weight': 4.20, 'chips': '外資連買', 'tech': '盤整向上', 'history': [84.0, 84.5, 85.0, 85.2, 85.5]},
            {'id': '2882', 'name': '國泰金', 'weight': 3.90, 'chips': '投信小買', 'tech': '站上月線', 'history': [61.5, 62.0, 61.8, 62.5, 62.8]},
            {'id': '3231', 'name': '緯創', 'weight': 3.50, 'chips': '散戶退場', 'tech': '跌破均線', 'history': [128.0, 126.5, 125.0, 126.0, 125.0]},
            {'id': '2382', 'name': '廣達', 'weight': 3.40, 'chips': '投信低接', 'tech': '多頭排列', 'history': [300.0, 305.0, 302.0, 308.0, 310.5]},
            {'id': '3034', 'name': '聯詠', 'weight': 3.10, 'chips': '外資賣超', 'tech': '回測支撐', 'history': [585.0, 590.0, 582.0, 578.0, 580.0]},
            {'id': '2395', 'name': '研華', 'weight': 2.80, 'chips': '法人穩定佈局', 'tech': '緩步墊高', 'history': [380.0, 385.0, 382.0, 386.0, 388.0]},
            {'id': '2603', 'name': '長榮', 'weight': 2.50, 'chips': '大戶狂掃', 'tech': '帶量突破', 'history': [205.0, 208.0, 210.0, 212.0, 215.0]},
            {'id': '1519', 'name': '華城', 'weight': 2.20, 'chips': '投信認養', 'tech': '高檔強勢', 'history': [870.0, 880.0, 890.0, 905.0, 920.0]},
            {'id': '3443', 'name': '創意', 'weight': 2.00, 'chips': '融資增加', 'tech': '破底翻失敗', 'history': [1360.0, 1340.0, 1330.0, 1310.0, 1320.0]},
            {'id': '3661', 'name': '世芯-KY', 'weight': 1.86, 'chips': '外資回補', 'tech': '站穩五日線', 'history': [2750.0, 2780.0, 2800.0, 2820.0, 2850.0]}
        ]
    },
    '00992A': {
        'name': '群益科技創新', 'price': 16.93, 'change': '+1.62%', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法規紅利受惠者', 'tech': '高於週VWAP', 'history': [2080, 2100, 2095, 2130, 2185]},
            {'id': '6669', 'name': '緯穎', 'weight': 4.30, 'chips': '大戶持股創新高', 'tech': '整理區上緣', 'history': [2650, 2640, 2670, 2660, 2680]},
            {'id': '3105', 'name': '穩懋', 'weight': 5.10, 'chips': '空頭回補/放量', 'tech': '帶量長紅', 'history': [169, 172, 175, 180, 185]},
            {'id': '6223', 'name': '旺矽', 'weight': 4.58, 'chips': '融資暴增/獲利了結', 'tech': '跌破日VWAP', 'history': [495, 490, 488, 485, 482.5]},
            {'id': '3037', 'name': '欣興', 'weight': 3.50, 'chips': '投信重回認養', 'tech': '挑戰半年線', 'history': [205, 208, 210, 212, 215.5]},
            {'id': '6515', 'name': '穎崴', 'weight': 3.20, 'chips': '法人鎖籌碼', 'tech': '三角收斂末端', 'history': [1085, 1090, 1100, 1110, 1120]},
            {'id': '2454', 'name': '聯發科', 'weight': 3.10, 'chips': '外資逢低建倉', 'tech': '震盪築底', 'history': [1420, 1430, 1415, 1440, 1450]},
            {'id': '2382', 'name': '廣達', 'weight': 2.90, 'chips': '主力作多', 'tech': '均線糾結向上', 'history': [300.0, 305.0, 302.0, 308.0, 310.5]},
            {'id': '3231', 'name': '緯創', 'weight': 2.80, 'chips': '外資提款', 'tech': '跌破短天期均線', 'history': [128.0, 126.5, 125.0, 126.0, 125.0]},
            {'id': '2376', 'name': '技嘉', 'weight': 2.70, 'chips': '投信連買五日', 'tech': '突破整理平台', 'history': [360.0, 365.0, 370.0, 375.0, 380.0]},
            {'id': '3443', 'name': '創意', 'weight': 2.60, 'chips': '融券回補', 'tech': '下測年線', 'history': [1360.0, 1340.0, 1330.0, 1310.0, 1320.0]},
            {'id': '3661', 'name': '世芯-KY', 'weight': 2.50, 'chips': '投信控盤', 'tech': '高檔強勢整理', 'history': [2750.0, 2780.0, 2800.0, 2820.0, 2850.0]},
            {'id': '2303', 'name': '聯電', 'weight': 2.30, 'chips': '外資持續賣超', 'tech': '低檔鈍化', 'history': [54.5, 54.8, 55.0, 54.9, 55.2]},
            {'id': '3711', 'name': '日月光投控', 'weight': 2.20, 'chips': '內資接手', 'tech': '站上季線', 'history': [164.0, 165.0, 166.0, 167.0, 168.0]},
            {'id': '6415', 'name': '矽力*-KY', 'weight': 2.00, 'chips': '法人停損', 'tech': '均線蓋頭', 'history': [430.0, 425.0, 420.0, 415.0, 410.0]},
            {'id': '3529', 'name': '力旺', 'weight': 1.80, 'chips': '大戶積極吸碼', 'tech': '創波段新高', 'history': [2350.0, 2400.0, 2420.0, 2450.0, 2500.0]},
            {'id': '2308', 'name': '台達電', 'weight': 1.50, 'chips': '特定分點買超', 'tech': '突破整理區', 'history': [405, 410, 415, 420, 428.5]},
            {'id': '2345', 'name': '智邦', 'weight': 1.20, 'chips': '投信連十買', 'tech': '仰角攻擊', 'history': [650, 660, 680, 700, 712]}
        ]
    },
    '0050': {
        'name': '元大台灣50', 'price': 195.0, 'change': '+1.2%', 'scale': '4,500 億', 'topWeight': '51.2%', 'vwap': '權值護盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 51.2, 'chips': '外資認養', 'tech': '護國神山', 'history': [2080, 2100, 2095, 2130, 2185]},
            {'id': '2317', 'name': '鴻海', 'weight': 8.5, 'chips': 'AI伺服器商機', 'tech': '季線支撐', 'history': [240, 238, 242, 240, 245]},
            {'id': '2454', 'name': '聯發科', 'weight': 4.2, 'chips': '主力回補', 'tech': '築底向上', 'history': [1420, 1430, 1415, 1440, 1450]},
            {'id': '2308', 'name': '台達電', 'weight': 3.1, 'chips': '長線買盤', 'tech': '盤整區突破', 'history': [405, 410, 415, 420, 428.5]},
            {'id': '2382', 'name': '廣達', 'weight': 2.8, 'chips': '法人作多', 'tech': '量能增溫', 'history': [300.0, 305.0, 302.0, 308.0, 310.5]},
            {'id': '2303', 'name': '聯電', 'weight': 2.5, 'chips': '外資賣超轉買', 'tech': '底部翻揚', 'history': [54.5, 54.8, 55.0, 54.9, 55.2]},
            {'id': '3711', 'name': '日月光投控', 'weight': 2.0, 'chips': '半導體復甦', 'tech': '黃金交叉', 'history': [164.0, 165.0, 166.0, 167.0, 168.0]},
            {'id': '2881', 'name': '富邦金', 'weight': 1.8, 'chips': '金融股龍頭', 'tech': '穩步墊高', 'history': [84.0, 84.5, 85.0, 85.2, 85.5]},
            {'id': '2882', 'name': '國泰金', 'weight': 1.5, 'chips': '獲利雙雄', 'tech': '均線支撐', 'history': [61.5, 62.0, 61.8, 62.5, 62.8]},
            {'id': '2412', 'name': '中華電', 'weight': 1.3, 'chips': '避險資金', 'tech': '防禦型標的', 'history': [120, 122, 121, 123, 125]},
            {'id': '2891', 'name': '中信金', 'weight': 1.2, 'chips': '高配息期待', 'tech': '高檔橫盤', 'history': [36, 37, 36.5, 38, 38.2]},
            {'id': '1216', 'name': '統一', 'weight': 1.1, 'chips': '民生消費', 'tech': '多頭排列', 'history': [80, 82, 81, 83, 84]}
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
        for s in list(all_symbols):
            q = await fetch_yahoo_kline(s, ".TW", client)
            if not q:
                q = await fetch_yahoo_kline(s, ".TWO", client)
            if q:
                quotes[s] = q
            else:
                print(f"⚠️ 無法抓取 {s} 報價")
    
    updated_count = 0
    for etf, data in etf_base_data.items():
        for stock in data['holdings']:
            q = quotes.get(stock['id'])
            if q and len(q) > 0:
                stock['real_kline'] = q
                p = q[-1]['c']
                prev_p = q[-2]['c'] if len(q) > 1 else p
                chg_amt = p - prev_p
                chg_p = round((chg_amt / prev_p) * 100, 2) if prev_p else 0
                
                chg_text = f"{chg_amt:+.1f} ({chg_p:+.2f}%)"
                chg_text = ("▲ " if chg_p >= 0 else "▼ ") + chg_text
                
                # 量價分析邏輯
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
                stock['history'] = [day['c'] for day in q[-5:]] # sparkline needs 5 days of close prices
                updated_count += 1
                print(f"✅ 更新 {stock['id']} ({stock.get('name')}): {p} ({chg_text})")
            else:
                stock['price'] = stock['history'][-1]
                stock['change'] = '─ 0.00%'
                
    print(f"🎊 完成！成功更新 {updated_count} 檔股票歷史與最新報價。")

    js_data = json.dumps(etf_base_data, ensure_ascii=False, indent=4)
    replacement_str = f"const etfData = {js_data};"

    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    start_marker = "const etfData = {"
    end_marker = "function switchETF"
    
    start_idx = html.find(start_marker)
    end_idx = html.find(end_marker)
    
    if start_idx != -1 and end_idx != -1:
        # Find the last }; before function switchETF
        content_before = html[:start_idx]
        content_after = html[end_idx:]
        
        # We want to replace from start_idx to just before end_idx
        # But we need to be careful with the prefix/indentation
        new_html = content_before + replacement_str + "\n\n    " + content_after
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print(f"\n✅ 成功寫入 {html_file}")
    else:
        print(f"\n⚠️ 找不到標記: start={start_idx}, end={end_idx}")

if __name__ == "__main__":
    asyncio.run(update_prices())
