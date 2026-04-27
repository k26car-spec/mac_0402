import asyncio
import json
import httpx
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

data_file = "data.json"

# ─────────────────────────────────────────────
# [修正四] fetch_yahoo_full：補抓 high / low
#          以便後續計算標準 VWAP 典型價格
# ─────────────────────────────────────────────
async def fetch_yahoo_full(s, client):
    suffixes = [".TW", ".TWO"]
    if "00981" in s:
        suffixes = [".TW"]
    for suffix in suffixes:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{s}{suffix}"
            f"?interval=1d&range=5d"
        )
        try:
            r = await client.get(url, headers={"User-Agent": "Mozilla"}, timeout=12)
            if r.status_code != 200:
                continue
            res = r.json()["chart"]["result"][0]
            ts = res["timestamp"]
            q = res["indicators"]["quote"][0]
            bars = []
            for i in range(len(ts)):
                c = q["close"][i]
                if c is None:
                    continue
                o = q["open"][i] or c
                bars.append(
                    {
                        "t": ts[i],
                        "o": o,
                        "c": c,
                        "hPrice": q["high"][i] or c,   # 補 high
                        "lPrice": q["low"][i] or c,    # 補 low
                        "v": q["volume"][i] or 0,
                    }
                )
            return bars
        except Exception:
            continue
    return None


async def get_twse_official():
    chips = {}
    async with httpx.AsyncClient() as client:
        # TWSE 上市
        for d_back in range(10):
            try:
                date_str = (datetime.now() - timedelta(days=d_back)).strftime("%Y%m%d")
                url = (
                    f"https://www.twse.com.tw/fund/T86"
                    f"?response=json&date={date_str}&selectType=ALL"
                )
                res = await client.get(url, timeout=10)
                data = res.json()
                if "data" in data and len(data["data"]) > 100:
                    fields = data["fields"]
                    idx_id = fields.index("證券代號")
                    idx_trust = fields.index("投信買賣超股數")
                    for row in data["data"]:
                        try:
                            val = int(row[idx_trust].replace(",", ""))
                            chips[row[idx_id].strip()] = int(val / 1000)
                        except Exception:
                            pass
                    break
            except Exception:
                pass

        # TPEx (櫃買)
        for d_back in range(10):
            try:
                d = datetime.now() - timedelta(days=d_back)
                date_str = f"{d.year - 1911}/{d.strftime('%m/%d')}"
                url_otc = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={date_str}"
                res_otc = await client.get(url_otc, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                data_otc = res_otc.json()
                if "tables" in data_otc and len(data_otc["tables"]) > 0:
                    rows = data_otc["tables"][0].get("data", [])
                    if len(rows) > 100:
                        for row in rows:
                            try:
                                # 第 13 欄為「投信買賣超股數」
                                val = int(row[13].replace(",", ""))
                                chips[row[0].strip()] = int(val / 1000)
                            except Exception:
                                pass
                        break
            except Exception:
                pass
    return chips


async def get_name_to_id():
    name_to_id = {}
    async with httpx.AsyncClient() as client:
        try:
            r1 = await client.get(
                "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data",
                timeout=10,
            )
            for line in r1.text.split("\n")[1:]:
                parts = line.replace('"', "").split(",")
                if len(parts) > 2:
                    name_to_id[parts[2].strip()] = parts[1].strip()
            r2 = await client.get(
                "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", timeout=10
            )
            for item in r2.json():
                name_to_id[item["CompanyName"].strip()] = item[
                    "SecuritiesCompanyCode"
                ].strip()
        except Exception:
            pass
    return name_to_id


async def scrape_etf_holdings(etf_id, name_to_id):
    holdings = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 特別處理統一投信 (00981A)：同時抓取 Share（股數）用於計算 ETF 自身買賣超
        if etf_id == "00981A":
            try:
                import html as _html, re as _re
                url = "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=49YTW"
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                decoded = _html.unescape(r.text)
                # 額外抓取基金規格數據 (規模, 淨值, 現金比, 期貨)
                meta = {}
                try:
                    f_asset = _re.search(r'"FundAsset":([\d\.]+)', decoded)
                    if f_asset:
                        scale_val = float(f_asset.group(1))
                        meta["scale"] = f"{int(scale_val / 100000000):,} 億"
                    
                    f_nav = _re.search(r'"FundNav":([\d\.]+)', decoded)
                    if f_nav: meta["price"] = f_nav.group(1)
                    
                    f_rate = _re.search(r'"FundNavRate":([\d\.\+\-]+)', decoded)
                    if f_rate: meta["change"] = f"{float(f_rate.group(1)):+.2f}%"
                    
                    # 抓資產配置 (現金與期貨)
                    f_cash = _re.search(r'"AssetCode":"Cash","AssetRate":([\d\.]+)', decoded)
                    if f_cash: meta["cash_ratio"] = f"{f_cash.group(1)}%"
                    
                    f_fut = _re.search(r'"AssetCode":"Futures","AssetRate":([\d\.]+)', decoded)
                    if f_fut: meta["futures_margin"] = f"{f_fut.group(1)}%"
                except:
                    pass

                if holdings:
                    return sorted(holdings, key=lambda x: x["weight"], reverse=True), meta
            except Exception:
                pass
            if holdings:
                return sorted(holdings, key=lambda x: x["weight"], reverse=True), {}

        # 特別處理群益投信 (00992A)
        if etf_id == "00992A":
            try:
                url = "https://www.capitalfund.com.tw/etf/product/detail/500/portfolio"
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                rows = soup.find_all("div", class_=lambda c: c and "tr" in c.split())
                for row in rows:
                    divs = row.find_all("div")
                    texts = [d.text.strip() for d in divs]
                    if len(texts) >= 3 and "%" in texts[2]:
                        try:
                            w = float(texts[2].replace("%", ""))
                            if w > 0:
                                holdings.append({"id": texts[0], "name": texts[1], "weight": w})
                        except Exception:
                            pass
            except Exception:
                pass
            if holdings:
                return sorted(holdings, key=lambda x: x["weight"], reverse=True)

        # 其他 ETF (元大 0050 等) 使用 MoneyDJ
        try:
            url = f"https://www.moneydj.com/ETF/X/Basic/Basic0007A.xdjhtm?etfid={etf_id}.TW"
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for t in soup.find_all("table"):
                rows = t.find_all("tr")
                if len(rows) > 3:
                    sample = [col.text.strip().replace("\u3000", "") for col in rows[1].find_all("td")]
                    if len(sample) > 3 and "%" in sample[3] and "." in sample[2]:
                        for row in rows[1:]:
                            cols = [c.text.strip().replace("\u3000", "") for c in row.find_all("td")]
                            if len(cols) > 3 and name_to_id.get(cols[0]):
                                holdings.append({"id": name_to_id[cols[0]], "name": cols[0], "weight": float(cols[2])})
        except Exception:
            pass
    return sorted(holdings, key=lambda x: x["weight"], reverse=True)


etf_base_data = {
    "00981A": {
        "name": "統一台股增長",
        "scale": "2,321 億",
        "price": "27.74",
        "change": "+0.36%",
        "cash_ratio": "6.60%",
        "futures_margin": "0.22%",
        "topWeight": "9.46%",   # 啟動時的預設值；run() 會動態覆蓋
        "vwap": "多頭鎖碼",
        "holdings": [
            {"id": "2330", "name": "台積電",   "weight": 8.55},
            {"id": "3037", "name": "欣興",     "weight": 2.50, "is_new": True},
            {"id": "2454", "name": "聯發科",   "weight": 6.20},
            {"id": "2317", "name": "鴻海",     "weight": 4.10},
            {"id": "2383", "name": "台光電",   "weight": 4.80},
            {"id": "3017", "name": "奇鋐",     "weight": 4.30},
            {"id": "2449", "name": "京元電",   "weight": 2.00, "is_new": True},
            {"id": "6223", "name": "旺矽",     "weight": 2.20},
            {"id": "2368", "name": "金像電",   "weight": 2.10},
            {"id": "2345", "name": "智邦",     "weight": 1.80},
            {"id": "3653", "name": "健策",     "weight": 1.60},
            {"id": "6669", "name": "緯穎",     "weight": 1.40},
        ],
    },
    "00992A": {
        "name": "群益科技創新",
        "scale": "468 億",
        "topWeight": "20.00%",
        "vwap": "權值撐盤",
        "holdings": [
            {"id": "2330", "name": "台積電", "weight": 20.00},
            {"id": "3037", "name": "欣興",   "weight": 3.80, "is_new": True},
            {"id": "6669", "name": "緯穎",   "weight": 4.80},
            {"id": "3105", "name": "穩懋",   "weight": 4.50},
            {"id": "2454", "name": "聯發科", "weight": 3.20},
            {"id": "2317", "name": "鴻海",   "weight": 2.90},
            {"id": "2368", "name": "金像電", "weight": 2.50},
        ],
    },
    "0050": {
        "name": "元大台灣50",
        "scale": "4,500 億",
        "topWeight": "51.52%",
        "vwap": "權值護盤",
        "holdings": [
            {"id": "2330", "name": "台積電", "weight": 51.52},
            {"id": "2317", "name": "鴻海",   "weight": 3.14},
            {"id": "2454", "name": "聯發科", "weight": 3.23},
            {"id": "2308", "name": "台達電", "weight": 3.93},
            {"id": "2303", "name": "聯電",   "weight": 1.85},
            {"id": "3711", "name": "日月光", "weight": 1.58},
            {"id": "2881", "name": "富邦金", "weight": 1.62},
            {"id": "2882", "name": "國泰金", "weight": 1.51},
            {"id": "2891", "name": "中信金", "weight": 1.12},
            {"id": "2412", "name": "中華電", "weight": 1.05},
            {"id": "2886", "name": "兆豐金", "weight": 0.92},
            {"id": "3037", "name": "欣興",   "weight": 1.25, "is_new": True},
            {"id": "2382", "name": "廣達",   "weight": 0.63},
            {"id": "3231", "name": "緯創",   "weight": 0.60},
            {"id": "3008", "name": "大立光", "weight": 0.45},
            {"id": "2885", "name": "元大金", "weight": 0.42},
            {"id": "2912", "name": "統一超", "weight": 0.41},
            {"id": "2892", "name": "第一金", "weight": 0.40},
            {"id": "5880", "name": "合庫金", "weight": 0.38},
        ],
    },
}


# ─────────────────────────────────────────────
# [修正三] 讀取上次 data.json 的成分股清單，
#          用來判斷「這次爬蟲新出現的股票」才是真正 is_new
# ─────────────────────────────────────────────
def load_previous_holdings() -> dict:
    """
    回傳 {
      etf_id: {
        'ids': {股票代號, ...},
        'shares': {股票代號: 股數, ...}  ← 用於計算 00981A 自身買賣超
      }
    }
    """
    if not os.path.exists(data_file):
        return {}
    try:
        with open(data_file, encoding="utf-8") as f:
            saved = json.load(f)
        result = {}
        for eid, d in saved.get("etf_data", {}).items():
            result[eid] = {
                "ids": {s["id"] for s in d.get("holdings", [])},
                "shares": {s["id"]: s.get("shares", 0) for s in d.get("holdings", [])},
                "names": {s["id"]: s.get("name", "") for s in d.get("holdings", [])},
            }
        return result
    except Exception:
        return {}


# ─────────────────────────────────────────────
# [修正四] 標準週 VWAP：使用典型價格 (H+L+C)/3
# ─────────────────────────────────────────────
def calc_vwap(bars: list[dict]) -> float:
    total_val = sum((b["hPrice"] + b["lPrice"] + b["c"]) / 3 * b["v"] for b in bars)
    total_vol = sum(b["v"] for b in bars)
    return total_val / total_vol if total_vol > 0 else bars[-1]["c"]


# ─────────────────────────────────────────────
# [修正二] 動態生成籌碼專家筆記
#          根據實際數據產生文字，不再硬編碼
# ─────────────────────────────────────────────
def generate_chip_notes(etf_data: dict) -> list[str]:
    notes = []
    for eid, data in etf_data.items():
        for st in data.get("holdings", []):
            nb_raw = st.get("net_buy", "盤後更新")
            if nb_raw == "盤後更新":
                continue
            try:
                nb = int(nb_raw)
            except ValueError:
                continue

            name = st["name"]
            sid = st["id"]
            vwap_pos = st.get("vwap_pos", "")
            below_vwap = "低於 VWAP" in vwap_pos

            # 強力買超且跌破 VWAP → 警示
            if nb > 500 and below_vwap:
                notes.append(
                    f"⚠️ **{name} ({sid})**：投信單日大買 {nb:+,} 張，"
                    f"但股價仍低於週 VWAP，籌碼與價格背離，需觀察後續走勢。"
                )
            # 強力賣超且跌破 VWAP → 警示
            elif nb < -500 and below_vwap:
                notes.append(
                    f"🔴 **{name} ({sid})**：投信單日大賣 {nb:+,} 張，"
                    f"且股價已低於週 VWAP，法人調節訊號明確，留意下檔風險。"
                )
            # 積極買超且高於 VWAP → 正面
            elif nb > 200:
                notes.append(
                    f"🔥 **{name} ({sid})**：投信積極買超 {nb:+,} 張，"
                    f"{'股價同步高於週 VWAP，多頭動能強勁。' if not below_vwap else '但股價尚低於週 VWAP，持續追蹤。'}"
                )
    if not notes:
        notes.append("今日暫無特別籌碼異動訊號，數據更新後將自動重新分析。")
    return notes


async def run():
    # 讀取上次成分股快照（用於 is_new 判斷）
    prev_holdings = load_previous_holdings()

    c_map = await get_twse_official()
    name_to_id = await get_name_to_id()

    # 動態爬蟲覆蓋預設持股
    if name_to_id:
        for eid in list(etf_base_data.keys()):
            res = await scrape_etf_holdings(eid, name_to_id)
            if res:
                if isinstance(res, tuple):
                    scraped, meta = res
                    if meta:
                        etf_base_data[eid].update(meta)
                else:
                    scraped = res
                
                prev_info = prev_holdings.get(eid, {"ids": set(), "shares": {}, "names": {}})
                prev_ids = prev_info.get("ids", set())
                prev_shares = prev_info.get("shares", {})

                for st in scraped:
                    # [修正三] is_new
                    if prev_ids and st["id"] not in prev_ids:
                        st["is_new"] = True

                    # ──────────────────────────────────────────────────────
                    # [修正五] 00981A 自身買賣超 = 今日股數 - 昨日股數
                    #          單位：股 → 張 (除以 1000)
                    # ──────────────────────────────────────────────────────
                    if eid == "00981A" and "shares" in st:
                        prev_s = prev_shares.get(st["id"], None)
                        if prev_s is not None:
                            delta_lots = int((st["shares"] - prev_s) / 1000)
                            st["etf_net_buy"] = delta_lots  # 儲存 ETF 自身買賣超

                # 處理被刪除的股票
                if eid == "00981A" and prev_ids:
                    scraped_ids = {st["id"] for st in scraped}
                    deleted_ids = prev_ids - scraped_ids
                    for del_id in deleted_ids:
                        del_name = prev_info.get("names", {}).get(del_id, str(del_id))
                        del_shares = prev_shares.get(del_id, 0)
                        scraped.append({
                            "id": del_id,
                            "name": del_name,
                            "weight": 0,
                            "shares": 0,
                            "etf_net_buy": -int(del_shares / 1000) if del_shares else -99999,
                            "is_deleted": True
                        })

                etf_base_data[eid]["holdings"] = scraped
                etf_base_data[eid]["topWeight"] = f"{scraped[0]['weight']:.2f}%"

    # 抓個股 + ETF 本身的 Yahoo Finance 報價
    async with httpx.AsyncClient() as client:
        all_sids = set(["00981A", "00992A", "0050"])
        for d in etf_base_data.values():
            for st in d["holdings"]:
                all_sids.add(st["id"])

        id_list = list(all_sids)
        tasks = [fetch_yahoo_full(sid, client) for sid in id_list]
        responses = await asyncio.gather(*tasks)
        q_map = {id_list[i]: res for i, res in enumerate(responses) if res}

    # 填入價格、VWAP、量能資訊
    for eid, data in etf_base_data.items():
        if eid in q_map:
            q = q_map[eid]
            data["price"] = round(q[-1]["c"], 2)
            data["change"] = f"{((q[-1]['c'] - q[-2]['c']) / q[-2]['c'] * 100):+.2f}%"

        for st in data.get("holdings", []):
            sid = st["id"]
            if sid in q_map:
                q = q_map[sid]
                p, p_p = q[-1]["c"], q[-2]["c"]
                v, v_p = q[-1]["v"], q[-2]["v"]

                # [修正四] 使用標準典型價格計算 VWAP
                vw_avg = calc_vwap(q)
                dist = (p - vw_avg) / vw_avg * 100

                st.update(
                    {
                        "price": p,
                        "change": f"{p - p_p:+.1f} ({((p - p_p) / p_p * 100):+.2f}%)",
                        "history": q,
                    }
                )
                st["vwap_pos"] = (
                    f"{'💪' if dist > 0 else '📉'} "
                    f"{'高於' if dist > 0 else '低於'} VWAP {abs(dist):.1f}%"
                )
                vol_ratio = v / v_p if v_p > 0 else 1.0
                st["vp_analysis"] = (
                    f"{'⚡ 量能' if vol_ratio > 1.2 else '🐢 量縮'} "
                    f"{vol_ratio:.1f}倍 {'(向上)' if p > p_p else '(向下)'}"
                )

            # ──────────────────────────────────────────────────────────
            # [修正五] 00981A 優先使用「ETF 自身持股變化」顯示基金動向
            #          其他 ETF 仍使用 T86 全市場投信合計買賣超
            # ──────────────────────────────────────────────────────────
            if eid == "00981A" and "etf_net_buy" in st:
                nb = st["etf_net_buy"]
                st["net_buy"] = f"{nb:+d}"
                st["chips"] = (
                    "🔥 本基金積極買入" if nb > 50
                    else "👍 本基金小幅買入" if nb > 0
                    else "💤 本基金減碼" if nb < 0
                    else "⚖️ 本基金持平"
                )
            elif sid in c_map:
                nb = c_map[sid]
                st["net_buy"] = f"{nb:+d}"
                st["chips"] = (
                    "🔥 投信積極" if nb > 100
                    else "👍 投信認養" if nb > 0
                    else "💤 法人賣超" if nb < 0
                    else "⚖️ 法人持平"
                )
            else:
                st["net_buy"] = "盤後更新"
                st["chips"] = "⏳ 盤後數據更新中"

    # [修正二] 動態生成籌碼筆記
    chip_notes = generate_chip_notes(etf_base_data)

    # 計算主力共識持股 (所有 ETF 皆持有的成分股)
    sets_of_names = []
    for data in etf_base_data.values():
        sets_of_names.append(set(st["name"] for st in data.get("holdings", [])))
    
    common_holdings = list(set.intersection(*sets_of_names)) if sets_of_names else []

    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "etf_data": etf_base_data,
                "chip_notes": chip_notes,          # 動態筆記寫入 JSON
                "common_holdings": common_holdings,
                "update_time": update_time,
            },
            f,
            ensure_ascii=False,
            indent=4,
        )
    print(f"✅ 更新完成：{update_time}，共 {len(chip_notes)} 則籌碼筆記")


if __name__ == "__main__":
    asyncio.run(run())
