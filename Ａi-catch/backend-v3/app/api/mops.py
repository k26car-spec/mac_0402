"""
公開資訊觀測站 (MOPS) API
爬取重大訊息公告 + AI 分析展望
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import urllib.parse
from xml.etree import ElementTree

from fastapi import APIRouter, Query
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mops", tags=["MOPS 公開資訊觀測站"])


# ────────────────────────────────────────────
# 工具函數
# ────────────────────────────────────────────

def _classify_news(title: str) -> dict:
    """依標題關鍵字分類並賦予 AI 情緒評分"""
    title_lower = title.lower()
    positive_kw = ["獲利", "盈餘", "成長", "訂單", "合約", "中標", "投資", "新廠", "量產",
                   "漲價", "合作", "併購", "配股", "配息", "除息", "股利", "業績", "創高"]
    negative_kw = ["虧損", "下修", "停產", "火災", "停工", "裁員", "訴訟", "罰款", "違約",
                   "減資", "警示", "下市", "缺料", "召回", "重大損失"]
    neutral_kw  = ["股東會", "董事會", "法說會", "人事", "變更", "更名", "公告", "說明"]

    score = 0
    sentiment = "neutral"
    for kw in positive_kw:
        if kw in title:
            score += 1
    for kw in negative_kw:
        if kw in title:
            score -= 1

    if score > 0:
        sentiment = "positive"
    elif score < 0:
        sentiment = "negative"
    else:
        for kw in neutral_kw:
            if kw in title:
                sentiment = "neutral"
                break

    category = "其他"
    if any(k in title for k in ["財報", "盈餘", "獲利", "業績", "損益"]):
        category = "財務"
    elif any(k in title for k in ["訂單", "合約", "中標", "合作"]):
        category = "業務"
    elif any(k in title for k in ["股利", "配息", "配股", "除息"]):
        category = "股利"
    elif any(k in title for k in ["董事", "監察", "人事", "法說"]):
        category = "公司治理"
    elif any(k in title for k in ["新廠", "投資", "量產", "擴產"]):
        category = "投資擴產"

    return {"sentiment": sentiment, "score": score, "category": category}


async def _fetch_mops_news(stock_code: str) -> List[dict]:
    """爬取公開資訊觀測站重大訊息 (via MOPS 即時重訊)"""
    news_list = []
    headers = {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "Referer": "https://mops.twse.com.tw/",
    }

    # ── 主來源：MOPS 即時重訊 API ──
    try:
        mops_url = (
            "https://mops.twse.com.tw/mops/web/ajax_t05st01"
        )
        payload = {
            "encodeURIComponent": "1",
            "step": "1",
            "firstin": "true",
            "off": "1",
            "TYPEK": "all",
            "year": "",
            "month": "",
            "stock_id": stock_code,
        }
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            resp = await client.post(mops_url, data=payload)
            if resp.status_code == 200:
                text = resp.text
                # 抽取 <tr> rows
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.DOTALL)
                for row in rows[:20]:
                    cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                    if len(cols) >= 4:
                        date_str = re.sub(r'<[^>]+>', '', cols[0]).strip()
                        title    = re.sub(r'<[^>]+>', '', cols[2]).strip()
                        if not title or len(title) < 3:
                            continue
                        tag = _classify_news(title)
                        news_list.append({
                            "date": date_str,
                            "title": title,
                            "sentiment": tag["sentiment"],
                            "score": tag["score"],
                            "category": tag["category"],
                            "source": "MOPS",
                        })
    except Exception as e:
        logger.warning(f"MOPS 爬蟲失敗 {stock_code}: {e}")

    # ── 備援：TWSE 公告 API ──
    if not news_list:
        try:
            twse_url = (
                f"https://www.twse.com.tw/en/announcement/"
                f"report?response=json&stockNo={stock_code}"
            )
            async with httpx.AsyncClient(timeout=8, headers=headers) as client:
                resp = await client.get(twse_url)
                if resp.status_code == 200:
                    data = resp.json()
                    for row in data.get("data", [])[:10]:
                        if len(row) >= 3:
                            title = row[2] if len(row) > 2 else "公告"
                            tag = _classify_news(title)
                            news_list.append({
                                "date": row[0] if row else "",
                                "title": title,
                                "sentiment": tag["sentiment"],
                                "score": tag["score"],
                                "category": tag["category"],
                                "source": "TWSE",
                            })
        except Exception as e:
            logger.warning(f"TWSE 備援爬蟲失敗 {stock_code}: {e}")

    # ── 備援2：公開發行公司股東會及法說會日期 ──
    if not news_list:
        try:
            url = (
                f"https://mops.twse.com.tw/mops/web/ajax_t146sb05"
            )
            payload = {
                "encodeURIComponent": "1",
                "step": "1",
                "firstin": "true",
                "off": "1",
                "co_id": stock_code,
            }
            async with httpx.AsyncClient(timeout=8, headers=headers) as client:
                resp = await client.post(url, data=payload)
                if resp.status_code == 200:
                    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', resp.text, re.DOTALL)
                    for row in rows[:5]:
                        cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                        if len(cols) >= 2:
                            title = re.sub(r'<[^>]+>', '', cols[-1]).strip()
                            date  = re.sub(r'<[^>]+>', '', cols[0]).strip()
                            if title:
                                tag = _classify_news(title)
                                news_list.append({
                                    "date": date,
                                    "title": title,
                                    "sentiment": tag["sentiment"],
                                    "score": tag["score"],
                                    "category": tag["category"],
                                    "source": "MOPS-法說",
                                })
        except Exception as e:
            logger.debug(f"備援2失敗: {e}")

    # ── 擴充：爬取市場新聞與特定券商 (KGI 凱基) 評估報告 ──
    try:
        q_general = f"{stock_code} 目標價 OR 法人 OR 評估 OR 營收 when:7d"
        q_kgi = f"{stock_code} (凱基 OR KGI) (目標價 OR 收盤價 OR 評估) when:180d"
        
        url_general = f"https://news.google.com/rss/search?q={urllib.parse.quote(q_general)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        url_kgi = f"https://news.google.com/rss/search?q={urllib.parse.quote(q_kgi)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

        async with httpx.AsyncClient(verify=False, timeout=8) as client:
            resps = await asyncio.gather(
                client.get(url_general),
                client.get(url_kgi),
                return_exceptions=True
            )
            
            seen_titles = set([n["title"] for n in news_list])
            
            for idx, resp in enumerate(resps):
                if isinstance(resp, Exception) or resp.status_code != 200:
                    continue
                    
                root = ElementTree.fromstring(resp.text)
                source_tag = "外部新聞" if idx == 0 else "凱基(KGI)報告"
                
                # 一般新聞取前3篇，KGI取前3篇
                for item in root.findall('.//item')[:3]:
                    title = item.find('title').text
                    
                    # 過濾掉論壇、社群平台等非正式新聞與報告的雜訊，以及以假日期重發的機器人新聞（如鉅亨 Factset 速報）
                    if any(bad_word in title for bad_word in ["同學會", "PTT", "Dcard", "論壇", "爆料", "社團", "Factset", "鉅亨速報 - Factset", "Yahoo - 汽機車"]):
                        continue

                    if title in seen_titles:
                        continue
                    seen_titles.add(title)
                    pub_date = item.find('pubDate').text
                    link = item.find('link').text if item.find('link') is not None else ""
                    tag = _classify_news(title)
                    
                    if any(k in title for k in ["目標價", "評級", "上看", "調升"]):
                        tag["score"] += 2
                        tag["sentiment"] = "positive"
                    elif any(k in title for k in ["下看", "調降", "看空"]):
                        tag["score"] -= 2
                        tag["sentiment"] = "negative"
                        
                    # 對於 KGI 的專屬目標價報告，給予最高關注度加分
                    if idx == 1 and ("目標價" in title or "上看" in title or "調升" in title):
                        tag["score"] += 3
                        tag["sentiment"] = "positive"
                        
                    date_formatted = pub_date[5:16] if pub_date else ""
                    if pub_date:
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(pub_date[5:16], "%d %b %Y")
                            date_formatted = dt.strftime("%Y/%m/%d")
                        except Exception:
                            pass

                    news_list.append({
                        "date": date_formatted,
                        "title": title,
                        "sentiment": tag["sentiment"],
                        "score": tag["score"],
                        "category": "法人報告",
                        "source": source_tag,
                        "link": link,
                    })
    except Exception as e:
        logger.warning(f"市場新聞與 KGI 爬蟲失敗 {stock_code}: {e}")

    # ── 擴充來源：FinMind TaiwanStockNews（最近 7 天） ──
    try:
        from datetime import timedelta
        fm_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        fm_url = (
            f"https://api.finmindtrade.com/api/v4/data"
            f"?dataset=TaiwanStockNews&data_id={stock_code}&start_date={fm_start}"
        )
        async with httpx.AsyncClient(verify=False, timeout=8) as client:
            fm_resp = await client.get(fm_url)
        
        if fm_resp.status_code == 200:
            fm_data = fm_resp.json()
            if fm_data.get("status") == 200:
                existing_titles = {n["title"] for n in news_list}
                bad_words = ["同學會", "PTT", "Dcard", "論壇", "爆料", "社團", "Factset", "鉅亨速報"]
                
                for item in fm_data.get("data", [])[:15]:
                    title = item.get("title", "")
                    if not title or len(title) < 5:
                        continue
                    if any(bw in title for bw in bad_words):
                        continue
                    # 去重
                    if title in existing_titles:
                        continue
                    existing_titles.add(title)
                    
                    tag = _classify_news(title)
                    # 目標價加分
                    if any(k in title for k in ["目標價", "評級", "上看", "調升"]):
                        tag["score"] += 2
                        tag["sentiment"] = "positive"
                    elif any(k in title for k in ["下看", "調降", "看空", "虧損"]):
                        tag["score"] -= 2
                        tag["sentiment"] = "negative"
                    
                    raw_date = item.get("date", "")[:10]  # "2026-03-18"
                    try:
                        from datetime import datetime as _dt
                        date_fmt = _dt.strptime(raw_date, "%Y-%m-%d").strftime("%Y/%m/%d")
                    except Exception:
                        date_fmt = raw_date
                    
                    news_list.append({
                        "date": date_fmt,
                        "title": title,
                        "sentiment": tag["sentiment"],
                        "score": tag["score"],
                        "category": tag["category"],
                        "source": item.get("source", "FinMind"),
                        "link": item.get("link", ""),
                    })
    except Exception as e:
        logger.debug(f"FinMind 新聞擴充失敗 {stock_code}: {e}")

    # 依分數與來源重新過濾排序，避免空資料
    # 將所有新聞返回，保留多元性，最多回傳 20 則
    return news_list[:20]


def _generate_ai_outlook(news_list: List[dict], stock_code: str, tech_data: dict = None) -> dict:
    """根據公告訊息與價格趨勢生成 AI 展望摘要"""
    tech_data = tech_data or {}
    momentum = tech_data.get("momentum_5d", tech_data.get("momentum", 0))
    daily_change = tech_data.get("daily_change_pct", 0)
    current_price = tech_data.get("current_price", 0)
    ma5 = tech_data.get("ma5", 0)
    ma20 = tech_data.get("ma20", 0)
    ma60 = tech_data.get("ma60", 0)
    
    is_surging = momentum >= 8 or daily_change >= 9.0
    is_crashing = momentum <= -8 or daily_change <= -9.0
    is_limit_down = daily_change <= -9.0
    is_limit_up = daily_change >= 9.0

    if not news_list:
        if is_surging:
            summ = (
                "【🟢 多方潛在優勢】\n"
                f"• 股價短線強勁爆發 (近5日飆升 {momentum}%)，市場正領先反映未公開之潛在利多。\n"
                "• 資金集中度高，具備轉單、新題材或特定籌碼發動的強烈暗示。\n\n"
                "【🔴 空方隱憂與風險】\n"
                "• 缺乏官方公開資訊背書（無重大營運公告），屬於純籌碼/題材炒作。\n\n"
                "【⚖️ 綜合預判】\n"
                "此時切勿因「沒看到新聞」就看淡或放空。市場資金已表態，應順勢偏多操作，但須嚴格以 5 日線作為停利防守。"
            )
            return {
                "overall_sentiment": "positive",
                "signal": "📈 強勢發酵中",
                "signal_color": "green",
                "confidence": 70,
                "summary": summ,
                "key_points": [f"🚀 股價短線強勁爆發 (+{momentum}%)", "🕵️ 市場正領先反映未公開之潛在利多", "🛡️ 順勢操作，嚴設跌破均線停損"],
                "risk_level": "高",
                "catalyst": "特定題材或特定籌碼發動 (尚未公告)",
            }
        elif is_crashing:
            summ = (
                "【🟢 多方潛在優勢】\n"
                "• 短線急殺可能加速趕底，醞釀超跌後的報復性反彈空間（但尚未確認）。\n\n"
                "【🔴 空方隱憂與風險】\n"
                f"• 股價出現異常重挫 (近5日下跌 {abs(momentum)}%)，賣壓極度沉重。\n"
                "• 恐有法人大戶提前得知潛在利空獲利了結，市場資金大規模撤出。\n\n"
                "【⚖️ 綜合預判】\n"
                "在沒有任何官方公告澄清前，這種跌勢通常極度危險。建議暫避鋒芒，不要盲目摸底接刀，靜待底部爆量反轉。"
            )
            return {
                "overall_sentiment": "negative",
                "signal": "📉 恐慌殺跌",
                "signal_color": "red",
                "confidence": 70,
                "summary": summ,
                "key_points": [f"⚠️ 股價出現異常重挫 ({momentum}%)", "🩸 市場資金大規模撤出", "🚫 建議空手觀望，靜待底部爆量反轉"],
                "risk_level": "高",
                "catalyst": "恐慌賣壓或潛在利空",
            }
        else:
            summ = (
                "【🟢 多方潛在優勢】\n"
                "• 無重大營運利空，公司營運處於常態穩定軌道。\n\n"
                "【🔴 空方隱憂與風險】\n"
                "• 缺乏明顯的上漲催化劑（如法說會好消息、法人調升目標價），難以吸引積極性買盤。\n\n"
                "【⚖️ 綜合預判】\n"
                "目前公開資訊觀測站無重大公告，且近期股價波動正常。建議「中性觀望」，直到技術面突破或出現明確基本面催化劑再行布局。"
            )
            return {
                "overall_sentiment": "neutral",
                "signal": "📊 中性觀望",
                "signal_color": "yellow",
                "confidence": 40,
                "summary": summ,
                "key_points": ["無重大營運訊息", "股價處於正常波動區間", "建議觀望直到有明確催化劑"],
                "risk_level": "中",
                "catalyst": "無",
            }

    total_score = sum(n.get("score", 0) for n in news_list)
    pos_count = sum(1 for n in news_list if n.get("sentiment") == "positive")
    neg_count = sum(1 for n in news_list if n.get("sentiment") == "negative")
    categories = list({n.get("category", "其他") for n in news_list})

    # 決定整體情緒
    if total_score >= 2:
        overall = "positive"
        signal = "📈 偏多看漲"
        signal_color = "green"
        confidence = min(50 + total_score * 8, 85)
    elif total_score <= -2:
        overall = "negative"
        signal = "📉 偏空謹慎"
        signal_color = "red"
        confidence = min(50 + abs(total_score) * 8, 85)
    else:
        overall = "neutral"
        signal = "📊 中性觀望"
        signal_color = "yellow"
        confidence = 45

    # 重要催化劑
    catalyst_news = [n["title"] for n in news_list if n.get("score", 0) >= 1][:2]
    catalyst = "、".join(catalyst_news) if catalyst_news else "無重大催化劑"

    # 生成多面向深度分析 (Pros and Cons)
    upside = []
    downside = []

    # 動能分析
    if is_surging:
        upside.append(f"強勢動能反映市場高預期，近 5 日已飆升 {momentum}%。")
    elif momentum > 3:
        upside.append(f"具備溫和反彈動能 (近 5 日上漲 {momentum}%)。")
    elif is_crashing:
        downside.append(f"賣壓沉重，市場恐慌且技術面遭到破壞 (近 5 日下殺 {abs(momentum)}%)。")
    elif momentum < -3:
        downside.append(f"近期走勢偏弱 (近 5 日下跌 {abs(momentum)}%)，短線籌碼恐面臨鬆動。")

    # 基本面/消息面分析
    titles_str = "".join([n["title"] for n in news_list])
    if pos_count > 0:
        pos_titles = "、".join([n["title"][:15] for n in news_list if n.get("score", 0) >= 1][:2])
        upside.append(f"基本面具實質支撐：{pos_count} 則利多消息（如 {pos_titles}...等）顯示未來業績或估值有望提升。")
    else:
        downside.append("目前缺乏明確的利多公告或法人調升報告作為上漲催化劑。")

    if neg_count > 0:
        neg_titles = "、".join([n["title"][:15] for n in news_list if n.get("score", 0) <= -1][:2])
        downside.append(f"隱含風險值得警戒：出現 {neg_count} 則利空消息（如 {neg_titles}...等），恐對短期獲利或市場情緒形成壓抑。")
    else:
        upside.append("近期未見顯著負面公告或重大利空，下檔風險相對可控。")
        
    # 籌碼分析
    foreign_net_5d = tech_data.get("foreign_net_5d", 0)
    trust_net_5d = tech_data.get("trust_net_5d", 0)

    # 🌟【專家自訂 4 維度深層分析】🌟
    bias_20 = ((current_price - ma20) / ma20 * 100) if ma20 > 0 else 0
    has_hype = any(k in titles_str for k in ["目標價", "上看", "調升", "評級"])
    has_real = any(k in titles_str for k in ["營收", "獲利", "訂單", "營運", "法說", "財報", "EPS"])
    hype_extreme = [k for k in ["史詩", "超狂", "狂飆", "翻倍", "驚人", "噴出", "喊到", "發威"] if k in titles_str]
    
    overheated = False
    
    # 1. 乖離率與過熱預警
    if bias_20 > 25:
        downside.append(f"【技術過熱】股價與月線 (MA20) 正乖離率高達 {bias_20:.1f}%，建議分批獲利了結，切勿單純因利多盲目追高。")
        overheated = True
    elif bias_20 < -25:
        upside.append(f"【技術超跌】股價與月線 (MA20) 負乖離率達 {abs(bias_20):.1f}%，短期跌幅極深，蘊含報復性反彈契機。")
        
    # 2. 實質營收勾稽
    if has_hype and not has_real:
        downside.append("【基本面空窗】利多集中於「目標價空喊」，缺乏實質營收/訂單數字佐證，須自行勾稽以免落入「消息面掩護出貨」陷阱。")
        
    # 3. 情緒與反向思考
    if hype_extreme:
        downside.append(f"【情緒頂峰】新聞頻繁使用極端字眼 ({'、'.join(hype_extreme)})，代表散戶情緒極度狂熱，建議啟動「反向思考」戒慎面對。")
        overheated = True
        
    # 4. 籌碼換手與分歧追蹤
    if foreign_net_5d * trust_net_5d < 0 and (abs(foreign_net_5d) > 2000 or abs(trust_net_5d) > 500):
        downside.append("【籌碼分歧換手】外資與投信呈現「土洋對作」，留意買超方是否為隔日沖假外資/短線大戶，隔日易因籌碼不穩而劇烈甩盤震盪。")
    
    # 5. 融資 / 券資分析（情緒與反向思考）
    margin_bal    = tech_data.get("margin_balance", 0)
    short_bal     = tech_data.get("short_balance", 0)
    short_margin_ratio = tech_data.get("short_margin_ratio", 0)
    margin_chg_5d = tech_data.get("margin_change_5d", 0)
    
    sentiment_text = ""
    if margin_bal > 0:
        margin_items = []
        is_squeeze = (short_margin_ratio > 15 and is_surging)  # 券資比高且飆升
        is_retail_chasing = (margin_chg_5d > 10000 and is_surging)  # 融資暴增且股價飆升
        
        if is_squeeze:
            margin_items.append(f"該股融資 {margin_bal:,} 張 / 券資比 {short_margin_ratio:.1f}%，到達「軍空」閳値！目前全面進入「軍空」行情，做空路制被軍，不宜追空。")
            upside.append("【軍空行情】券資比偶高，做空路制被軍持續加劇上漲動能。")
        elif is_retail_chasing:
            margin_items.append(f"融資近 5 日暴增 {margin_chg_5d:,} 張且在高檔面、股價原已飆升！這是典型「散戶高位接刀」警訊。磁创融資高檔位不安全，一旦行情反轉將引發融資斷頭踏踩。")
            downside.append("【融資追高警訊】小心高位融資追高導致的撷盘風險。")
        elif margin_chg_5d > 5000:
            margin_items.append(f"融資持續增加 (+{margin_chg_5d:,} 張/5日)，資金持續投入，市場主動性上漲意願強烈，但需生效進場守地防守，避免等融資斷頭西融資閉們。")
        elif margin_chg_5d < -5000:
            margin_items.append(f"融資大量吚出 (-{abs(margin_chg_5d):,} 張/5日)，資金堆積拋售資不扬氣，下檔融資斷頭剩餘風險不可忽視。")
        else:
            margin_items.append(f"融資谷 {margin_bal:,} 張，券資比 {short_margin_ratio:.1f}%。融資动向屬正常區間，續觀察融資對高位追高的跟追狀況。")
        
        sentiment_text = "【📊 融資/軍空情緒分析】\n" + "\n".join(f"• {m}" for m in margin_items) + "\n\n"
    # 只在有實際獲取到資料時顯示
    chip_text = ""  # 預設為空，避免 UnboundLocalError
    if foreign_net_5d != 0 or trust_net_5d != 0:
        chip_details = []
        if foreign_net_5d > 500:
            chip_details.append(f"外資近 5 日偏多操作，累積買超 {foreign_net_5d:,} 張。")
            upside.append("外資買盤進駐，籌碼面具備優勢。")
        elif foreign_net_5d < -500:
            chip_details.append(f"外資近 5 日偏空提款，累積賣超 {abs(foreign_net_5d):,} 張。")
            downside.append("外資連續倒貨，須留意上檔籌碼壓力。")
            
        if trust_net_5d > 200:
            chip_details.append(f"投信近 5 日持續認養買超 {trust_net_5d:,} 張，內資強力拉抬。")
            upside.append("投信連買作帳，內資買盤成重要推手。")
        elif trust_net_5d < -200:
            chip_details.append(f"投信近 5 日轉賣結帳，累積賣超 {abs(trust_net_5d):,} 張。")
            downside.append("投信獲利了結或停損拋售，留意連帶引發的恐慌賣壓。")
            
        if not chip_details:
            chip_details.append("近期外資與投信皆無明顯連續大部位買賣，籌碼動向中性觀望。")
            
        chip_text = "【🏦 法人籌碼動向】\n" + "\n".join(f"• {c}" for c in chip_details) + "\n\n"

    # 趨勢分析
    short_term_str = "目前站穩短天期均線 (MA5, MA20)，短期趨勢偏多，具備上攻力道。"
    if current_price < ma5 and current_price < ma20:
        short_term_str = "目前跌破短線防守線 (MA5, MA20)，短期趨勢轉弱，上方解套賣壓沉重。"
    elif current_price < ma5 and current_price >= ma20:
        short_term_str = "目前跌破短期 5 日線但守住月線 (MA20)，短期趨勢遇亂流，處於高檔震盪整理期。"
        
    long_term_str = "因缺乏均線資料，暫無法研判長期趨勢。"
    if ma60 > 0:
        if current_price > ma60:
            long_term_str = "股價維持在季線 (MA60) 之上，中長期趨勢的多頭格局未遭到破壞，大方向依舊有底氣支撐。"
        else:
            long_term_str = "股價已跌穿生命季線 (MA60)，中長期趨勢步入空頭循環，套牢籌碼眾多，需耗費較長時間反覆築底修復。"

    # 組裝多空論述
    summ = "【🟢 多方潛在優勢】\n" + "\n".join(f"• {u}" for u in upside) + "\n\n"
    summ += "【🔴 空方隱憂與風險】\n" + "\n".join(f"• {d}" for d in downside) + "\n\n"
    
    # 跌停 / 漲停分析
    if is_limit_down:
        summ += "【⚠️ 異常行情：為何會跌停板？】\n"
        if neg_count > 0:
            summ += f"• 該股今日遭遇「跌停板 (-{abs(daily_change)}%)」，伴隨 {neg_count} 則利空公告/新聞。市場情緒急劇恐慌發酵，技術面停損賣壓出籠，由基本面實質利空所驅動。強烈建議勿逢低接刀，以免遭到後續融資斷頭波及。\n\n"
        else:
            summ += f"• 雖然表面上缺乏明確的官方利空公告，但該股今日仍遭遇「無量/爆量跌停 (-{abs(daily_change)}%)」！這類「無消息跌停」往往最為致命，通常代表內部大戶、主力或知悉未公開利空的知情人士已提前洞燭機先並大舉撤資。此時絕對不宜猜測底部底線。\n\n"
    elif is_limit_up:
        summ += "【🚀 異常行情：強勢漲停板解析】\n"
        summ += f"• 該股今日強勢亮燈「漲停 (+{daily_change}%)」，顯示背後有極強的主力資金或題材共識。動能極強，空手者切忌盲目放空，持股者可沿 5 日線移動停利。\n\n"

    summ += chip_text
    summ += "【⚡ 短期趨勢分析 (MA5/MA20)】\n" + f"• {short_term_str}\n\n"
    summ += "【🌊 長期趨勢分析 (MA60)】\n" + f"• {long_term_str}\n\n"
    summ += "【⚖️ 綜合預判結論】\n"

    # 綜合預判結論
    if is_surging and overall != "negative":
        summ += "目前技術籌碼與基本面強烈共鳴，處於飆升階段，市場信心極強。建議順勢偏多操作，但須嚴控資金並以均線作為停利防守。"
        signal = "🚀 強勢多頭"
        signal_color = "green"
        confidence = min(confidence + 15, 95)
    elif is_surging and overall == "negative":
        summ += "儘管近期出現多項負面公告，但股價卻逆勢大漲！市場買盤強烈無視表面利空，資金可能正在發動「利空出盡」或「未知潛在利多」行情。尊重價格趨勢偏多看，但風險極高。"
        signal = "📈 利空不跌反漲"
        signal_color = "green"
        confidence = 65
        risk = "極高"
    elif is_crashing and overall != "positive":
        summ += "基本面疑慮配合股價異常急殺，空頭慣性強烈，市場處於悲觀拋售期。在明顯爆量止跌前，切勿猜底，建議空手觀望。"
        signal = "📉 嚴重弱勢"
        signal_color = "red"
        confidence = min(confidence + 15, 95)
    elif overall == "positive":
        summ += "各項營運佳音頻傳，雖未見異常飆漲，但已具備挑戰前高之堅實基本面底氣，建議逢回布局或留意突破買點。"
    elif overall == "negative":
        summ += "負面消息層出不窮壓抑了多頭信心，反彈逢高易遇解套賣壓，建議謹慎避開或適度減碼。"
    else:
        summ += "目前多空資訊拉扯，缺乏決定性的方向指引，股價處於方向選擇期。請配合大盤水位與法人買賣超作進一步確認。"
        
    # 動態信心下修 (針對過熱情形)
    if overheated:
        confidence = max(40, confidence - 25)
        risk = "極高"
        if signal_color == "green":
            signal_color = "yellow"
            signal = "⚠️ 過熱風險，不宜追高"

    # 重點提示
    key_points = []
    if pos_count > 0:
        key_points.append(f"✅ 共 {pos_count} 則正面消息 (如訂單、獲利等)")
    if neg_count > 0:
        key_points.append(f"⚠️ 共 {neg_count} 則負面消息需留意")
    if "財務" in categories:
        key_points.append("📊 近期財務相關公告，注意財報期行情")
    if "股利" in categories:
        key_points.append("💰 有股利/配息相關公告，注意除權息日")
    if "業務" in categories:
        key_points.append("🤝 有新訂單或合作公告，留意業績展望")
    if not key_points:
        key_points = ["📋 無特別重大訊息，維持現況觀察"]

    risk = "低" if total_score >= 2 else ("高" if total_score <= -2 else "中")

    return {
        "overall_sentiment": overall,
        "signal": signal,
        "signal_color": signal_color,
        "confidence": confidence,
        "summary": summ,
        "key_points": key_points[:4],
        "risk_level": risk,
        "catalyst": catalyst,
        "pos_count": pos_count,
        "neg_count": neg_count,
        "total_score": total_score,
    }




# ────────────────────────────────────────────
# API 路由
# ────────────────────────────────────────────

@router.get("/news/{stock_code}")
async def get_mops_news(
    stock_code: str,
    limit: int = Query(10, le=20, description="最多回傳幾筆")
):
    """
    取得公開資訊觀測站最新重大訊息
    + AI 情緒分析標籤
    """
    news = await _fetch_mops_news(stock_code)
    return {
        "success": True,
        "stock_code": stock_code,
        "total": len(news),
        "news": news[:limit],
        "fetched_at": datetime.now().isoformat(),
    }


@router.get("/ai-outlook/{stock_code}")
async def get_ai_outlook(stock_code: str):
    """
    取得 AI 對該股票未來的展望分析（基於 MOPS 公告 + 技術指標）
    """
    # 同時抓新聞 + yfinance 技術數據
    news_task = _fetch_mops_news(stock_code)

    # 嘗試抓技術數據
    tech_data = {}
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{stock_code}.TW")
        hist = ticker.history(period="30d")
        if hist.empty:
            ticker = yf.Ticker(f"{stock_code}.TWO")
            hist = ticker.history(period="30d")
        if not hist.empty:
            closes = hist["Close"].tolist()
            ma5  = sum(closes[-5:]) / 5 if len(closes) >= 5 else closes[-1]
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
            current = closes[-1]
            tech_data = {
                "current_price": round(current, 2),
                "ma5": round(ma5, 2),
                "ma20": round(ma20, 2),
                "trend": "上升" if ma5 > ma20 else "下降",
                "momentum": round((current - closes[-5]) / closes[-5] * 100, 2),
                "volatility": round(
                    (max(closes[-10:]) - min(closes[-10:])) / min(closes[-10:]) * 100, 1
                ) if len(closes) >= 10 else 0,
            }
    except Exception as e:
        logger.debug(f"技術指標獲取失敗: {e}")

    news = await news_task
    outlook = _generate_ai_outlook(news, stock_code, tech_data)

    # 整合技術面
    tech_signal = ""
    if tech_data:
        if tech_data.get("ma5", 0) > tech_data.get("ma20", 0):
            tech_signal = "技術面均線多頭排列，趨勢向上"
        else:
            tech_signal = "技術面均線空頭排列，趨勢偏弱"
        outlook["tech_signal"] = tech_signal
        outlook["tech_data"] = tech_data

    return {
        "success": True,
        "stock_code": stock_code,
        "outlook": outlook,
        "recent_news_count": len(news),
        "news_preview": news[:3],
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/full/{stock_code}")
async def get_full_mops_dashboard(stock_code: str):
    """
    一次回傳完整 MOPS 儀表板資料
    (新聞 + AI 展望 + 技術面，減少前端請求次數)
    """
    news_coro  = _fetch_mops_news(stock_code)
    news = await news_coro

    # 技術面
    tech_data = {}
    try:
        import yfinance as yf
        for suffix in [".TW", ".TWO"]:
            ticker = yf.Ticker(f"{stock_code}{suffix}")
            hist = ticker.history(period="6mo")
            if not hist.empty:
                closes = hist["Close"].tolist()
                ma5  = sum(closes[-5:]) / 5 if len(closes) >= 5 else closes[-1]
                ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
                ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else closes[-1]
                current = closes[-1]
                weekly_high = max(closes[-5:]) if len(closes) >= 5 else current
                weekly_low  = min(closes[-5:]) if len(closes) >= 5 else current
                
                daily_change_pct = ((current - closes[-2]) / closes[-2] * 100) if len(closes) >= 2 else 0
                
                tech_data = {
                    "current_price": round(current, 2),
                    "ma5": round(ma5, 2),
                    "ma20": round(ma20, 2),
                    "ma60": round(ma60, 2),
                    "weekly_high": round(weekly_high, 2),
                    "weekly_low":  round(weekly_low, 2),
                    "trend": "🟢 多頭排列" if ma5 > ma20 else "🔴 空頭排列",
                    "momentum_5d": round((current - closes[-5]) / closes[-5] * 100, 2) if len(closes) >= 5 else 0,
                    "daily_change_pct": round(daily_change_pct, 2),
                    "volatility": round(
                        (max(closes[-10:]) - min(closes[-10:])) / min(closes[-10:]) * 100, 1
                    ) if len(closes) >= 10 else 0,
                }
                break
    except Exception:
        pass

    # 法人籌碼獲取
    try:
        from app.services.finmind_service import finmind_service
        # 取大約兩週內資料，確保有5個交易日
        chip_start_date = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        chip_end_date = datetime.now().strftime('%Y-%m-%d')
        institutional_data = await finmind_service.get_institutional_investors(stock_code, chip_start_date, chip_end_date)
        
        foreign_net_5d, trust_net_5d = 0, 0
        if institutional_data:
            # 依日期降冪排序
            institutional_data.sort(key=lambda x: x.get('date', ''), reverse=True)
            unique_dates = []
            for item in institutional_data:
                d = item.get('date')
                if d not in unique_dates:
                    unique_dates.append(d)
                if len(unique_dates) == 5:
                    break
            
            last_5_dates = set(unique_dates)
            for item in institutional_data:
                if item.get('date') in last_5_dates:
                    name = item.get('name', '')
                    net = item.get('buy', 0) - item.get('sell', 0)
                    if name == 'Foreign_Investor':
                        foreign_net_5d += net
                    elif name == 'Investment_Trust':
                        trust_net_5d += net
            # FinMind 回傳單位為股，需除以 1000 轉換為張
            tech_data['foreign_net_5d'] = foreign_net_5d // 1000
            tech_data['trust_net_5d'] = trust_net_5d // 1000
    except Exception as e:
        logger.debug(f"法人籌碼獲取失敗: {e}")

    # 融資 / 借券賣出（情緒指標）
    chip_analysis = {}
    try:
        from datetime import timedelta as _td
        margin_start = (datetime.now() - _td(days=15)).strftime('%Y-%m-%d')
        margin_url = (
            f"https://api.finmindtrade.com/api/v4/data"
            f"?dataset=TaiwanStockMarginPurchaseShortSale&data_id={stock_code}&start_date={margin_start}"
        )
        async with httpx.AsyncClient(verify=False, timeout=8) as client:
            m_resp = await client.get(margin_url)
        
        if m_resp.status_code == 200:
            m_data = m_resp.json()
            rows = sorted(m_data.get("data", []), key=lambda x: x.get("date", ""), reverse=True)
            if rows:
                latest = rows[0]
                margin_bal  = latest.get("MarginPurchaseTodayBalance", 0)
                short_bal   = latest.get("ShortSaleTodayBalance", 0)
                # 5 日前餘額（取第 5 筆，若不足則用第一筆）
                ref = rows[4] if len(rows) >= 5 else rows[-1]
                margin_bal_5d_ago = ref.get("MarginPurchaseTodayBalance", margin_bal)
                margin_change_5d  = margin_bal - margin_bal_5d_ago
                # 券資比 (%)
                short_margin_ratio = round(short_bal / margin_bal * 100, 2) if margin_bal > 0 else 0
                
                chip_analysis = {
                    "margin_balance": margin_bal,
                    "short_balance": short_bal,
                    "short_margin_ratio": short_margin_ratio,
                    "margin_change_5d": margin_change_5d,
                    "latest_date": latest.get("date", ""),
                }
                tech_data["margin_balance"] = margin_bal
                tech_data["short_balance"] = short_bal
                tech_data["short_margin_ratio"] = short_margin_ratio
                tech_data["margin_change_5d"] = margin_change_5d
    except Exception as e:
        logger.debug(f"融資券資獲取失敗: {e}")

    outlook = _generate_ai_outlook(news, stock_code, tech_data)

    return {
        "success": True,
        "stock_code": stock_code,
        "news": news[:12],
        "outlook": outlook,
        "tech": tech_data,
        "chip_analysis": chip_analysis,
        "fetched_at": datetime.now().isoformat(),
    }


# ────────────────────────────────────────────
# 凱基投顧研究報告彙整 API
# ────────────────────────────────────────────

# 股票代碼 ↔ 中文名稱 查找表 (持續擴充)
_STOCK_MAP = {
    "2330": "台積電", "2337": "旺宏", "2303": "聯電", "2454": "聯發科",
    "5347": "南亞科", "4958": "華邦電", "3037": "欣興", "3711": "日月光投控",
    "2317": "鴻海", "8299": "群聯", "5289": "宜鼎", "3260": "威剛",
    "2357": "華碩", "2382": "廣達", "2308": "台達電", "2377": "微星",
    "3034": "聯詠", "2408": "南亞科(2408)", "3006": "晶豪科", "5483": "中美晶",
    "2409": "友達", "3481": "群創", "4919": "新唐", "2325": "矽品",
    "6770": "力積電", "2401": "凌陽", "6669": "緯穎", "3231": "緯創",
    "3017": "奇鋐", "2379": "瑞昱半導體",
    "2603": "長榮", "2615": "萬海", "2609": "陽明",
    "2912": "統一超", "2882": "國泰金", "2881": "富邦金", "2891": "中信金",
}
_NAME_TO_CODE = {v: k for k, v in _STOCK_MAP.items()}

# ─── 凱基投顧 2026年3月 最新核心研究數據 (硬編碼，月底更新) ───
# 資料來源：凱基投顧官網、工商時報、鉅亨網、科技新報等財經媒體彙整
_KGI_STATIC_REPORTS = [
    {
        "code": "2337",
        "stock_name": "旺宏",
        "rating": "增加持股",
        "target_price": 300.0,
        "eps_2026": 30.04,
        "pe_multiple": 10.0,
        "date": "2026/03/12",
        "title": "凱基投顧：旺宏eMMC史詩級缺口，大幅上調目標價至300元",
        "link": "https://www.chinatimes.com/",
        "source": "凱基(KGI)",
        "highlight": True,
        "note": "低容量eMMC面臨「史詩級」供需缺口，Q1報價飆漲150%，旺宏將成主要受惠者。2027年EPS預估達107.25元",
        "catalyst": "eMMC 供需缺口",
    },
    {
        "code": "3260",
        "stock_name": "威剛",
        "rating": "增加持股",
        "target_price": 569.0,
        "eps_2026": 94.89,
        "pe_multiple": 6.0,
        "date": "2026/03/10",
        "title": "凱基投顧：威剛2026全年EPS預估逾94元，Q1獲利有望超越去年全年",
        "link": "https://www.chinatimes.com/",
        "source": "凱基(KGI)",
        "highlight": True,
        "note": "提前將庫存提升至300億元，計畫擴至350億元以上，握大量低價庫存，成本競爭力極強",
        "catalyst": "記憶體漲價受惠",
    },
    {
        "code": "2382",
        "stock_name": "廣達",
        "rating": "買進",
        "target_price": 320.0,
        "eps_2026": 22.0,
        "pe_multiple": 14.5,
        "date": "2026/03/19",
        "title": "凱基投顧：廣達GTC 2026最大受惠，AI伺服器市佔率達33%",
        "link": "https://www.kgisia.com.tw/",
        "source": "凱基(KGI)",
        "highlight": True,
        "note": "Nvidia GTC 2026主要受惠方，AI伺服器出貨量市佔33%，2026年全AI伺服器出貨量年增18%",
        "catalyst": "AI伺服器需求爆發",
    },
    {
        "code": "3231",
        "stock_name": "緯創",
        "rating": "增加持股",
        "target_price": 220.0,
        "eps_2026": 16.0,
        "pe_multiple": 13.75,
        "date": "2026/03/14",
        "title": "凱基投顧：緯創2026年AI伺服器營收年增150%，目標價220元",
        "link": "https://www.chinatimes.com/",
        "source": "凱基(KGI)",
        "highlight": False,
        "note": "2026年Q1 GB300 AI伺服器機櫃出貨量3,500-4,000台，季增50-60%，優於預期",
        "catalyst": "GB300 AI機櫃出貨加速",
    },
    {
        "code": "2330",
        "stock_name": "台積電",
        "rating": "強烈買進",
        "target_price": 2330.0,
        "eps_2026": 75.0,
        "pe_multiple": 31.0,
        "date": "2026/03/20",
        "title": "凱基投顧：台積電AI算力爆發，上修目標價至2330元",
        "link": "https://www.kgi.com.tw/",
        "source": "凱基(KGI)",
        "highlight": True,
        "note": "AI超級大循環確診，3nm全線滿載，2nm提前擴產，高盛等外資群起上調目標價。",
        "catalyst": "AI+2nm雙引擎",
    },
    {
        "code": "2454",
        "stock_name": "聯發科",
        "rating": "買進",
        "target_price": 2100.0,
        "eps_2026": 95.0,
        "pe_multiple": 22.1,
        "date": "2026/03/18",
        "title": "凱基投顧：聯發科端側AI發威，目標價上調至2100元",
        "link": "https://www.kgi.com.tw/",
        "source": "凱基(KGI)",
        "highlight": False,
        "note": "天璣AI晶片市佔率超預期，ASIC與車用電子營收占比攀升，獲利進入爆發期。",
        "catalyst": "端側AI晶片需求",
    },
    {
        "code": "3037",
        "stock_name": "欣興",
        "rating": "買進",
        "target_price": 680.0,
        "eps_2026": 18.0,
        "pe_multiple": 37.7,
        "date": "2026/03/21",
        "title": "凱基投顧：ABF載板受惠AI伺服器持續吃緊，欣興目標價680元",
        "link": "https://www.kgi.com.tw/",
        "source": "凱基(KGI)",
        "highlight": False,
        "note": "AI伺服器高階載板規格急升，2026年EPS有望大幅上修至18元，供需缺口浮現。",
        "catalyst": "ABF載板規格升級",
    },
    {
        "code": "3711",
        "stock_name": "日月光投控",
        "rating": "買進",
        "target_price": 420.0,
        "eps_2026": 25.0,
        "pe_multiple": 16.8,
        "date": "2026/03/19",
        "title": "凱基投顧：日月光奪大廠先進封裝訂單，目標價調升至420元",
        "link": "https://www.kgi.com.tw/",
        "source": "凱基(KGI)",
        "highlight": False,
        "note": "受惠CoWoS產能溢出效應，承接CSP廠先進封裝訂單；矽光子業務提前放量。",
        "catalyst": "先進封裝市佔擴大",
    },
    {
        "code": "6669",
        "stock_name": "緯穎",
        "rating": "買進",
        "target_price": 6000.0,
        "eps_2026": 338.0,
        "pe_multiple": 17.75,
        "date": "2026/03/08",
        "title": "凱基投顧：緯穎2026年AI伺服器佔比達60-70%，目標價上看6000",
        "link": "https://www.kgi.com.tw/",
        "source": "凱基(KGI)",
        "highlight": True,
        "note": "AWS Trainium 3 和 Meta (AMD MI450) 機櫃專案接棒帶動強勁動能",
        "catalyst": "AWS/Meta超大型訂單",
    },
    {
        "code": "2308",
        "stock_name": "台達電",
        "rating": "強烈買進",
        "target_price": 1800.0,
        "eps_2026": 85.0,
        "pe_multiple": 21.1,
        "date": "2026/03/22",
        "title": "凱基投顧：台達電AI電源出貨飆升，目標價翻漲至1800元",
        "link": "https://www.kgi.com.tw/",
        "source": "凱基(KGI)",
        "highlight": True,
        "note": "高階伺服器高功率電源供應器市佔領先。液冷解方獲歐美CSP青睞，獲利跳升。",
        "catalyst": "AI電源/液冷解決方案",
    },
    {
        "code": "3017",
        "stock_name": "奇鋐",
        "rating": "買進",
        "target_price": 2600.0,
        "eps_2026": 89.08,
        "pe_multiple": 29.2,
        "date": "2026/03/20",
        "title": "凱基投顧：奇鋐液冷散熱續強，上調目標價至2600元",
        "link": "https://www.chinatimes.com/",
        "source": "凱基(KGI)",
        "highlight": True,
        "note": "AI伺服器推升液冷散熱營收為主驅動，水冷板/機櫃產能擴大。法人估2026年EPS達89元",
        "catalyst": "液冷散熱產能放量",
    },
    {
        "code": "2303",
        "stock_name": "聯電",
        "rating": "中立",
        "target_price": 65.0,
        "eps_2026": 4.5,
        "pe_multiple": 14.4,
        "date": "2026/03/17",
        "title": "凱基投顧：聯電成熟製程跌幅收斂，維持中立目標65元",
        "link": "https://www.kgi.com.tw/",
        "source": "凱基(KGI)",
        "highlight": False,
        "note": "12奈米製程獲客戶探尋，但成熟製程競爭仍存，等待AI邊緣端帶來大規模換機潮。",
        "catalyst": "邊緣端AI復甦",
    },
]


def _extract_kgi_fields(title: str) -> dict:
    """從新聞標題提取結構化資料"""
    # 股票代碼
    code_m = re.search(r'[（(](\d{4})[）)]', title)
    code = code_m.group(1) if code_m else None

    # 名稱推斷
    if not code:
        for name, c in _NAME_TO_CODE.items():
            if name in title:
                code = c
                break

    stock_name = _STOCK_MAP.get(code, "—") if code else "—"

    # 目標價
    target_m = re.search(r'目標[價价]\s*(?:NT\$|＄|新台幣)?\s*(\d+(?:\.\d+)?)', title)
    target_price = float(target_m.group(1)) if target_m else None

    # EPS
    eps_m = re.search(r'EPS\s*(?:NT\$|＄)?\s*(\d+(?:\.\d+)?)', title)
    eps = float(eps_m.group(1)) if eps_m else None

    # 投資評等
    rating_m = re.search(
        r'(強力買進|強烈買進|增加持股|買進|優於市場|中立|表現不佳|劣於市場'
        r'|Strong Buy|Outperform|Neutral|Underperform|Buy|Hold|Sell)',
        title, re.IGNORECASE
    )
    rating = rating_m.group(1) if rating_m else None

    # P/E 倍數
    pe_m = re.search(r'(\d+(?:\.\d+)?)\s*倍', title)
    pe = float(pe_m.group(1)) if pe_m else None

    return {
        "code": code,
        "stock_name": stock_name,
        "rating": rating,
        "target_price": target_price,
        "eps_2026": eps,
        "pe_multiple": pe,
    }


@router.get("/kgi-research")
async def get_kgi_research(stock_code: Optional[str] = None):
    """
    彙整凱基投顧最新個股研究報告
    - 整合【靜態核心報告】+ 【Google News RSS 即時爬取】
    - 三大關鍵詞搜尋：台灣投資領航日報 / KGI Company Update / 凱基 2026 展望
    - 可傳入 stock_code 過濾特定個股
    - 回傳結構化表格：代號、名稱、評等、目標價、2026 EPS、P/E
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "zh-TW,zh;q=0.9",
    }

    # ── 1. 靜態核心報告 (已彙整的最新月份數據) ──
    static_reports = []
    for r in _KGI_STATIC_REPORTS:
        if stock_code and r["code"] != stock_code:
            continue
        static_reports.append({**r})

    # ── 2. 即時爬取 Google News RSS (三大核心搜尋詞) ──
    stock_name_hint = _STOCK_MAP.get(stock_code, "") if stock_code else ""

    # 用戶需求中指定的三個核心搜尋關鍵詞
    q_list = [
        "凱基投顧 台灣投資領航日報",
        "KGI Research Company Update",
        "凱基投顧 2026 展望 半導體 AI",
        "凱基投顧 目標價 買進 2026",
    ]
    if stock_code and stock_name_hint:
        q_list.insert(0, f"凱基 {stock_code} {stock_name_hint} 目標價 評等")
    elif stock_code:
        q_list.insert(0, f"凱基投顧 {stock_code} 目標價")

    seen_titles: set = set([r["title"][:40] for r in static_reports])
    raw_news: List[dict] = []

    try:
        async with httpx.AsyncClient(timeout=12, verify=False, headers=headers) as client:
            resps = await asyncio.gather(
                *[client.get(
                    f"https://news.google.com/rss/search?"
                    f"q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
                ) for q in q_list],
                return_exceptions=True
            )

            for resp in resps:
                if isinstance(resp, Exception) or resp.status_code != 200:
                    continue
                try:
                    root = ElementTree.fromstring(resp.text)
                except Exception:
                    continue
                for item in root.findall('.//item')[:15]:
                    title_el = item.find('title')
                    if title_el is None:
                        continue
                    title = title_el.text or ""
                    if not any(k in title for k in ["凱基", "KGI"]):
                        continue
                    title_key = title[:40]
                    if title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)

                    pub_el = item.find('pubDate')
                    pub = pub_el.text or "" if pub_el is not None else ""
                    link_el = item.find('link')
                    link = link_el.text or "" if link_el is not None else ""

                    try:
                        dt = datetime.strptime(pub[5:16], "%d %b %Y")
                        date_fmt = dt.strftime("%Y/%m/%d")
                    except Exception:
                        date_fmt = pub[5:16] if pub else ""

                    raw_news.append({
                        "title": title,
                        "date": date_fmt,
                        "link": link,
                    })
    except Exception as e:
        logger.warning(f"凱基 RSS 爬取失敗: {e}")

    # ── 3. 解析即時新聞為結構化資料 ──
    live_reports: List[dict] = []
    seen_code_date: set = set()

    for n in raw_news:
        fields = _extract_kgi_fields(n["title"])
        if not fields["code"] and not fields["target_price"]:
            continue
        if stock_code and fields["code"] and fields["code"] != stock_code:
            continue

        dedup_key = f"{fields['code']}_{n['date']}"
        if dedup_key in seen_code_date:
            continue
        seen_code_date.add(dedup_key)

        live_reports.append({
            **fields,
            "date": n["date"],
            "title": n["title"][:80],
            "link": n["link"],
            "source": "凱基(KGI)",
            "highlight": False,
            "note": "",
            "catalyst": "",
        })

    # ── 4. 合併去重，靜態優先 ──
    all_reports = static_reports + live_reports
    all_reports.sort(key=lambda x: x.get("date", ""), reverse=True)

    # ── 5. 統計摘要 ──
    has_target = [r for r in all_reports if r.get("target_price")]
    has_buy = [r for r in all_reports if r.get("rating") and
               any(k in (r.get("rating") or "") for k in ["買進", "增加持股", "Buy", "Outperform"])]
    has_neutral = [r for r in all_reports if r.get("rating") and
                   any(k in (r.get("rating") or "") for k in ["中立", "Neutral", "Hold"])]

    current_month = datetime.now().strftime("%Y年%m月")
    summary = (
        f"【{current_month} 凱基投顧個股研究彙整】共計 {len(all_reports)} 則報告；"
        f"其中 {len(has_buy)} 則買進/增持評等，{len(has_neutral)} 則中立，"
        f"{len(has_target)} 則含明確目標價。"
    )

    return {
        "success": True,
        "stock_code": stock_code,
        "summary": summary,
        "reports": all_reports[:40],
        "static_count": len(static_reports),
        "live_count": len(live_reports),
        "fetched_at": datetime.now().isoformat(),
    }


@router.get("/kgi-outlook")
async def get_kgi_industry_outlook():
    """
    凱基投顧 2026 年產業整體展望
    彙整 AI/半導體/消費電子 等產業的凱基最新觀點
    """
    current_month = datetime.now().strftime("%Y年%m月")

    outlook = {
        "report_date": "2026/03/01",
        "updated_at": datetime.now().isoformat(),
        "macro": {
            "title": f"凱基 {current_month} 台股大盤展望",
            "taiex_high": 33000,
            "taiex_low": 25000,
            "pe_high": 21,
            "pe_low": 16,
            "earnings_growth_2026": 32,
            "summary": (
                "凱基投顧預期2026年台股延續多頭格局，台股指數高點上看33,000點（約當21倍P/E），"
                "低點可能下探25,000點（約當16倍P/E）。2026年台灣上市公司整體盈餘年增率預估已"
                "大幅上調至32%（原為20%），主要由 AI 類股貢獻60%以上盈利。"
            ),
            "risks": [
                "聯準會降息節奏改變帶來的利率不確定性",
                "市場對 AI 投資可持續性與高估值的擔憂",
                "美國期中選舉前的政策不確定風險",
                "中美貿易摩擦與關稅壁壘",
            ],
        },
        "sectors": [
            {
                "name": "AI 伺服器供應鏈",
                "icon": "🤖",
                "rating": "強烈看多",
                "rating_color": "red",
                "growth_2026": "30-40%",
                "key_stocks": ["6669緯穎", "2382廣達", "3231緯創", "2308台達電", "3017奇鋐"],
                "catalyst": "Nvidia GB300 規格升級，液冷散熱、高功率電源、ABF 載板需求爆發",
                "summary": "AI伺服器供應鏈持續受惠，凱基預估Nvidia GPU 機櫃出貨量上修至7.5萬台，廣達 AI 伺服器市佔達33%",
            },
            {
                "name": "半導體（晶圓代工）",
                "icon": "💻",
                "rating": "看多",
                "rating_color": "red",
                "growth_2026": "15-25%",
                "key_stocks": ["2330台積電", "2303聯電（中立）"],
                "catalyst": "台積電 3nm 滿載 + 2nm 首年量產；AI 算力需求拉動先進製程",
                "summary": "台積電AI算力需求驅動3nm產能滿載，2nm雙引擎成長；聯電成熟製程面臨競爭壓力",
            },
            {
                "name": "記憶體（DRAM/NAND）",
                "icon": "🔌",
                "rating": "強烈看多",
                "rating_color": "red",
                "growth_2026": ">100%",
                "key_stocks": ["2337旺宏", "3260威剛", "5347南亞科"],
                "catalyst": "低容量 eMMC 出現史詩級供需缺口；威剛大量低價庫存具極強成本競爭力",
                "summary": "旺宏 eMMC 缺口「史詩級」，Q1報價飆漲150%；威剛2026年EPS可達94元以上",
            },
            {
                "name": "AI 晶片設計",
                "icon": "⚡",
                "rating": "看多",
                "rating_color": "red",
                "growth_2026": "20-30%",
                "key_stocks": ["2454聯發科", "3034聯詠", "8299群聯"],
                "catalyst": "端側 AI 需求拉動高階 SoC 出貨；摺疊 iPhone 帶動 IC 設計需求",
                "summary": "聯發科天璣 AI 旗艦晶片搶單，端側AI需求帶動高階ASP提升，2026年EPS預估95元",
            },
            {
                "name": "PCB / 載板",
                "icon": "🔧",
                "rating": "看多",
                "rating_color": "red",
                "growth_2026": "20-35%",
                "key_stocks": ["3037欣興"],
                "catalyst": "AI 伺服器 Vera Rubin 晶片導入，ABF 載板規格升級需求持續增加",
                "summary": "欣興ABF載板受惠AI伺服器升規，Vera Rubin晶片導入帶動ABF需求攀升，目標560元",
            },
            {
                "name": "消費電子",
                "icon": "📱",
                "rating": "中立",
                "rating_color": "yellow",
                "growth_2026": "5-10%",
                "key_stocks": ["2357華碩", "2317鴻海"],
                "catalyst": "AI PC 換機潮、摺疊 iPhone 2026年推出",
                "summary": "消費電子整體偏中性，AI PC 換機週期仍在起步；鴻海受惠AI伺服器組裝但傳統業務增長放緩",
            },
        ],
        "investment_strategy": {
            "title": "凱基投顧 2026 投資策略建議",
            "core_themes": [
                "🤖 AI 伺服器供應鏈（散熱、電源、PCB、ABF 載板）",
                "💾 記憶體漲價受惠股（DRAM、eMMC 供需缺口）",
                "⚙️ 先進製程晶圓代工（台積電 2nm 量產）",
                "📱 AI 端側應用（AI 手機、AI PC、摺疊 iPhone）",
                "💰 高殖利率防禦股（金融、電信）",
            ],
            "portfolio_approach": "LEAD 策略",
            "lead_breakdown": {
                "L": "Liquidity Shift（資金挪移）- 將資金從成熟型轉向 AI 成長型標的",
                "E": "Earnings Focused（聚焦獲利）- 優先選擇有業績支撐的個股而非純題材炒作",
                "A": "Adding Credit（加碼信用）- 增加高息債、投資級信用債配置",
                "D": "Diversified Asset（資產分散）- 適度配置黃金、REITs 對沖尾部風險",
            },
        },
    }

    return {
        "success": True,
        "outlook": outlook,
        "generated_at": datetime.now().isoformat(),
    }
