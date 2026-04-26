import asyncio
import json
import httpx
import os
from datetime import datetime

data_file = "docs/data.json"

async def fetch_yahoo_full(s, client):
    suffixes = [".TW", ".TWO"]
    if "00981" in s: suffixes = [".TW"]
    for suffix in suffixes:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}{suffix}?interval=1d&range=5d"
        try:
            r = await client.get(url, headers={'User-Agent': 'Mozilla'}, timeout=12)
            if r.status_code != 200: continue
            res = r.json()['chart']['result'][0]
            ts, q = res['timestamp'], res['indicators']['quote'][0]
            return [{"c": q['close'][i], "v": q['volume'][i] or 0} for i in range(len(ts)) if q['close'][i]]
        except: continue
    return None

async def get_twse_official():
    # 抓取三大法人買賣超 (T86)
    url = "https://www.twse.com.tw/fund/T86?response=open_data"
    try:
        async with httpx.AsyncClient() as client:
            import csv, io
            res = await client.get(url, timeout=30)
            rows = list(csv.reader(io.StringIO(res.text)))
            chips = {}
            trust_idx = -1
            if rows:
                for i, col in enumerate(rows[0]):
                    if "投信買賣超" in col:
                        trust_idx = i
                        break
            if trust_idx != -1:
                for row in rows[1:]:
                    if len(row) > trust_idx and row[0].strip():
                        ticker = row[0].strip()
                        try:
                            raw = row[trust_idx].strip().replace(",", "")
                            chips[ticker] = int(int(raw) / 1000)
                        except: continue
            # 若資料筆數 < 100，代表今天是假日，回傳空 dict 讓 UI 顯示「盤後更新」
            if len(chips) < 100:
                print(f"T86 only has {len(chips)} stocks - likely holiday, skipping chip data")
                return {}
            return chips
    except Exception as e:
        print(f"T86 error: {e}")
        return {}


etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55},
        {'id': '3037', 'name': '欣興', 'weight': 2.50, 'is_new': True},
        {'id': '2454', 'name': '聯發科', 'weight': 6.20},
        {'id': '2317', 'name': '鴻海', 'weight': 4.10},
        {'id': '2383', 'name': '台光電', 'weight': 4.80},
        {'id': '3017', 'name': '奇鋐', 'weight': 4.30},
        {'id': '2449', 'name': '京元電', 'weight': 2.00, 'is_new': True},
        {'id': '6223', 'name': '旺矽', 'weight': 2.20},
        {'id': '2368', 'name': '金像電', 'weight': 2.10},
        {'id': '2345', 'name': '智邦', 'weight': 1.80},
        {'id': '3653', 'name': '健策', 'weight': 1.60},
        {'id': '6669', 'name': '緯穎', 'weight': 1.40}
    ]},
    '00992A': { 'name': '群益科技創新', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 20.00},
        {'id': '3037', 'name': '欣興', 'weight': 3.80, 'is_new': True},
        {'id': '6669', 'name': '緯穎', 'weight': 4.80},
        {'id': '3105', 'name': '穩懋', 'weight': 4.50},
        {'id': '2454', 'name': '聯發科', 'weight': 3.20},
        {'id': '2317', 'name': '鴻海', 'weight': 2.90},
        {'id': '2368', 'name': '金像電', 'weight': 2.50}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23},
        {'id': '2308', 'name': '台達電', 'weight': 3.93},
        {'id': '2303', 'name': '聯電', 'weight': 1.85},
        {'id': '3711', 'name': '日月光', 'weight': 1.58},
        {'id': '2881', 'name': '富邦金', 'weight': 1.62},
        {'id': '2882', 'name': '國泰金', 'weight': 1.51},
        {'id': '2891', 'name': '中信金', 'weight': 1.12},
        {'id': '2412', 'name': '中華電', 'weight': 1.05},
        {'id': '2886', 'name': '兆豐金', 'weight': 0.92},
        {'id': '3037', 'name': '欣興', 'weight': 1.25, 'is_new': True},
        {'id': '2382', 'name': '廣達', 'weight': 0.63},
        {'id': '3231', 'name': '緯創', 'weight': 0.60},
        {'id': '3008', 'name': '大立光', 'weight': 0.45},
        {'id': '2885', 'name': '元大金', 'weight': 0.42},
        {'id': '2912', 'name': '統一超', 'weight': 0.41},
        {'id': '2892', 'name': '第一金', 'weight': 0.40},
        {'id': '5880', 'name': '合庫金', 'weight': 0.38}
    ]}
}

async def run():
    c_map = await get_twse_official()
    async with httpx.AsyncClient() as client:
        all_sids = set(["00981A", "0050"])
        for d in etf_base_data.values():
            for st in d['holdings']: all_sids.add(st['id'])
        
        id_list = list(all_sids)
        tasks = [fetch_yahoo_full(sid, client) for sid in id_list]
        responses = await asyncio.gather(*tasks)
        q_map = {id_list[i]: res for i, res in enumerate(responses) if res}

    for eid, data in etf_base_data.items():
        if eid in q_map:
            q = q_map[eid]
            data['price'] = round(q[-1]['c'], 2)
            data['change'] = f"{((q[-1]['c']-q[-2]['c'])/q[-2]['c']*100):+.2f}%"

        for st in data.get('holdings', []):
            sid = st['id']
            if sid in q_map:
                q = q_map[sid]
                p, p_p = q[-1]['c'], q[-2]['c']
                v, v_p = q[-1]['v'], q[-2]['v']
                total_val = sum([x['c'] * x['v'] for x in q])
                total_vol = sum([x['v'] for x in q])
                vw_avg = total_val/total_vol if total_vol > 0 else p
                dist = ((p - vw_avg) / vw_avg) * 100
                st.update({'price': p, 'change': f"{p-p_p:+.1f} ({((p-p_p)/p_p*100):+.2f}%)", 'history': q})
                st['vwap_pos'] = f"{'💪' if dist > 0 else '📉'} {'高於' if dist > 0 else '低於'} VWAP {abs(dist):.1f}%"
                vol_ratio = v / v_p if v_p > 0 else 1.0
                st['vp_analysis'] = f"{'⚡ 量能' if vol_ratio > 1.2 else '🐢 量縮'} {vol_ratio:.1f}倍 {'(向上)' if p > p_p else '(向下)'}"
            
            if sid in c_map:
                nb = c_map[sid]
                st['net_buy'] = f"{nb:+d}"
                st['chips'] = f"{'🔥 投信積極' if nb > 100 else ('👍 投信認養' if nb > 0 else ('💤 法人賣超' if nb < 0 else '⚖️ 法人持平'))}"
            else:
                st['net_buy'] = "盤後更新"
                st['chips'] = "⏳ 盤後數據更新中"

    # 更新時間標記
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": [], "update_time": update_time }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
