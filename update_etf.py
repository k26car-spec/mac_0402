import asyncio
import json
import httpx
import os

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
    url = "https://www.twse.com.tw/fund/T86?response=open_data"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=30)
            chips = {}
            for line in res.text.split("\n")[1:]:
                parts = line.replace('"', '').split(",")
                if len(parts) >= 11:
                    chips[parts[0].strip()] = int(int(parts[10])/1000)
            return chips
    except: return {}

etf_base_data = {
    '00981A': { 'name': '統一台股增長', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 8.55},
        {'id': '3037', 'name': '欣興', 'weight': 2.50, 'is_new': True},
        {'id': '2454', 'name': '聯發科', 'weight': 6.20},
        {'id': '2317', 'name': '鴻海', 'weight': 4.10},
        {'id': '2383', 'name': '台光電', 'weight': 4.80}
    ]},
    '0050': { 'name': '元大台灣50', 'scale': '4,500 億', 'topWeight': '51.52%', 'vwap': '權值護盤', 'holdings': [
        {'id': '2330', 'name': '台積電', 'weight': 51.52},
        {'id': '2317', 'name': '鴻海', 'weight': 3.14},
        {'id': '2454', 'name': '聯發科', 'weight': 3.23}
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
                
                # 計算 VWAP
                total_val = sum([x['c'] * x['v'] for x in q])
                total_vol = sum([x['v'] for x in q])
                vw_avg = total_val/total_vol if total_vol > 0 else p
                dist = ((p - vw_avg) / vw_avg) * 100
                
                st.update({'price': p, 'change': f"{p-p_p:+.1f} ({((p-p_p)/p_p*100):+.2f}%)", 'history': q})
                
                # --- 數值化差異分析 ---
                st['vwap_pos'] = f"{'💪' if dist > 0 else '📉'} {'高於' if dist > 0 else '低於'} VWAP {abs(dist):.1f}%"
                
                vol_ratio = v / v_p if v_p > 0 else 1.0
                st['vp_analysis'] = f"{'⚡ 量能' if vol_ratio > 1.2 else '🐢 量縮'} {vol_ratio:.1f}倍 {'(向上)' if p > p_p else '(向下)'}"
                
                if sid in c_map:
                    nb = c_map[sid]
                    st['net_buy'] = f"{nb:+d}"
                    st['chips'] = f"{'🔥 投信積極' if nb > 500 else ('👍 投信認養' if nb > 0 else '💤 法人觀望')}"
                else:
                    st['chips'] = "💤 無法人數據"
                    st['net_buy'] = "+0"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({ "etf_data": etf_base_data, "common_holdings": [] }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__": asyncio.run(run())
