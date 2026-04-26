"""
市場聯合決策服務 v1.0
Market Combined Decision Service

功能：
1. 串接證交所 OpenAPI 獲取大盤即時數據
2. 串接 yfinance 獲取美股、日股、匯率等外部預警數據
3. 實現大盤 + 個股的聯合決策矩陣
4. 提供盤前、盤中、尾盤三階段預警系統
"""

import asyncio
import logging
import httpx
import yfinance as yf
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional
from app.services.market_condition_filter import market_filter

logger = logging.getLogger(__name__)

class MarketDecisionService:
    """市場聯合決策服務"""
    
    # 證交所 OpenAPI 端點
    INDEX_API = "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX"
    INSTITUTIONAL_API = "https://openapi.twse.com.tw/v1/fund/BFI82U"
    ADVDEC_API = "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX" # 上漲下跌家數也在 MI_INDEX 中
    
    def __init__(self):
        self.market_cache = {}
        self.cache_time = None
        self.cache_duration = 60 # 1 分鐘快取
        
    async def _fetch_openapi(self, url: str) -> Optional[List[Dict]]:
        """呼叫證交所 OpenAPI"""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"OpenAPI 請求失敗 {url}: {e}")
        return None

    async def get_market_data(self) -> Dict[str, Any]:
        """獲取大盤核心數據 (優先使用 MIS 實時 API)"""
        now = datetime.now()
        if self.cache_time and (now - self.cache_time).total_seconds() < self.cache_duration:
            return self.market_cache

        market_info = {
            "index": 0,
            "change": 0,
            "change_pct": 0,
            "volume": 0,
            "foreign_net": 0,
            "trust_net": 0,
            "dealer_net": 0,
            "up_count": 0,
            "down_count": 0,
            "unchanged_count": 0,
            "adv_dec_ratio": 1.0,
            "timestamp": now.isoformat()
        }

        # 1. 獲取核心大盤狀態 (使用 market_filter，它已經處理了 MIS API 和 yfinance 備援)
        try:
            m_cond = market_filter.get_market_condition()
            if m_cond and m_cond.get("index_value"):
                market_info["index"] = m_cond["index_value"]
                market_info["change_pct"] = m_cond["change_pct"]
                # 推算漲跌點數
                market_info["change"] = round(market_info["index"] * (market_info["change_pct"] / 100), 2)
                logger.info(f"✅ [MarketDecision] 從 Filter 獲取大盤: {market_info['index']} ({market_info['change_pct']:+.2f}%)")
        except Exception as e:
            logger.warning(f"從 Filter 獲取大盤數據失敗: {e}")

        # 2. 獲取更多指數 (MIS API) - 櫃買指標
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # TSE 加權 (t00.tw) & OTC 櫃買 (o00.tw)
                mis_url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw|otc_o00.tw"
                res = await client.get(mis_url)
                if res.status_code == 200:
                    data = res.json()
                    for info in data.get("msgArray", []):
                        current = float(info.get("z", info.get("o", "0")))
                        yesterday = float(info.get("y", "0"))
                        if current > 0 and yesterday > 0:
                            change = round(current - yesterday, 2)
                            pct = round((change / yesterday) * 100, 2)
                            vol = int(info.get("v", "0")) # 指數的 volume 通常是成交金額或特化指標，這裡暫採 v
                            
                            if info.get("c") == "t00": # TSE
                                market_info["index"] = round(current, 2)
                                market_info["change"] = change
                                market_info["change_pct"] = pct
                                market_info["volume"] = vol
                            elif info.get("c") == "o00": # OTC
                                market_info["ota_index"] = round(current, 2)
                                market_info["ota_change"] = change
                                market_info["ota_change_pct"] = pct
                                logger.info(f"✅ 從 MIS 獲取即時櫃買: {current} ({pct:+.2f}%)")
        except Exception as e:
            logger.warning(f"MIS API (TSE+OTC) 獲取失敗: {e}")



        # 3. 獲取三大法人數據 (使用 twse_crawler，比 OpenAPI 穩定)
        try:
            from app.services.twse_crawler import twse_crawler
            inst_res = await twse_crawler.get_institutional_trading()
            if inst_res and inst_res.get("status") == "success":
                for item in inst_res.get("data", []):
                    name = item.get("name", "")
                    diff_str = str(item.get("diff", "0")).replace(",", "")
                    if diff_str:
                        try:
                            diff = float(diff_str) / 100000000  # 億
                            if "外資及陸資" in name:
                                market_info["foreign_net"] = round(diff, 2)
                            elif "投信" in name:
                                market_info["trust_net"] = round(diff, 2)
                            elif "自營商" in name and "外資" not in name:
                                market_info["dealer_net"] = round(market_info.get("dealer_net", 0) + diff, 2)
                        except (ValueError, TypeError):
                            continue
                logger.info(f"✅ [MarketDecision] 獲取三大法人: 外{market_info['foreign_net']} 投{market_info['trust_net']}")
        except Exception as e:
            logger.warning(f"獲取三大法人數據失敗: {e}")

        # 4. 獲取美股、日股、匯率 (yfinance)
        ext_data = await self.get_external_market_status()
        market_info.update(ext_data)

        self.market_cache = market_info
        self.cache_time = now
        return market_info

    async def get_external_market_status(self) -> Dict:
        """獲取美股、日股、匯率等外部數據"""
        try:
            # 這裡非同步抓取
            loop = asyncio.get_event_loop()
            symbols = ["^GSPC", "^N225", "TWD=X", "2330.TW"]
            
            # yfinance 的下載建議在 thread pool 中跑
            def fetch_yf():
                data = {}
                for sym in symbols:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period="2d")
                    if not hist.empty and len(hist) >= 2:
                        prev = hist['Close'].iloc[-2]
                        curr = hist['Close'].iloc[-1]
                        change_pct = ((curr - prev) / prev) * 100
                        data[sym] = {"price": curr, "change_pct": change_pct}
                    elif not hist.empty:
                        data[sym] = {"price": hist['Close'].iloc[-1], "change_pct": 0}
                return data

            yf_data = await loop.run_in_executor(None, fetch_yf)
            
            def safe_float(v, default=0.0):
                try:
                    f = float(v)
                    import math
                    return default if (math.isnan(f) or math.isinf(f)) else round(f, 2)
                except:
                    return default

            return {
                "sp500_change": safe_float(yf_data.get("^GSPC", {}).get("change_pct", 0)),
                "nikkei_change": safe_float(yf_data.get("^N225", {}).get("change_pct", 0)),
                "usdtwd": safe_float(yf_data.get("TWD=X", {}).get("price", 0)),
                "usdtwd_change": safe_float(yf_data.get("TWD=X", {}).get("change_pct", 0)),
                "tsmc_status": safe_float(yf_data.get("2330.TW", {}).get("change_pct", 0))
            }
        except Exception as e:
            logger.warning(f"外部數據獲取失敗: {e}")
            return {}

    def get_trading_decision(self, market_cond: str, stock_cond: str) -> Dict:
        """
        聯合決策矩陣
        market_cond: 'BULL' | 'NEUTRAL' | 'BEAR'
        stock_cond: 'STRONG' | 'NEUTRAL' | 'WEAK'
        """
        matrix = {
            ('BULL', 'STRONG'):   {"action": "✅ 全力做多", "position": "100%", "level": "success"},
            ('BULL', 'NEUTRAL'):  {"action": "✅ 做多", "position": "70%", "level": "info"},
            ('BULL', 'WEAK'):     {"action": "🟡 謹慎試單", "position": "30%", "level": "warning"},
            ('NEUTRAL', 'STRONG'): {"action": "✅ 做多 (個股獨立行情)", "position": "70%", "level": "info"},
            ('NEUTRAL', 'NEUTRAL'):{"action": "🟡 謹慎試單", "position": "30%", "level": "warning"},
            ('NEUTRAL', 'WEAK'):   {"action": "❌ 觀望", "position": "0%", "level": "error"},
            ('BEAR', 'STRONG'):    {"action": "🟡 輕倉做多 (逆勢)", "position": "30%", "level": "warning"},
            ('BEAR', 'NEUTRAL'):   {"action": "❌ 觀望", "position": "0%", "level": "error"},
            ('BEAR', 'WEAK'):      {"action": "❌ 空手", "position": "0%", "level": "error"},
        }
        
        res = matrix.get((market_cond, stock_cond), {"action": "未知", "position": "0%", "level": "default"})
        return res

    async def get_market_warnings(self) -> List[Dict]:
        """生成大盤預警系統消息"""
        now = datetime.now()
        cur_time = now.time()
        
        data = await self.get_market_data()
        warnings = []
        
        # 1. 開盤預警 (08:00 - 09:15)
        if time(8, 0) <= cur_time <= time(9, 15):
            sp500 = data.get("sp500_change", 0)
            nikkei = data.get("nikkei_change", 0)
            usdtwd = data.get("usdtwd", 0)
            
            prediction = "偏多" if sp500 > 0 and nikkei > 0 else "觀望"
            if sp500 < -0.5 or nikkei < -0.5: prediction = "偏空"
            
            warnings.append({
                "type": "opening",
                "title": "🌅 今日開盤預警",
                "content": [
                    f"昨日美股：S&P 500 {sp500:+.2f}% {'🔴' if sp500 > 0 else '🟢'}",
                    f"昨日日經：{nikkei:+.2f}% {'🔴' if nikkei > 0 else '🟢'}",
                    f"美元台幣：{usdtwd} ({data.get('usdtwd_change', 0):+.2f}%)",
                    f"外資昨日：{data.get('foreign_net', 0)} 億 {'🔴' if data.get('foreign_net', 0) > 0 else '🟢'}"
                ],
                "prediction": f"{'🔴' if '多' in prediction else '🟢' if '空' in prediction else '🟡'} 今日{prediction}，可{'布局多單' if '多' in prediction else '謹慎應對'}",
                "timestamp": now.strftime("%H:%M")
            })
            
        # 2. 盤中異常預警 (09:15 - 13:00)
        if time(9, 15) <= cur_time <= time(13, 0):
            change_pct = data.get("change_pct", 0)
            tsmc = data.get("tsmc_status", 0)
            
            if abs(change_pct) > 1.0 or abs(tsmc) > 2.0:
                warnings.append({
                    "type": "abnormal",
                    "title": "🚨 盤中異常警示",
                    "content": [
                        f"加權指數：{data.get('index')} ({change_pct:+.2f}%)",
                        f"原因：{'台積電急殺' if tsmc < -1.5 else '台積電強拉' if tsmc > 1.5 else '指數波動大'}",
                        f"量能估計：{'爆量' if change_pct < -0.5 else '正常'}",
                        f"外資：即時趨勢 {'🟢' if change_pct < 0 else '🔴'}"
                    ],
                    "recommendation": f"🟢 減倉 50%，觀望大盤止跌" if change_pct < -0.8 else "🔴 持續持有，盤勢穩定",
                    "timestamp": now.strftime("%H:%M")
                })
            else:
                # 正常盤中提醒
                warnings.append({
                    "type": "normal",
                    "title": "📊 盤中動態提醒",
                    "content": [
                        f"加權指數：{data.get('index')} ({change_pct:+.2f}%)",
                        f"台積電：{tsmc:+.2f}%",
                        f"外資動向：{'🔴' if data.get('foreign_net', 0) > 0 else '🟢'} {data.get('foreign_net', 0)} 億"
                    ],
                    "recommendation": "🟡 盤勢平穩，按策略操作",
                    "timestamp": now.strftime("%H:%M")
                })
                
        # 3. 尾盤預警 (13:00 - 14:00)
        if time(13, 0) <= cur_time <= time(14, 0):
            change_pct = data.get("change_pct", 0)
            warnings.append({
                "type": "closing",
                "title": "🕐 尾盤操作提醒",
                "content": [
                    f"加權指數：{data.get('index')} ({change_pct:+.2f}%)",
                    f"尾盤量能：{'偏弱' if change_pct < 0 else '守穩'}",
                    f"外資現貨：{data.get('foreign_net', 0)} 億"
                ],
                "prediction": f"{'🔴' if change_pct > -0.2 else '🟢'} 尾盤可能{'守穩' if change_pct > -0.2 else '收低'}，留倉風險{'低' if change_pct > 0 else '高'}",
                "timestamp": now.strftime("%H:%M")
            })
            
        return warnings

# 單例
market_decision_service = MarketDecisionService()
