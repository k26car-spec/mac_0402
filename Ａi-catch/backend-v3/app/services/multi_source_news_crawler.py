"""
多源新聞爬蟲
整合 TTV 台視財經、工商時報等新聞來源
"""
import requests
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 請求 Header
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
}


class MultiSourceNewsCrawler:
    """多源新聞爬蟲"""
    
    def __init__(self):
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 1800  # 30 分鐘
    
    def _get_cache(self, source: str) -> Optional[List[Dict]]:
        """取得快取"""
        if source in self._cache and source in self._cache_time:
            elapsed = (datetime.now() - self._cache_time[source]).seconds
            if elapsed < self._cache_ttl:
                return self._cache[source]
        return None
    
    def _set_cache(self, source: str, news: List[Dict]):
        """設定快取"""
        self._cache[source] = news
        self._cache_time[source] = datetime.now()
    
    def crawl_ttv_finance(self, force_refresh: bool = False) -> List[Dict]:
        """
        爬取台視財經新聞
        來源: https://www.ttv.com.tw/finance/
        """
        source_name = "台視財經"
        source_url = "https://www.ttv.com.tw/finance/"
        
        if not force_refresh:
            cached = self._get_cache('ttv')
            if cached:
                logger.info(f"使用 {source_name} 快取 ({len(cached)} 則)")
                return cached
        
        news_list = []
        
        try:
            response = requests.get(source_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"{source_name} 請求失敗: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 找所有新聞連結
            links = soup.find_all('a', href=True)
            seen_titles = set()
            
            for link in links:
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                # 過濾有效新聞連結
                if 'finance/view' in href and title and len(title) > 10:
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)
                    
                    # 解析日期 (從 URL 中提取，格式如 12202526...)
                    date_str = self._extract_date_from_ttv_url(href)
                    
                    # 完整 URL
                    full_url = href if href.startswith('http') else f"https://www.ttv.com.tw{href}"
                    
                    news_list.append({
                        'id': f"ttv_{hash(title) % 100000}",
                        'title': title,
                        'url': full_url,
                        'source': source_name,
                        'sourceType': 'ttv',
                        'date': date_str,
                        'industry': self._detect_industry(title),
                        'sentiment': self._analyze_sentiment(title),
                    })
            
            # 去重並限制數量
            news_list = news_list[:30]
            
            self._set_cache('ttv', news_list)
            logger.info(f"✅ 取得 {source_name} 新聞 {len(news_list)} 則")
            
        except Exception as e:
            logger.error(f"{source_name} 爬取失敗: {e}")
        
        return news_list
    
    def crawl_cmoney(self, force_refresh: bool = False) -> List[Dict]:
        """
        爬取 CMoney 投資網誌 台股新聞快訊
        來源: https://cmnews.com.tw/twstock/twstock_news
        """
        source_name = "CMoney新聞"
        source_url = "https://cmnews.com.tw/twstock/twstock_news"
        
        if not force_refresh:
            cached = self._get_cache('cmoney')
            if cached:
                logger.info(f"使用 {source_name} 快取 ({len(cached)} 則)")
                return cached
        
        news_list = []
        seen_titles = set()
        
        try:
            response = requests.get(source_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"{source_name} 請求失敗: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 找所有新聞文章連結 - CMoney 文章連結格式: /article/...
            links = soup.find_all('a', href=re.compile(r'/article/'))
            
            for link in links:
                href = link.get('href', '')
                
                # 取得連結文字
                raw_title = link.get_text(strip=True)
                
                # 過濾無效標題
                if not raw_title or len(raw_title) < 10:
                    continue
                
                # 處理「前往【即時新聞】...文章頁」格式
                # 提取中間的新聞標題部分
                clean_title = raw_title
                
                # 移除「前往」前綴
                if clean_title.startswith('前往'):
                    clean_title = clean_title[2:]
                
                # 移除「文章頁」後綴
                if clean_title.endswith('文章頁'):
                    clean_title = clean_title[:-3]
                
                # 移除【即時新聞】等標籤
                clean_title = re.sub(r'^【[^】]+】', '', clean_title).strip()
                
                # 過濾掉 NA 或太短的標題
                if not clean_title or len(clean_title) < 5 or clean_title == 'NA':
                    continue
                
                # 去重
                if clean_title in seen_titles:
                    continue
                seen_titles.add(clean_title)
                
                # 完整 URL
                full_url = href if href.startswith('http') else f"https://cmnews.com.tw{href}"
                
                # 從標題提取股票代碼 (格式: 股票名(代碼))
                stocks = []
                stock_matches = re.findall(r'([^\(]+)\((\d{4})\)', raw_title)
                for name, code in stock_matches:
                    stocks.append(code)
                
                # 也使用關鍵詞對照表來提取股票
                additional_stocks = self._extract_stock_codes(clean_title)
                for code in additional_stocks:
                    if code not in stocks:
                        stocks.append(code)
                
                news_list.append({
                    'id': f"cmoney_{hash(clean_title) % 100000}",
                    'title': clean_title,
                    'url': full_url,
                    'source': source_name,
                    'sourceType': 'cmoney',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'industry': self._detect_industry(clean_title),
                    'sentiment': self._analyze_sentiment(clean_title),
                    'stocks': stocks,
                })
            
            # 限制數量
            news_list = news_list[:50]
            
            self._set_cache('cmoney', news_list)
            logger.info(f"✅ 取得 {source_name} 新聞 {len(news_list)} 則")
            
        except Exception as e:
            logger.error(f"{source_name} 爬取失敗: {e}")
        
        return news_list
    
    def crawl_udn(self, force_refresh: bool = False) -> List[Dict]:
        """
        爬取經濟日報熱門新聞排行榜
        來源: https://money.udn.com/rank/pv/1001/0 (經濟日報即時熱門)
        """
        source_name = "經濟日報"
        # 使用熱門排行榜頁面
        source_url = "https://money.udn.com/rank/pv/1001/0"
        
        if not force_refresh:
            cached = self._get_cache('udn')
            if cached:
                logger.info(f"使用 {source_name} 快取 ({len(cached)} 則)")
                return cached
        
        news_list = []
        seen_titles = set()
        
        try:
            response = requests.get(source_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"{source_name} 請求失敗: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 找所有新聞文章連結
            # UDN 格式: <a href="https://money.udn.com/money/story/5607/9227014?from=...">
            links = soup.find_all('a', href=re.compile(r'money\.udn\.com/money/story/\d+/\d+'))
            
            for link in links:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 過濾無效標題
                if not title or len(title) < 8:
                    continue
                
                # 過濾導航連結
                skip_titles = ['看更多', '最新', '最熱', '閱讀更多', '編輯精選', '服務']
                if any(skip in title for skip in skip_titles):
                    continue
                
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                # 清理 URL (移除追蹤參數)
                clean_url = href.split('?')[0] if '?' in href else href
                if not clean_url.startswith('http'):
                    clean_url = f"https://money.udn.com{clean_url}"
                
                # 嘗試從 story ID 推測日期 (新的 story ID 較大)
                date_str = datetime.now().strftime('%Y-%m-%d')
                
                news_list.append({
                    'id': f"udn_{hash(title) % 100000}",
                    'title': title,
                    'url': clean_url,
                    'source': source_name,
                    'sourceType': 'udn',
                    'date': date_str,
                    'industry': self._detect_industry(title),
                    'sentiment': self._analyze_sentiment(title),
                    'stocks': self._extract_stock_codes(title),
                })
            
            # 限制數量
            news_list = news_list[:50]
            
            self._set_cache('udn', news_list)
            logger.info(f"✅ 取得 {source_name} 新聞 {len(news_list)} 則")
            
        except Exception as e:
            logger.error(f"{source_name} 爬取失敗: {e}")
        
        return news_list
    
    def crawl_technews(self, force_refresh: bool = False, pages: int = 2) -> List[Dict]:
        """
        爬取科技新報 TechNews
        來源: https://technews.tw/category/cutting-edge/
        支援多頁爬取
        """
        source_name = "科技新報"
        base_url = "https://technews.tw/category/cutting-edge"
        
        if not force_refresh:
            cached = self._get_cache('technews')
            if cached:
                logger.info(f"使用 {source_name} 快取 ({len(cached)} 則)")
                return cached
        
        news_list = []
        seen_titles = set()
        
        try:
            # 爬取多頁
            for page in range(1, pages + 1):
                if page == 1:
                    url = base_url
                else:
                    url = f"{base_url}/page/{page}/"
                
                logger.info(f"爬取 {source_name} 第 {page} 頁: {url}")
                
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.encoding = 'utf-8'
                
                if response.status_code != 200:
                    logger.error(f"{source_name} 第 {page} 頁請求失敗: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # TechNews 文章結構
                # 找所有文章標題連結
                articles = soup.find_all('article')
                
                for article in articles:
                    # 找標題連結 - TechNews 使用 h1.entry-title > a
                    title_elem = article.find('h1', class_='entry-title') or \
                                 article.find('h2', class_='entry-title')
                    
                    if title_elem:
                        a_tag = title_elem.find('a')
                        if a_tag:
                            title = a_tag.get_text(strip=True)
                            href = a_tag.get('href', '')
                        else:
                            continue
                    else:
                        # 備用：找任何 h1/h2 裡的連結
                        for h_tag in article.find_all(['h1', 'h2']):
                            a_tag = h_tag.find('a')
                            if a_tag and a_tag.get('href'):
                                title = a_tag.get_text(strip=True)
                                href = a_tag.get('href', '')
                                break
                        else:
                            continue
                    
                    # 過濾無效標題
                    if not title or len(title) < 8:
                        continue
                    
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)
                    
                    # 提取日期
                    date_elem = article.find('time')
                    if date_elem and date_elem.get('datetime'):
                        date_str = date_elem['datetime'][:10]
                    else:
                        date_str = datetime.now().strftime('%Y-%m-%d')
                    
                    # 提取摘要
                    excerpt_elem = article.find('p', class_='entry-content-excerpt') or \
                                   article.find('div', class_='entry-content')
                    excerpt = excerpt_elem.get_text(strip=True)[:200] if excerpt_elem else ''
                    
                    news_list.append({
                        'id': f"technews_{hash(title) % 100000}",
                        'title': title,
                        'url': href,
                        'source': source_name,
                        'sourceType': 'technews',
                        'date': date_str,
                        'excerpt': excerpt,
                        'industry': self._detect_industry(title),
                        'sentiment': self._analyze_sentiment(title),
                        'stocks': self._extract_stock_codes(title),
                    })
                
                # 頁面間延遲
                import time
                time.sleep(0.5)
            
            # 限制數量
            news_list = news_list[:60]
            
            self._set_cache('technews', news_list)
            logger.info(f"✅ 取得 {source_name} 新聞 {len(news_list)} 則 ({pages} 頁)")
            
        except Exception as e:
            logger.error(f"{source_name} 爬取失敗: {e}")
        
        return news_list
    
    def _extract_stock_codes(self, title: str) -> List[str]:
        """從標題中提取股票代碼"""
        stocks = []
        
        # 關鍵詞對照表 (擴展版)
        keyword_map = {
            # 半導體
            '台積電': '2330', '台積': '2330', 'TSMC': '2330',
            '聯發科': '2454', '聯電': '2303', '日月光': '3711',
            '力成': '6239', '世芯': '3661', '創意': '3443',
            '瑞昱': '2379', '聯詠': '3034', '群聯': '8299',
            '華邦電': '2344', '南亞科': '2408', '力積電': '6770',
            '旺宏': '2337', '矽品': '2325', '威盛': '2388',
            # 測試/封裝
            '欣銓': '3264', '京元電': '2449', '南茂': '8150', 
            '穎崴': '6515', '雍智': '6955', '精測': '6510',
            # AI / 伺服器
            '廣達': '2382', '緯創': '3231', '緯穎': '6669',
            '技嘉': '2376', '微星': '2377', '華碩': '2357',
            '仁寶': '2324', '英業達': '2356', '神達': '3706',
            '鴻海': '2317', '和碩': '4938',
            # 零組件
            '國巨': '2327', '欣興': '3037', '台達電': '2308',
            '雙鴻': '3324', '奇鋐': '3017', '臻鼎': '4958',
            '大立光': '3008', '玉晶光': '3406',
            # 面板/光電
            '群創': '3481', '友達': '2409', '彩晶': '6116',
            '瀚宇彩晶': '6116', '元太': '8069', '達興': '5234',
            '榮創': '3455', '凌巨': '8105', '南電': '8046',
            # 被動元件
            '華新科': '2492', '奇力新': '2456', '大毅': '2478',
            '禾伸堂': '3026', '凱美': '2375',
            # 金融
            '中信金': '2891', '富邦金': '2881', '國泰金': '2882',
            '兆豐金': '2886', '玉山金': '2884', '台新金': '2887',
            '第一金': '2892', '華南金': '2880', '開發金': '2883',
            # 航運
            '長榮': '2603', '陽明': '2609', '萬海': '2615',
            '長榮航': '2618', '華航': '2610',
            # 營建 / 無塵室
            '亞翔': '6139', '漢唐': '2404', '帆宣': '6196',
            '聖暉': '5765', '千附': '8383',
            # 半導體材料
            '中砂': '1560', '環球晶': '6488', '合晶': '6182',
            # 汽車
            '和泰車': '2207', '裕隆': '2201', '東陽': '1319',
            # PCB
            '景碩': '3189', '南亞電': '8046', '燿華': '2367',
            '嘉聯益': '6153', '華通': '2313',
            # 光通訊/矽光子
            '聯鈞': '3450', '光聖': '6442', '眾達': '4977',
            '統新': '6426', '聯亞': '3081',
        }
        
        for keyword, code in keyword_map.items():
            if keyword in title:
                stocks.append(code)
        
        # 匹配 4 位數股票代碼
        code_matches = re.findall(r'\b(\d{4})\b', title)
        for code in code_matches:
            if code.startswith(('1', '2', '3', '4', '5', '6', '8', '9')) and code not in stocks:
                stocks.append(code)
        
        return stocks
    
    def fetch_news_content(self, url: str) -> str:
        """爬取新聞內容 (用於提取更多股票資訊)"""
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return ''
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 嘗試多種內容選擇器
            content_selectors = [
                'article',
                '.article-content',
                '.article-body',
                '.story-body',
                '#story-body',
                '.main-content',
            ]
            
            content = ''
            for selector in content_selectors:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text(strip=True)
                    break
            
            # 如果找不到，取所有段落
            if not content:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs[:20]])
            
            return content[:2000]  # 限制長度
            
        except Exception as e:
            logger.debug(f"爬取新聞內容失敗 {url}: {e}")
            return ''
    
    def enrich_news_with_content(self, news_item: Dict) -> Dict:
        """豐富新聞資訊：爬取內容並提取更多股票"""
        url = news_item.get('url', '')
        if not url:
            return news_item
        
        content = self.fetch_news_content(url)
        if content:
            # 從內容中提取更多股票
            content_stocks = self._extract_stock_codes(content)
            existing_stocks = news_item.get('stocks', [])
            
            # 合併股票列表（去重）
            all_stocks = list(set(existing_stocks + content_stocks))
            news_item['stocks'] = all_stocks
            news_item['content_preview'] = content[:200] + '...' if len(content) > 200 else content
        
        return news_item
    
    def crawl_all(self, force_refresh: bool = False) -> Dict[str, List[Dict]]:
        """爬取所有來源的新聞"""
        result = {
            'ttv': self.crawl_ttv_finance(force_refresh),
            'cmoney': self.crawl_cmoney(force_refresh),
            'udn': self.crawl_udn(force_refresh),
            'technews': self.crawl_technews(force_refresh),
        }
        
        # 嘗試添加口袋證券研報（可能較慢，需要 Playwright）
        try:
            from app.services.pocket_crawler import get_pocket_news
            result['pocket'] = get_pocket_news(force_refresh)
        except Exception as e:
            logger.warning(f"口袋證券研報爬取失敗: {e}")
            result['pocket'] = []
        
        return result
    
    def get_all_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得所有來源的新聞（合併）"""
        all_sources = self.crawl_all(force_refresh)
        all_news = []
        for source_news in all_sources.values():
            all_news.extend(source_news)
        
        # 依日期排序
        all_news.sort(key=lambda x: x.get('date', ''), reverse=True)
        return all_news
    
    def _extract_date_from_ttv_url(self, url: str) -> str:
        """從 TTV URL 中提取日期"""
        # URL 格式: .../view/default.asp?i=122025260859...
        # 12 = 月份 prefix, 2025 = 年, 26 = 日
        try:
            match = re.search(r'i=(\d{2})(\d{4})(\d{2})', url)
            if match:
                month = match.group(1)
                year = match.group(2)
                day = match.group(3)
                return f"{year}-{month}-{day}"
        except:
            pass
        return datetime.now().strftime('%Y-%m-%d')
    
    def _parse_date(self, date_text: str) -> Optional[str]:
        """解析日期文字"""
        try:
            # 常見格式: 2025-12-26, 2025/12/26, 12/26
            patterns = [
                (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"),
                (r'(\d{1,2})[/-](\d{1,2})', lambda m: f"{datetime.now().year}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"),
            ]
            for pattern, formatter in patterns:
                match = re.search(pattern, date_text)
                if match:
                    return formatter(match)
        except:
            pass
        return None
    
    def _detect_industry(self, title: str) -> str:
        """偵測產業分類"""
        industry_keywords = {
            '半導體': ['半導體', '晶片', '晶圓', '台積電', '聯發科', 'IC', 'DRAM', '記憶體'],
            '資通訊': ['AI', '人工智慧', '5G', '雲端', '伺服器', '資通訊', '光通訊'],
            '電動車': ['電動車', '特斯拉', '電池', '充電'],
            '金融': ['銀行', '保險', '金控', '利率', '降息', '升息'],
            '科技': ['科技', 'GPU', 'CPU', '軟體', '網路'],
            '國際': ['美股', '日股', '韓股', '美國', '日本', '歐洲', '中國', '大陸'],
        }
        
        for industry, keywords in industry_keywords.items():
            for kw in keywords:
                if kw in title:
                    return industry
        return '其他'
    
    def _analyze_sentiment(self, title: str) -> str:
        """分析情緒"""
        positive = ['漲', '爆發', '創高', '成長', '利多', '看好', '突破', '強勁', '熱銷']
        negative = ['跌', '下滑', '衰退', '利空', '風險', '警示', '憂', '減']
        
        pos_count = sum(1 for kw in positive if kw in title)
        neg_count = sum(1 for kw in negative if kw in title)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        return 'neutral'


# 全域實例
multi_source_crawler = MultiSourceNewsCrawler()


# 便捷函數
def get_ttv_news(force_refresh: bool = False) -> List[Dict]:
    """取得台視財經新聞"""
    return multi_source_crawler.crawl_ttv_finance(force_refresh)


def get_cmoney_news(force_refresh: bool = False) -> List[Dict]:
    """取得 CMoney 新聞"""
    return multi_source_crawler.crawl_cmoney(force_refresh)


def get_udn_news(force_refresh: bool = False) -> List[Dict]:
    """取得經濟日報新聞"""
    return multi_source_crawler.crawl_udn(force_refresh)


def get_technews_news(force_refresh: bool = False, pages: int = 2) -> List[Dict]:
    """取得科技新報新聞"""
    return multi_source_crawler.crawl_technews(force_refresh, pages)


def get_pocket_news(force_refresh: bool = False) -> List[Dict]:
    """取得口袋證券研報"""
    try:
        from app.services.pocket_crawler import get_pocket_news as _get_pocket
        return _get_pocket(force_refresh)
    except Exception as e:
        logger.warning(f"取得口袋證券研報失敗: {e}")
        return []


def get_all_external_news(force_refresh: bool = False) -> List[Dict]:
    """取得所有外部新聞"""
    return multi_source_crawler.get_all_news(force_refresh)
