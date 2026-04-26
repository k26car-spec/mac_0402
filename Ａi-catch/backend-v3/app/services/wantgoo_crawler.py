"""
Wantgoo 個股新聞爬蟲服務
從 wantgoo.com 爬取特定股票的最新消息

網頁結構:
- 新聞容器: ul#gossips
- 新聞項目: li > a.block-link
- 標題: h4.title
- 日期: time.title-time
- 分類: span.title-category
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import re
import logging
import ssl
import certifi

logger = logging.getLogger(__name__)


class WantgooCrawler:
    """Wantgoo 個股新聞爬蟲"""
    
    BASE_URL = "https://www.wantgoo.com"
    
    def __init__(self):
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.wantgoo.com/',
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
    
    async def get_stock_news(self, stock_code: str, limit: int = 15) -> List[Dict]:
        """
        取得特定股票的最新消息 - 整合三個來源
        來源: 玩股網、鉅亨網、Yahoo 台股
        
        Args:
            stock_code: 股票代碼 (如: 5498)
            limit: 最大新聞數量
            
        Returns:
            新聞列表，每則包含 title, date, source, url, sentiment
        """
        all_news = []
        current_year = datetime.now().year
        
        # 取得股票名稱
        stock_name = await self._get_stock_name(stock_code)
        logger.info(f"開始取得新聞: 股票 {stock_code} ({stock_name})")
        
        # 並行抓取三個來源
        import asyncio
        
        tasks = [
            self._fetch_wantgoo_news(stock_code, limit),
            self._fetch_cnyes_news(stock_code, limit),
            self._fetch_yahoo_tw_news(stock_code, limit),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"新聞來源抓取失敗: {result}")
        
        # 過濾只保留一個月內的資料
        from datetime import timedelta
        one_month_ago = datetime.now() - timedelta(days=30)
        
        filtered_news = []
        seen_titles = set()  # 去重
        
        for news in all_news:
            title = news.get('title', '')
            date_str = news.get('date', '')
            
            # 去除重複標題
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            # 嚴格過濾：新聞標題必須包含股票代碼或股票名稱
            is_relevant = False
            if stock_code in title:
                is_relevant = True
            elif stock_name and len(stock_name) >= 2 and stock_name in title:
                is_relevant = True
            
            # 如果不相關，跳過此新聞
            if not is_relevant:
                continue
            
            # 檢查是否為一個月內的資料
            is_recent = True
            if date_str:
                try:
                    # 處理各種日期格式
                    news_date = None
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) >= 3:
                            news_date = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                        elif len(parts) == 2:
                            news_date = datetime(current_year, int(parts[0]), int(parts[1]))
                    elif '-' in date_str:
                        parts = date_str.split('-')
                        if len(parts) >= 3:
                            news_date = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    
                    if news_date and news_date < one_month_ago:
                        is_recent = False
                except:
                    pass  # 無法解析日期，預設為最近
            
            if is_recent:
                filtered_news.append(news)
        
        # 按日期排序 (最新的在前)
        filtered_news.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # 如果沒有找到相關新聞，返回提示訊息
        if len(filtered_news) == 0:
            logger.info(f"未找到股票 {stock_code} ({stock_name}) 的相關新聞")
            filtered_news.append({
                "title": f"暫無 {stock_name or stock_code} 的相關新聞",
                "date": datetime.now().strftime('%Y/%m/%d'),
                "source": "系統提示",
                "url": "",
                "sentiment": "neutral",
                "summary": f"目前各大新聞網站沒有 {stock_name or stock_code} ({stock_code}) 的專屬新聞報導。",
                "impact": "low"
            })
        else:
            logger.info(f"整合新聞: 總共 {len(all_news)} 則, 相關新聞 {len(filtered_news)} 則 (股票: {stock_code} {stock_name})")
        
        return filtered_news[:limit]
    
    async def _fetch_wantgoo_news(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """從玩股網抓取新聞"""
        news_list = []
        
        try:
            # 先嘗試 JSON API
            api_url = f"{self.BASE_URL}/stock/{stock_code}/gossips"
            session = await self._get_session()
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Referer': f'{self.BASE_URL}/stock/{stock_code}',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            async with session.get(api_url, timeout=15, headers=headers) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        data = await response.json()
                        for item in data[:limit]:
                            title = item.get('title', '')
                            publish_time = item.get('publishTime', '')
                            news_type = item.get('name', '玩股網')
                            news_id = item.get('id', 0)
                            
                            date_str = ''
                            if publish_time:
                                try:
                                    dt = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
                                    date_str = dt.strftime('%Y/%m/%d')
                                except:
                                    date_str = publish_time[:10]
                            
                            if title:
                                news_list.append({
                                    "title": title,
                                    "date": date_str,
                                    "source": f"玩股網 - {news_type}",
                                    "url": f"{self.BASE_URL}/news/{news_id}" if news_id else "",
                                    "sentiment": self._analyze_sentiment(title),
                                    "summary": "",
                                    "impact": "medium"
                                })
                        logger.info(f"玩股網 API 取得 {len(news_list)} 則新聞")
                        return news_list
        except Exception as e:
            logger.warning(f"玩股網 API 失敗: {e}")
        
        # API 失敗，使用 Playwright DOM 提取
        return await self._fallback_html_scrape(stock_code, limit)
    
    async def _fetch_cnyes_news(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """從鉅亨網搜尋特定股票代碼的新聞"""
        news_list = []
        
        # 動態取得股票名稱
        stock_name = await self._get_stock_name(stock_code)
        
        try:
            session = await self._get_session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-TW,zh;q=0.9',
            }
            
            # 方法1: 從鉅亨網個股頁面直接爬取 (最準確)
            stock_page_url = f"https://www.cnyes.com/twstock/{stock_code}"
            async with session.get(stock_page_url, timeout=15, headers={**headers, 'Accept': 'text/html'}) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 從頁面標題確認是正確的股票
                    title_tag = soup.find('title')
                    page_title = title_tag.text if title_tag else ''
                    
                    # 確認頁面是該股票的頁面
                    if stock_code in page_title or (stock_name and stock_name in page_title):
                        # 找新聞連結
                        news_items = soup.find_all('a', href=re.compile(r'/news/id/\d+'))
                        seen_titles = set()
                        
                        for item in news_items[:limit * 2]:
                            news_title = item.get_text(strip=True)
                            if news_title and len(news_title) > 10 and news_title not in seen_titles:
                                href = item.get('href', '')
                                if not href.startswith('http'):
                                    href = f"https://www.cnyes.com{href}"
                                
                                news_list.append({
                                    "title": news_title,
                                    "date": datetime.now().strftime('%Y/%m/%d'),
                                    "source": "鉅亨網",
                                    "url": href,
                                    "sentiment": self._analyze_sentiment(news_title),
                                    "summary": "",
                                    "impact": "medium"
                                })
                                seen_titles.add(news_title)
                                
                                if len(news_list) >= limit:
                                    break
            
            # 方法2: 如果個股頁面沒找到新聞，從 API 搜尋 (只保留包含股票代碼或名稱的新聞)
            if len(news_list) < limit // 2:
                for page in range(1, 4):  # 最多查詢 3 頁
                    if len(news_list) >= limit:
                        break
                        
                    api_url = f"https://news.cnyes.com/api/v3/news/category/tw_stock?page={page}&limit=30"
                    
                    async with session.get(api_url, timeout=15, headers=headers) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                items = data.get('items', {}).get('data', [])
                                
                                for item in items:
                                    title = item.get('title', '')
                                    # 嚴格過濾: 必須包含股票代碼或股票名稱
                                    is_relevant = False
                                    if stock_code in title:
                                        is_relevant = True
                                    elif stock_name and len(stock_name) >= 2 and stock_name in title:
                                        is_relevant = True
                                    
                                    if is_relevant:
                                        news_id = item.get('newsId', '')
                                        publish_at = item.get('publishAt', 0)
                                        
                                        date_str = ''
                                        if publish_at:
                                            try:
                                                from datetime import timezone
                                                dt = datetime.fromtimestamp(publish_at, tz=timezone.utc)
                                                date_str = dt.strftime('%Y/%m/%d')
                                            except:
                                                pass
                                        
                                        if title and len(title) > 5:
                                            news_list.append({
                                                "title": title,
                                                "date": date_str or datetime.now().strftime('%Y/%m/%d'),
                                                "source": "鉅亨網",
                                                "url": f"https://news.cnyes.com/news/id/{news_id}" if news_id else "",
                                                "sentiment": self._analyze_sentiment(title),
                                                "summary": "",
                                                "impact": "medium"
                                            })
                                            
                                        if len(news_list) >= limit:
                                            break
                            except Exception as e:
                                logger.warning(f"鉅亨網 API 解析失敗 (page {page}): {e}")
            
            logger.info(f"鉅亨網取得 {len(news_list)} 則新聞 (股票: {stock_code}, 名稱: {stock_name})")
                        
        except Exception as e:
            logger.warning(f"鉅亨網爬蟲失敗 (股票: {stock_code}): {e}")
        
        return news_list
    
    async def _get_stock_name(self, stock_code: str) -> str:
        """動態取得股票名稱"""
        # 常用股票名稱快取
        stock_names = {
            '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2308': '台達電',
            '2881': '富邦金', '2882': '國泰金', '2884': '玉山金', '2886': '兆豐金',
            '2891': '中信金', '2303': '聯電', '2412': '中華電', '3008': '大立光',
            '2382': '廣達', '2357': '華碩', '2301': '光寶科', '3711': '日月光投控',
            '2002': '中鋼', '1301': '台塑', '1303': '南亞', '6505': '台塑化',
            '5498': '凱崴', '5521': '工信', '8110': '華東', '3706': '神達',
            '5475': '德宏', '3363': '上詮', '6257': '矽格', '8155': '博智',
            '1623': '大東電', '8044': '網家',
        }
        
        if stock_code in stock_names:
            return stock_names[stock_code]
        
        # 從 API 動態取得
        try:
            session = await self._get_session()
            url = f"https://tw.stock.yahoo.com/quote/{stock_code}.TW"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.find('title')
                    if title:
                        # 格式: "股票名稱(代碼.TW) 走勢圖 - Yahoo奇摩股市"
                        match = re.match(r'([^(]+)\(', title.text)
                        if match:
                            return match.group(1).strip()
        except:
            pass
        
        return ''
    
    async def _fetch_yahoo_tw_news(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """從 Yahoo 台灣股市抓取個股新聞"""
        news_list = []
        url = f"https://tw.stock.yahoo.com/quote/{stock_code}.TW/news"
        
        try:
            session = await self._get_session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-TW,zh;q=0.9',
            }
            
            async with session.get(url, timeout=15, headers=headers) as response:
                if response.status != 200:
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 找新聞標題 (h3 標籤)
                news_items = soup.find_all('h3')
                
                for item in news_items[:limit * 2]:
                    link = item.find('a')
                    if link:
                        title = link.get_text(strip=True)
                        if title and len(title) > 8:
                            href = link.get('href', '')
                            if not href.startswith('http'):
                                href = f"https://tw.stock.yahoo.com{href}"
                            
                            news_list.append({
                                "title": title,
                                "date": datetime.now().strftime('%Y/%m/%d'),
                                "source": "Yahoo 台股",
                                "url": href,
                                "sentiment": self._analyze_sentiment(title),
                                "summary": "",
                                "impact": "medium"
                            })
                            
                            if len(news_list) >= limit:
                                break
            
            logger.info(f"Yahoo 台股取得 {len(news_list)} 則新聞 (股票: {stock_code})")
                        
        except Exception as e:
            logger.warning(f"Yahoo 台股爬蟲失敗 (股票: {stock_code}): {e}")
        
        return news_list
    
    async def _fallback_html_scrape(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """
        使用 Playwright + Stealth 模擬瀏覽器，從 DOM 提取 Wantgoo 新聞
        這可以繞過 Wantgoo 的 Cloudflare 反爬蟲機制
        """
        news_list = []
        url = f"{self.BASE_URL}/stock/{stock_code}"
        
        try:
            from playwright.async_api import async_playwright
            from playwright_stealth import Stealth
            import random
            
            async with async_playwright() as p:
                # 使用反偵測參數啟動瀏覽器
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                    ]
                )
                
                # 創建更真實的瀏覽器上下文
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-TW',
                    timezone_id='Asia/Taipei',
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # 應用 stealth 插件隱藏自動化特徵
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
                
                # 注入額外的反偵測腳本
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """)
                
                # 載入頁面
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    # 等待 JavaScript 完成
                    await page.wait_for_timeout(8000)
                    
                    # 模擬人類行為
                    await page.mouse.move(random.randint(100, 500), random.randint(100, 300))
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_timeout(2000)
                    
                except Exception as e:
                    logger.warning(f"頁面載入時發生問題 (股票: {stock_code}): {e}")
                
                # 從 DOM 提取新聞
                news_data = await page.evaluate('''
                    () => {
                        // 嘗試 gossips 區塊
                        const gossips = document.querySelector('ul#gossips');
                        if (gossips) {
                            const items = gossips.querySelectorAll('a.block-link');
                            if (items.length > 0) {
                                return {
                                    source: 'gossips',
                                    data: Array.from(items).map(a => ({
                                        title: a.querySelector('h4')?.innerText?.trim() || '',
                                        date: a.querySelector('time')?.innerText?.trim() || '',
                                        category: a.querySelector('.title-category')?.innerText?.trim() || '',
                                        url: a.href || ''
                                    }))
                                };
                            }
                        }
                        
                        // 備用：嘗試所有 block-link
                        const allLinks = document.querySelectorAll('a.block-link');
                        if (allLinks.length > 0) {
                            return {
                                source: 'all-links',
                                data: Array.from(allLinks).map(a => ({
                                    title: (a.querySelector('h4') || a.querySelector('h3'))?.innerText?.trim() || '',
                                    date: a.querySelector('time')?.innerText?.trim() || '',
                                    category: '',
                                    url: a.href || ''
                                }))
                            };
                        }
                        
                        return { source: 'none', data: [] };
                    }
                ''')
                
                await browser.close()
                
                source = news_data.get('source', 'none')
                data = news_data.get('data', [])
                
                if source in ('gossips', 'all-links') and data:
                    # DOM 提取格式: {title, date, category, url}
                    for item in data[:limit]:
                        title = item.get('title', '')
                        if not title:
                            continue
                        
                        # 格式化日期 (DOM 格式可能是 "11/25" 或 "2024")
                        date_str = item.get('date', '')
                        if date_str and '/' in date_str and len(date_str) <= 5:
                            # 格式化日期 (MM/DD -> YYYY/MM/DD)
                            current_year = datetime.now().year
                            date_str = f"{current_year}/{date_str}"
                        
                        category = item.get('category', '') or '玩股網'
                        news_url = item.get('url', '')
                        
                        news_list.append({
                            "title": title,
                            "date": date_str,
                            "source": f"玩股網 - {category}" if category else "玩股網",
                            "url": news_url,
                            "sentiment": self._analyze_sentiment(title),
                            "summary": "",
                            "impact": "medium"
                        })
                    
                    logger.info(f"Wantgoo DOM 提取 {len(news_list)} 則新聞 (股票: {stock_code})")
                
                else:
                    logger.warning(f"Wantgoo 無資料 (股票: {stock_code}, source: {source})")
                
        except ImportError:
            logger.warning("Playwright 未安裝，無法使用瀏覽器爬蟲")
            return await self._yahoo_finance_news(stock_code, limit)
        except Exception as e:
            logger.error(f"Playwright 爬蟲失敗 (股票: {stock_code}): {e}")
            return await self._yahoo_finance_news(stock_code, limit)
        
        # 如果 Wantgoo 沒有取得新聞，使用中文新聞備援
        if not news_list:
            return await self._yahoo_finance_news(stock_code, limit)
        
        return news_list
    
    async def _yahoo_finance_news(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """
        使用台灣中文新聞來源取得個股相關新聞
        來源: 鉅亨網、Yahoo 台股
        """
        news_list = []
        
        # 嘗試從鉅亨網取得個股新聞
        try:
            cnyes_news = await self._crawl_cnyes_stock_news(stock_code, limit)
            news_list.extend(cnyes_news)
            logger.info(f"鉅亨網取得 {len(cnyes_news)} 則新聞 (股票: {stock_code})")
        except Exception as e:
            logger.warning(f"鉅亨網新聞獲取失敗: {e}")
        
        # 如果鉅亨網新聞不足，嘗試 Yahoo 台股
        if len(news_list) < limit:
            try:
                yahoo_news = await self._crawl_yahoo_tw_stock_news(stock_code, limit - len(news_list))
                news_list.extend(yahoo_news)
                logger.info(f"Yahoo 台股取得 {len(yahoo_news)} 則新聞 (股票: {stock_code})")
            except Exception as e:
                logger.warning(f"Yahoo 台股新聞獲取失敗: {e}")
        
        return news_list
    
    async def _crawl_cnyes_stock_news(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """
        從鉅亨網爬取個股相關新聞
        URL: https://www.cnyes.com/twstock/{stock_code}
        """
        news_list = []
        url = f"https://www.cnyes.com/twstock/{stock_code}"
        
        try:
            session = await self._get_session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-TW,zh;q=0.9',
            }
            
            async with session.get(url, timeout=15, headers=headers) as response:
                if response.status != 200:
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 嘗試找新聞區塊
                news_items = soup.find_all('a', href=re.compile(r'/news/id/\d+'))
                
                for item in news_items[:limit]:
                    title = item.get_text(strip=True)
                    if title and len(title) > 8:
                        href = item.get('href', '')
                        if not href.startswith('http'):
                            href = f"https://www.cnyes.com{href}"
                        
                        news_list.append({
                            "title": title,
                            "date": datetime.now().strftime('%Y/%m/%d'),
                            "source": "鉅亨網",
                            "url": href,
                            "sentiment": self._analyze_sentiment(title),
                            "summary": "",
                            "impact": "medium"
                        })
                        
        except Exception as e:
            logger.error(f"鉅亨網爬蟲失敗 (股票: {stock_code}): {e}")
        
        return news_list
    
    async def _crawl_yahoo_tw_stock_news(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """
        從 Yahoo 台灣股市爬取個股相關新聞
        URL: https://tw.stock.yahoo.com/quote/{stock_code}.TW/news
        """
        news_list = []
        url = f"https://tw.stock.yahoo.com/quote/{stock_code}.TW/news"
        
        try:
            session = await self._get_session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-TW,zh;q=0.9',
            }
            
            async with session.get(url, timeout=15, headers=headers) as response:
                if response.status != 200:
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 找新聞標題 (h3 標籤)
                news_items = soup.find_all('h3')
                
                for item in news_items[:limit]:
                    link = item.find('a')
                    if link:
                        title = link.get_text(strip=True)
                        if title and len(title) > 8:
                            href = link.get('href', '')
                            if not href.startswith('http'):
                                href = f"https://tw.stock.yahoo.com{href}"
                            
                            news_list.append({
                                "title": title,
                                "date": datetime.now().strftime('%Y/%m/%d'),
                                "source": "Yahoo 台股",
                                "url": href,
                                "sentiment": self._analyze_sentiment(title),
                                "summary": "",
                                "impact": "medium"
                            })
                        
        except Exception as e:
            logger.error(f"Yahoo 台股爬蟲失敗 (股票: {stock_code}): {e}")
        
        return news_list
    
    async def get_stock_news_page(self, stock_code: str, limit: int = 20) -> List[Dict]:
        """
        從專門的新聞頁面取得更多新聞
        URL: https://www.wantgoo.com/stock/{stock_code}/news
        
        Args:
            stock_code: 股票代碼
            limit: 最大新聞數量
            
        Returns:
            新聞列表
        """
        news_list = []
        url = f"{self.BASE_URL}/stock/{stock_code}/news"
        
        try:
            session = await self._get_session()
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    logger.warning(f"Wantgoo 新聞頁返回狀態碼: {response.status}")
                    return news_list
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 新聞頁使用 a.news-link 和 h3
                news_links = soup.find_all('a', class_='news-link')
                
                for item in news_links[:limit]:
                    try:
                        title_elem = item.find('h3')
                        title = title_elem.get_text(strip=True) if title_elem else ""
                        
                        time_elem = item.find('time')
                        date_str = time_elem.get_text(strip=True) if time_elem else ""
                        
                        href = item.get('href', '')
                        if href and not href.startswith('http'):
                            href = f"{self.BASE_URL}{href}"
                        
                        if title:
                            news_list.append({
                                "title": title,
                                "date": date_str,
                                "source": "wantgoo",
                                "url": href,
                                "sentiment": self._analyze_sentiment(title),
                                "summary": "",
                                "impact": "medium"
                            })
                    except Exception as e:
                        continue
                
                logger.info(f"Wantgoo 新聞頁爬取 {len(news_list)} 則 (股票: {stock_code})")
                
        except Exception as e:
            logger.error(f"爬取 Wantgoo 新聞頁失敗: {e}")
        
        return news_list
    
    def _analyze_sentiment(self, title: str) -> str:
        """
        分析新聞標題情緒
        
        Returns:
            'positive', 'negative', 或 'neutral'
        """
        positive_keywords = [
            "大漲", "創新高", "突破", "利多", "買超", "營收成長",
            "獲利創高", "法人看好", "目標價上調", "強勢", "爆量",
            "外資買", "投信買", "主力進場", "多頭", "籌碼集中",
            "開高", "收紅", "反彈", "上漲", "年增", "月增"
        ]
        
        negative_keywords = [
            "大跌", "創新低", "跌破", "利空", "賣超", "營收衰退",
            "獲利下滑", "目標價下調", "弱勢", "爆量下殺",
            "外資賣", "投信賣", "主力出場", "空頭", "籌碼鬆動",
            "開低", "收黑", "下跌", "年減", "月減", "警示", "處置"
        ]
        
        positive_count = sum(1 for kw in positive_keywords if kw in title)
        negative_count = sum(1 for kw in negative_keywords if kw in title)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"


# 全域實例
wantgoo_crawler = WantgooCrawler()


# 便捷函數
async def get_wantgoo_news(stock_code: str, limit: int = 10) -> List[Dict]:
    """取得 Wantgoo 個股新聞"""
    return await wantgoo_crawler.get_stock_news(stock_code, limit)


async def get_wantgoo_news_full(stock_code: str, limit: int = 20) -> List[Dict]:
    """取得 Wantgoo 個股新聞 (完整頁面)"""
    # 先從概覽頁取得
    news = await wantgoo_crawler.get_stock_news(stock_code, limit)
    
    # 如果不夠，從新聞頁補充
    if len(news) < limit:
        more_news = await wantgoo_crawler.get_stock_news_page(stock_code, limit - len(news))
        news.extend(more_news)
    
    return news[:limit]
