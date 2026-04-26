"""
AI 新聞爬蟲服務
自動爬取財經新聞，分析市場熱門話題，提取相關股票

支援來源:
1. 鉅亨網 (cnyes.com)
2. Yahoo 股市新聞
3. 經濟日報
4. 工商時報
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
import json
import logging
import ssl
import certifi
from collections import Counter

logger = logging.getLogger(__name__)

# 台股代碼對照表 (常見股票)
STOCK_NAME_MAP = {
    # 權值股
    "台積電": "2330", "鴻海": "2317", "聯發科": "2454",
    "台達電": "2308", "聯電": "2303", "中華電": "2412",
    "富邦金": "2881", "國泰金": "2882", "中信金": "2891",
    "兆豐金": "2886", "台新金": "2887", "玉山金": "2884",
    
    # 電子股
    "廣達": "2382", "技嘉": "2376", "微星": "2377",
    "華碩": "2357", "宏碁": "2353", "仁寶": "2324",
    "緯創": "3231", "英業達": "2356", "和碩": "4938",
    "日月光": "3711", "矽品": "2325", "力成": "6239",
    
    # AI 概念股
    "緯穎": "6669", "廣達": "2382", "鴻海": "2317",
    "台光電": "2383", "金像電": "2368", "景碩": "3189",
    "嘉澤": "3533", "健策": "3653", "創意": "3443",
    
    # 航運股
    "長榮": "2603", "陽明": "2609", "萬海": "2615",
    "長榮航": "2618", "華航": "2610", "台驊": "2637",
    
    # 金融股
    "國泰金": "2882", "富邦金": "2881", "中信金": "2891",
    "台新金": "2887", "玉山金": "2884", "兆豐金": "2886",
    "第一金": "2892", "華南金": "2880", "合庫金": "5880",
    
    # 傳產股
    "台塑": "1301", "南亞": "1303", "台化": "1326",
    "台泥": "1101", "亞泥": "1102", "統一": "1216",
    "大立光": "3008", "玉晶光": "3406", "揚明光": "3504",
    
    # 中小型股
    "工信": "5521", "世芯": "3661", "祥碩": "5269",
    "信驊": "5274", "瑞昱": "2379", "聯詠": "3034",
}

# 新聞情緒關鍵詞
POSITIVE_KEYWORDS = [
    "大漲", "創新高", "突破", "利多", "買超", "營收成長",
    "獲利創高", "法人看好", "目標價上調", "強勢", "爆量",
    "外資買", "投信買", "主力進場", "多頭", "籌碼集中"
]

NEGATIVE_KEYWORDS = [
    "大跌", "創新低", "跌破", "利空", "賣超", "營收衰退",
    "獲利下滑", "目標價下調", "弱勢", "爆量下殺",
    "外資賣", "投信賣", "主力出場", "空頭", "籌碼鬆動"
]


class NewsCrawlerService:
    """新聞爬蟲服務"""
    
    def __init__(self):
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.session = None
    
    async def _get_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            self.session = aiohttp.ClientSession(connector=connector, headers=self.headers)
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    # ==================== 新聞爬蟲 ====================
    
    async def crawl_cnyes_news(self) -> List[Dict]:
        """爬取鉅亨網台股新聞"""
        news_list = []
        url = "https://news.cnyes.com/news/cat/tw_stock"
        
        try:
            session = await self._get_session()
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    logger.warning(f"鉅亨網返回狀態碼: {response.status}")
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 解析新聞列表
                articles = soup.find_all('a', class_='_2LOLO')  # 鉅亨網新聞連結
                if not articles:
                    articles = soup.find_all('a', href=re.compile(r'/news/id/\d+'))
                
                for article in articles[:20]:  # 最多取20則
                    title = article.get_text(strip=True)
                    if title and len(title) > 5:
                        news_list.append({
                            "source": "鉅亨網",
                            "title": title,
                            "url": article.get('href', ''),
                            "time": datetime.now().strftime("%Y-%m-%d"),
                        })
                
                logger.info(f"鉅亨網爬取 {len(news_list)} 則新聞")
                
        except Exception as e:
            logger.error(f"爬取鉅亨網失敗: {e}")
        
        return news_list
    
    async def crawl_yahoo_stock_news(self) -> List[Dict]:
        """爬取 Yahoo 股市新聞"""
        news_list = []
        url = "https://tw.stock.yahoo.com/news"
        
        try:
            session = await self._get_session()
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    logger.warning(f"Yahoo返回狀態碼: {response.status}")
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 解析新聞列表
                articles = soup.find_all('h3')
                for article in articles[:20]:
                    link = article.find('a')
                    if link:
                        title = link.get_text(strip=True)
                        if title and len(title) > 5:
                            news_list.append({
                                "source": "Yahoo股市",
                                "title": title,
                                "url": f"https://tw.stock.yahoo.com{link.get('href', '')}",
                                "time": datetime.now().strftime("%Y-%m-%d"),
                            })
                
                logger.info(f"Yahoo股市爬取 {len(news_list)} 則新聞")
                
        except Exception as e:
            logger.error(f"爬取Yahoo股市失敗: {e}")
        
        return news_list
    
    async def crawl_money_udn(self) -> List[Dict]:
        """爬取經濟日報股市新聞"""
        news_list = []
        url = "https://money.udn.com/money/cate/5607"
        
        try:
            session = await self._get_session()
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                articles = soup.find_all('h3', class_='title')
                for article in articles[:15]:
                    link = article.find('a')
                    if link:
                        title = link.get_text(strip=True)
                        if title and len(title) > 5:
                            news_list.append({
                                "source": "經濟日報",
                                "title": title,
                                "url": f"https://money.udn.com{link.get('href', '')}",
                                "time": datetime.now().strftime("%Y-%m-%d"),
                            })
                
                logger.info(f"經濟日報爬取 {len(news_list)} 則新聞")
                
        except Exception as e:
            logger.error(f"爬取經濟日報失敗: {e}")
        
        return news_list
    
    async def crawl_ptt_stock(self) -> List[Dict]:
        """爬取 PTT Stock 版熱門文章"""
        news_list = []
        url = "https://www.ptt.cc/bbs/Stock/index.html"
        
        try:
            session = await self._get_session()
            # PTT 需要 cookie 過年齡驗證
            cookies = {'over18': '1'}
            async with session.get(url, timeout=15, cookies=cookies) as response:
                if response.status != 200:
                    logger.warning(f"PTT返回狀態碼: {response.status}")
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 解析文章列表
                articles = soup.find_all('div', class_='r-ent')
                for article in articles[:20]:
                    title_elem = article.find('div', class_='title')
                    if title_elem:
                        link = title_elem.find('a')
                        if link:
                            title = link.get_text(strip=True)
                            # 過濾公告、刪除文章
                            if title and len(title) > 5 and not title.startswith('[公告]'):
                                # 檢查推文數
                                push_elem = article.find('div', class_='nrec')
                                push_count = 0
                                if push_elem:
                                    push_text = push_elem.get_text(strip=True)
                                    if push_text.isdigit():
                                        push_count = int(push_text)
                                    elif push_text == '爆':
                                        push_count = 100
                                
                                news_list.append({
                                    "source": "PTT Stock",
                                    "title": title,
                                    "url": f"https://www.ptt.cc{link.get('href', '')}",
                                    "time": datetime.now().strftime("%Y-%m-%d"),
                                    "push_count": push_count,
                                })
                
                # 依推文數排序，取熱門
                news_list.sort(key=lambda x: x.get('push_count', 0), reverse=True)
                logger.info(f"PTT Stock爬取 {len(news_list)} 篇文章")
                
        except Exception as e:
            logger.error(f"爬取PTT Stock失敗: {e}")
        
        return news_list[:15]  # 只取前15篇熱門
    
    async def crawl_all_news(self) -> List[Dict]:
        """同時爬取所有新聞來源 (含社群)"""
        tasks = [
            self.crawl_cnyes_news(),
            self.crawl_yahoo_stock_news(),
            self.crawl_money_udn(),
            self.crawl_ptt_stock(),  # 新增 PTT
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"新聞爬取異常: {result}")
        
        # 嘗試整合 Threads/Instagram (可選)
        try:
            from app.services.threads_crawler import get_threads_crawler
            threads = get_threads_crawler()
            if threads.logged_in or threads.login():
                threads_posts = threads.crawl_stock_hashtags(amount=10)
                # 轉換為新聞格式
                for post in threads_posts[:10]:
                    all_news.append({
                        "source": post.get("source", "Threads"),
                        "title": post.get("title", ""),
                        "url": post.get("url", ""),
                        "time": post.get("time", ""),
                    })
                logger.info(f"Threads 取得 {len(threads_posts)} 篇貼文")
        except Exception as e:
            logger.debug(f"Threads 爬蟲不可用 (需設定 IG 帳號): {e}")
        
        # 嘗試整合 GoodInfo 新聞 (可選)
        try:
            from app.services.goodinfo_crawler import goodinfo_crawler
            goodinfo_news = await goodinfo_crawler.get_stock_news()
            for news in goodinfo_news[:15]:
                all_news.append({
                    "source": "GoodInfo",
                    "title": news.get("title", ""),
                    "url": "",
                    "time": news.get("date", ""),
                })
            logger.info(f"GoodInfo 取得 {len(goodinfo_news)} 則新聞")
        except Exception as e:
            logger.debug(f"GoodInfo 爬蟲異常: {e}")
        
        # 嘗試整合 TWSE 市場新聞 (漲跌幅/成交量資訊)
        try:
            from app.services.twse_crawler import twse_crawler
            twse_news = await twse_crawler.get_market_news()
            for news in twse_news[:15]:
                all_news.append({
                    "source": news.get("source", "TWSE"),
                    "title": news.get("title", ""),
                    "url": "",
                    "time": news.get("date", ""),
                })
            logger.info(f"TWSE 取得 {len(twse_news)} 則新聞/公告")
        except Exception as e:
            logger.debug(f"TWSE 爬蟲異常: {e}")
        
        # 如果所有來源都失敗，使用備援新聞服務
        if len(all_news) == 0:
            try:
                from app.services.news_crawler_fix import get_fallback_news
                fallback_news = get_fallback_news()
                for news in fallback_news:
                    all_news.append({
                        "source": news.get("source", "系統快訊"),
                        "title": news.get("title", ""),
                        "url": "",
                        "time": news.get("timestamp", datetime.now().strftime("%Y-%m-%d")),
                    })
                logger.info(f"📰 使用備援新聞服務，取得 {len(all_news)} 則新聞")
            except Exception as e:
                logger.debug(f"備援新聞服務異常: {e}")
        
        logger.info(f"共爬取 {len(all_news)} 則新聞/討論")
        return all_news
    
    # ==================== 新聞分析 ====================
    
    def extract_stock_mentions(self, news_list: List[Dict]) -> Dict[str, int]:
        """從新聞中提取股票提及次數"""
        mentions = Counter()
        
        for news in news_list:
            title = news.get("title", "")
            
            # 方法1: 直接匹配股票名稱
            for stock_name, stock_code in STOCK_NAME_MAP.items():
                if stock_name in title:
                    mentions[stock_code] += 1
            
            # 方法2: 匹配股票代碼 (4位數字)
            codes = re.findall(r'\b(\d{4})\b', title)
            for code in codes:
                if code.startswith(('1', '2', '3', '4', '5', '6', '8', '9')):
                    mentions[code] += 1
        
        return dict(mentions.most_common(50))
    
    def analyze_sentiment(self, title: str) -> Tuple[str, float]:
        """分析新聞標題情緒"""
        positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in title)
        negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title)
        
        if positive_count > negative_count:
            sentiment = "positive"
            score = min(positive_count * 0.2, 1.0)
        elif negative_count > positive_count:
            sentiment = "negative"
            score = -min(negative_count * 0.2, 1.0)
        else:
            sentiment = "neutral"
            score = 0.0
        
        return sentiment, score
    
    def categorize_news(self, news_list: List[Dict]) -> Dict[str, List[Dict]]:
        """將新聞分類"""
        categories = {
            "ai_tech": [],      # AI/科技
            "finance": [],      # 金融
            "shipping": [],     # 航運
            "semiconductor": [], # 半導體
            "traditional": [],  # 傳產
            "general": [],      # 一般
        }
        
        for news in news_list:
            title = news["title"]
            
            if any(kw in title for kw in ["AI", "人工智慧", "ChatGPT", "輝達", "NVIDIA"]):
                categories["ai_tech"].append(news)
            elif any(kw in title for kw in ["台積電", "聯發科", "半導體", "晶片", "IC"]):
                categories["semiconductor"].append(news)
            elif any(kw in title for kw in ["金融", "銀行", "壽險", "證券", "升息"]):
                categories["finance"].append(news)
            elif any(kw in title for kw in ["航運", "貨櫃", "長榮", "陽明", "萬海"]):
                categories["shipping"].append(news)
            elif any(kw in title for kw in ["台塑", "鋼鐵", "水泥", "營建"]):
                categories["traditional"].append(news)
            else:
                categories["general"].append(news)
        
        return categories
    
    async def generate_daily_report(self) -> Dict:
        """
        生成每日新聞分析報告
        這是主要的對外接口
        """
        logger.info("開始生成每日新聞分析報告...")
        
        # 1. 爬取新聞
        news_list = await self.crawl_all_news()
        
        if not news_list:
            return {
                "status": "error",
                "message": "無法獲取新聞數據",
                "timestamp": datetime.now().isoformat()
            }
        
        # 2. 提取熱門股票
        hot_stocks = self.extract_stock_mentions(news_list)
        
        # 3. 分類新聞
        categorized = self.categorize_news(news_list)
        
        # 4. 各類別熱度
        category_heat = {
            cat: len(items) 
            for cat, items in categorized.items() 
            if items
        }
        
        # 5. 分析各新聞情緒
        sentiment_summary = {"positive": 0, "negative": 0, "neutral": 0}
        for news in news_list:
            sentiment, _ = self.analyze_sentiment(news["title"])
            sentiment_summary[sentiment] += 1
        
        # 6. 提取今日關鍵主題
        key_themes = []
        top_categories = sorted(category_heat.items(), key=lambda x: x[1], reverse=True)[:3]
        
        category_names = {
            "ai_tech": "AI 科技概念",
            "semiconductor": "半導體族群",
            "finance": "金融保險",
            "shipping": "航運類股",
            "traditional": "傳統產業",
            "general": "一般題材"
        }
        
        for cat, count in top_categories:
            key_themes.append({
                "theme": category_names.get(cat, cat),
                "news_count": count,
                "sample_news": [n["title"] for n in categorized[cat][:3]]
            })
        
        # 7. 生成報告
        report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "summary": {
                "total_news": len(news_list),
                "sentiment": sentiment_summary,
                "market_mood": "偏多" if sentiment_summary["positive"] > sentiment_summary["negative"] else "偏空" if sentiment_summary["negative"] > sentiment_summary["positive"] else "中性"
            },
            "hot_stocks": [
                {"code": code, "mentions": count}
                for code, count in list(hot_stocks.items())[:20]
            ],
            "key_themes": key_themes,
            "category_heat": category_heat,
            "top_news": [
                {
                    "title": n["title"],
                    "source": n["source"],
                    "sentiment": self.analyze_sentiment(n["title"])[0]
                }
                for n in news_list[:10]
            ],
            "investment_focus": self._generate_investment_focus(hot_stocks, key_themes, sentiment_summary)
        }
        
        logger.info(f"報告生成完成，熱門股票: {list(hot_stocks.keys())[:5]}")
        return report
    
    def _generate_investment_focus(self, hot_stocks: Dict, themes: List, sentiment: Dict) -> Dict:
        """生成明日投資重點"""
        focus = {
            "market_outlook": "",
            "sector_focus": [],
            "stock_watchlist": [],
            "risk_warnings": []
        }
        
        # 判斷市場展望
        if sentiment["positive"] > sentiment["negative"] * 1.5:
            focus["market_outlook"] = "市場情緒偏樂觀，可關注強勢族群"
        elif sentiment["negative"] > sentiment["positive"] * 1.5:
            focus["market_outlook"] = "市場情緒偏保守，建議控制部位"
        else:
            focus["market_outlook"] = "市場情緒中性，觀察盤中走勢"
        
        # 產業焦點
        for theme in themes:
            focus["sector_focus"].append(theme["theme"])
        
        # 推薦關注
        focus["stock_watchlist"] = list(hot_stocks.keys())[:10]
        
        # 風險提醒
        if sentiment["negative"] > 10:
            focus["risk_warnings"].append("近期負面新聞較多，注意風險控管")
        
        return focus


# 全域實例
news_crawler = NewsCrawlerService()


# ==================== 便捷函數 ====================

async def get_daily_news_report() -> Dict:
    """獲取每日新聞報告"""
    return await news_crawler.generate_daily_report()

async def get_hot_stocks_from_news() -> List[str]:
    """獲取新聞中的熱門股票代碼"""
    report = await news_crawler.generate_daily_report()
    return [s["code"] for s in report.get("hot_stocks", [])]
