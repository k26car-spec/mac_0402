"""
TWSE/TPEx 證交所資訊爬蟲
官方 API 無反爬蟲限制，資料更可靠

提供功能:
1. 法人買賣超 (三大法人)
2. 每日收盤行情
3. 漲跌幅排行
4. 成交量排行
5. 個股資訊

資料來源: 台灣證券交易所 / 櫃買中心
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import ssl
import os
import certifi
import json

logger = logging.getLogger(__name__)


class TWSECrawler:
    """證交所資料爬蟲"""
    
    # API 端點
    TWSE_URL = "https://www.twse.com.tw"
    TPEX_URL = "https://www.tpex.org.tw"
    
    def __init__(self):
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-TW,zh;q=0.9',
        }
    
    async def _get_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            timeout = aiohttp.ClientTimeout(total=5)
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=timeout
            )
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _fetch_json(self, url: str, params: Dict = None) -> Optional[Dict]:
        """獲取 JSON 資料"""
        try:
            session = await self._get_session()
            # 添加 Referer header 避免被阻擋
            headers = {
                'Referer': 'https://www.twse.com.tw/zh/',
                'Origin': 'https://www.twse.com.tw'
            }
            async with session.get(url, params=params, headers=headers, allow_redirects=True) as response:
                if response.status not in [200, 307]:
                    logger.warning(f"TWSE API 返回 {response.status}")
                    return None
                # 如果是 307，嘗試跟隨重定向
                if response.status == 307:
                    redirect_url = response.headers.get('Location')
                    if redirect_url:
                        async with session.get(redirect_url, headers=headers) as redirect_response:
                            if redirect_response.status == 200:
                                return await redirect_response.json()
                    return None
                return await response.json()
        except Exception as e:
            logger.error(f"TWSE API 請求失敗: {e}")
            return None
    
    # ==================== 三大法人買賣超 ====================
    
    async def get_institutional_trading(self, date: str = None) -> Dict:
        """
        取得三大法人買賣超資料
        
        Args:
            date: 日期 (YYYYMMDD)，預設今天
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        
        url = f"{self.TWSE_URL}/rwd/zh/fund/BFI82U"
        params = {"date": date, "response": "json"}
        
        data = await self._fetch_json(url, params)
        
        if not data or "data" not in data:
            logger.warning("無法取得法人買賣超資料")
            return {"status": "error", "message": "無資料"}
        
        result = {
            "status": "success",
            "date": date,
            "data": []
        }
        
        for item in data.get("data", []):
            if len(item) >= 4:
                result["data"].append({
                    "name": item[0],
                    "buy": item[1],
                    "sell": item[2],
                    "diff": item[3],
                })
        
        logger.info(f"取得 {date} 法人買賣超資料")
        return result
    
    # ==================== 每日收盤行情 ====================
    
    async def get_daily_trading(self, date: str = None) -> List[Dict]:
        """
        取得上市股票每日收盤行情
        
        Args:
            date: 日期 (YYYYMMDD)
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        
        url = f"{self.TWSE_URL}/rwd/zh/afterTrading/MI_INDEX"
        params = {"date": date, "response": "json"}
        
        data = await self._fetch_json(url, params)
        
        if not data:
            return []
        
        stocks = []
        
        # 解析股票列表
        tables = data.get("tables", [])
        for table in tables:
            if table.get("title") == "每日收盤行情(全部(不含權證、牛熊證))":
                for row in table.get("data", [])[:50]:  # 取前50筆
                    if len(row) >= 10:
                        try:
                            stocks.append({
                                "code": row[0],
                                "name": row[1],
                                "volume": row[2],
                                "transaction": row[3],
                                "value": row[4],
                                "open": row[5],
                                "high": row[6],
                                "low": row[7],
                                "close": row[8],
                                "change": row[9] if len(row) > 9 else "",
                                "change_pct": row[10] if len(row) > 10 else "",
                            })
                        except:
                            continue
        
        logger.info(f"取得 {date} 收盤行情 {len(stocks)} 筆")
        return stocks
    
    # ==================== 個股法人買賣超 ====================
    
    async def get_stock_institutional(self, stock_code: str, days: int = 30) -> List[Dict]:
        """
        取得個股法人買賣超 (優先從資料庫讀取)
        """
        try:
            from app.services.batch_institutional_service import batch_institutional_service
            
            clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
            
            # 1. 嘗試從資料庫讀取
            db_results = await batch_institutional_service.get_stock_institutional_history(clean_code, limit=days)
            
            # 如果資料庫已經有足夠資料，直接返回
            if len(db_results) >= min(days, 15): 
                return db_results
            
            # 2. 如果資料庫嚴重不足 (少於 5 天)，執行同步比對並補抓
            # 這回應了用戶需求：查詢哪一個，就執行批次比對缺失部分
            logger.info(f"🔄 {clean_code} 籌碼不足 ({len(db_results)} 筆)，啟動缺失日期補抓...")
            
            sync_task = batch_institutional_service.sync_missing_dates(requested_days=days)
            
            if not db_results:
                # 若完全沒資料，等待同步完成以便提供即時回饋
                await sync_task
            else:
                # 若已有部分資料，背景同步，先給用戶看現有的
                asyncio.create_task(sync_task)
            
            # 重新整理結果
            return await batch_institutional_service.get_stock_institutional_history(clean_code, limit=days)

        except Exception as e:
            logger.error(f"❌ 獲取法人籌碼失敗: {e}")
            return []
    
    # ==================== 漲跌幅排行 ====================
    
    async def get_price_ranking(self, rank_type: str = "up") -> List[Dict]:
        """
        取得漲跌幅排行
        
        Args:
            rank_type: "up" 漲幅 / "down" 跌幅
        """
        # 先取得全部行情
        stocks = await self.get_daily_trading()
        
        if not stocks:
            return []
        
        # 解析漲跌幅並排序
        valid_stocks = []
        for stock in stocks:
            try:
                change_pct = float(stock.get("change_pct", "0").replace(",", "").replace("%", ""))
                stock["change_pct_float"] = change_pct
                valid_stocks.append(stock)
            except:
                continue
        
        # 排序
        if rank_type == "up":
            valid_stocks.sort(key=lambda x: x["change_pct_float"], reverse=True)
        else:
            valid_stocks.sort(key=lambda x: x["change_pct_float"])
        
        return valid_stocks[:20]
    
    # ==================== 成交量排行 ====================
    
    async def get_volume_ranking(self) -> List[Dict]:
        """取得成交量排行"""
        stocks = await self.get_daily_trading()
        
        if not stocks:
            return []
        
        # 解析成交量並排序
        valid_stocks = []
        for stock in stocks:
            try:
                volume = int(stock.get("volume", "0").replace(",", ""))
                stock["volume_int"] = volume
                valid_stocks.append(stock)
            except:
                continue
        
        valid_stocks.sort(key=lambda x: x["volume_int"], reverse=True)
        return valid_stocks[:20]
    
    # ==================== 個股資訊 ====================
    
    async def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """取得個股基本資訊"""
        stocks = await self.get_daily_trading()
        
        for stock in stocks:
            if stock.get("code") == stock_code:
                return stock
        
        return None
    
    # ==================== 市場新聞/公告 ====================
    
    async def get_market_news(self) -> List[Dict]:
        """
        取得市場新聞公告
        資料來源: 證交所公告
        """
        news_list = []
        
        # TWSE 重大訊息
        try:
            url = f"{self.TWSE_URL}/rwd/zh/news/newslist"
            params = {"response": "json"}
            data = await self._fetch_json(url, params)
            
            if data and "data" in data:
                for item in data.get("data", [])[:20]:
                    if len(item) >= 3:
                        news_list.append({
                            "source": "TWSE 公告",
                            "date": item[0] if len(item) > 0 else "",
                            "title": item[1] if len(item) > 1 else "",
                            "category": "公告"
                        })
        except Exception as e:
            logger.debug(f"TWSE 公告獲取失敗: {e}")
        
        # 備用: 取得當日漲幅股票作為熱門話題
        try:
            gainers = await self.get_price_ranking("up")
            for stock in gainers[:5]:
                news_list.append({
                    "source": "TWSE 熱門",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "title": f"【漲幅排行】{stock.get('code', '')} {stock.get('name', '')} 漲幅 {stock.get('change_pct', '')}",
                    "category": "熱門股"
                })
        except:
            pass
        
        # 取得今日成交量排行
        try:
            volume = await self.get_volume_ranking()
            for stock in volume[:5]:
                news_list.append({
                    "source": "TWSE 成交量",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "title": f"【成交量】{stock.get('code', '')} {stock.get('name', '')} 成交 {stock.get('volume', '')} 張",
                    "category": "成交量"
                })
        except:
            pass
        
        logger.info(f"TWSE 取得 {len(news_list)} 則新聞/公告")
        return news_list
    
    # ==================== 綜合報告 ====================
    
    async def generate_market_report(self) -> Dict:
        """生成市場綜合報告"""
        logger.info("開始生成 TWSE 市場報告...")
        
        tasks = [
            self.get_institutional_trading(),
            self.get_price_ranking("up"),
            self.get_price_ranking("down"),
            self.get_volume_ranking(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        institutional = results[0] if isinstance(results[0], dict) else {}
        top_gainers = results[1] if isinstance(results[1], list) else []
        top_losers = results[2] if isinstance(results[2], list) else []
        top_volume = results[3] if isinstance(results[3], list) else []
        
        report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source": "TWSE",
            "institutional": institutional,
            "rankings": {
                "top_gainers": top_gainers[:10],
                "top_losers": top_losers[:10],
                "top_volume": top_volume[:10],
            },
            "summary": {
                "total_stocks": len(top_gainers) + len(top_losers),
            }
        }
        
        logger.info("TWSE 市場報告生成完成")
        return report


# 全域實例
twse_crawler = TWSECrawler()


# ==================== 便捷函數 ====================

async def get_twse_report() -> Dict:
    """獲取 TWSE 市場報告"""
    return await twse_crawler.generate_market_report()

async def get_institutional_data() -> Dict:
    """獲取法人買賣超"""
    return await twse_crawler.get_institutional_trading()


# ==================== 測試 ====================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("TWSE 爬蟲測試")
        print("=" * 60)
        
        crawler = TWSECrawler()
        
        # 測試法人買賣超
        print("\n💰 三大法人買賣超:")
        institutional = await crawler.get_institutional_trading()
        if institutional.get("status") == "success":
            for item in institutional.get("data", [])[:3]:
                print(f"  {item['name']}: {item['diff']}")
        
        # 測試漲幅排行
        print("\n📈 漲幅排行前5名:")
        gainers = await crawler.get_price_ranking("up")
        for stock in gainers[:5]:
            print(f"  {stock['code']} {stock['name']}: {stock.get('change_pct', '-')}")
        
        # 測試成交量排行
        print("\n📊 成交量排行前5名:")
        volume = await crawler.get_volume_ranking()
        for stock in volume[:5]:
            print(f"  {stock['code']} {stock['name']}: {stock.get('volume', '-')}")
        
        await crawler.close()
        print("\n✅ 測試完成!")
    
    asyncio.run(test())
