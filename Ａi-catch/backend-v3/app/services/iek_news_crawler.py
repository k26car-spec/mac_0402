"""
IEK 產業情報網 新聞爬蟲服務
https://ieknet.iek.org.tw/member/DailyNews.aspx
"""
import requests
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IEKNewsCrawler:
    """IEK 產業情報網新聞爬蟲"""
    
    BASE_URL = "https://ieknet.iek.org.tw"
    DAILY_NEWS_URL = f"{BASE_URL}/member/DailyNews.aspx"
    
    # 產業分類對應
    INDUSTRY_MAP = {
        '1': '半導體',
        '2': '零組件及材料',
        '3': '資通訊',
        '5': '綠能與環境',
        '6': '生技醫療',
        '7': '石化材料',
        '8': '車輛',
        '9': '產經政策',
        '10': '兩岸產經',
        '11': '總體經濟',
        '13': '機械',
    }
    
    # 產業關鍵字對應股票
    INDUSTRY_STOCKS = {
        '半導體': ['2330', '2454', '2303', '3034', '2408', '6669', '3711', '2344', '2337'],
        '資通訊': ['2317', '2357', '2382', '3045', '2412', '4904', '2356'],
        '零組件及材料': ['2308', '3037', '8046', '3443', '2474', '6257'],
        '車輛': ['2207', '2201', '9941', '1319', '2227'],
        '綠能與環境': ['6443', '3576', '6244', '3023', '1513'],
        '生技醫療': ['4743', '1760', '4142', '6446', '4147'],
        '機械': ['1513', '2049', '4523', '2059'],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 1800  # 30 分鐘快取
    
    def fetch_daily_news(self, force_refresh: bool = False) -> List[Dict]:
        """
        取得每日產業新聞
        
        Returns:
            [
                {
                    'title': str,
                    'url': str,
                    'source': str,
                    'date': str,
                    'industry': str,
                    'sentiment': str
                }
            ]
        """
        # 檢查快取
        if not force_refresh and self._cache_time:
            elapsed = (datetime.now() - self._cache_time).seconds
            if elapsed < self._cache_ttl and 'all' in self._cache:
                logger.info(f"使用 IEK 新聞快取 ({len(self._cache['all'])} 則)")
                return self._cache['all']
        
        all_news = []
        
        try:
            response = self.session.get(self.DAILY_NEWS_URL, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 解析新聞連結
                news_links = soup.find_all('a', href=re.compile(r'news_more\.aspx'))
                
                for link in news_links:
                    try:
                        title = link.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue
                        
                        href = link.get('href', '')
                        if not href:
                            continue
                        
                        # 完整 URL
                        if not href.startswith('http'):
                            full_url = f"{self.BASE_URL}{href}" if href.startswith('/') else f"{self.BASE_URL}/{href}"
                        else:
                            full_url = href
                        
                        # 解析產業 ID
                        industry_match = re.search(r'indu_idno=(\d+)', href)
                        industry_id = industry_match.group(1) if industry_match else ''
                        industry = self.INDUSTRY_MAP.get(industry_id, '其他')
                        
                        # 找來源和日期 (通常在連結後面)
                        parent = link.parent
                        full_text = parent.get_text() if parent else ''
                        
                        # 解析來源
                        source = '工研院IEK'
                        source_patterns = ['工商時報', '經濟日報', '中央社', '聯合報', '中國時報']
                        for pattern in source_patterns:
                            if pattern in full_text:
                                source = pattern
                                break
                        
                        # 解析日期
                        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', full_text)
                        if date_match:
                            date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                        else:
                            date_str = datetime.now().strftime('%Y-%m-%d')
                        
                        # 判斷情緒
                        sentiment = self._analyze_sentiment(title)
                        
                        news_item = {
                            'title': title,
                            'url': full_url,
                            'source': source,
                            'date': date_str,
                            'industry': industry,
                            'sentiment': sentiment
                        }
                        
                        # 避免重複
                        if not any(n['title'] == title for n in all_news):
                            all_news.append(news_item)
                    
                    except Exception as e:
                        logger.debug(f"解析新聞項目失敗: {e}")
                        continue
                
                logger.info(f"✅ IEK 新聞爬取成功，共 {len(all_news)} 則")
            
        except Exception as e:
            logger.error(f"IEK 新聞爬取失敗: {e}")
        
        # 更新快取
        self._cache['all'] = all_news
        self._cache_time = datetime.now()
        
        return all_news
    
    def _analyze_sentiment(self, title: str) -> str:
        """分析新聞標題情緒"""
        positive_keywords = [
            '創高', '大漲', '飆升', '爆發', '利多', '突破', '成長', '增長',
            '大單', '熱銷', '擴產', '強勁', '看好', '上揚', '旺', '補',
            '加持', '商機', '贏家', '亮眼', '優於'
        ]
        negative_keywords = [
            '下跌', '暴跌', '重挫', '利空', '衰退', '虧損', '減少',
            '警告', '風險', '限制', '禁令', '危機', '黑', '跌'
        ]
        
        positive_count = sum(1 for kw in positive_keywords if kw in title)
        negative_count = sum(1 for kw in negative_keywords if kw in title)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def get_news_by_industry(self, industry: str) -> List[Dict]:
        """依產業取得新聞"""
        all_news = self.fetch_daily_news()
        return [n for n in all_news if n['industry'] == industry]
    
    def get_news_for_stock(self, stock_code: str) -> List[Dict]:
        """
        取得與股票相關的新聞
        根據股票所屬產業篩選新聞
        """
        all_news = self.fetch_daily_news()
        
        # 找出股票所屬產業
        stock_industries = []
        for industry, stocks in self.INDUSTRY_STOCKS.items():
            if stock_code in stocks:
                stock_industries.append(industry)
        
        if not stock_industries:
            # 預設返回半導體和總體經濟新聞
            stock_industries = ['半導體', '總體經濟']
        
        # 篩選相關新聞
        related_news = [
            n for n in all_news 
            if n['industry'] in stock_industries
        ]
        
        return related_news[:10]  # 最多返回10則
    
    def get_summary(self) -> Dict:
        """取得新聞摘要"""
        all_news = self.fetch_daily_news()
        
        # 統計各產業新聞數
        industry_counts = {}
        for news in all_news:
            industry = news['industry']
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
        
        # 統計情緒
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        for news in all_news:
            sentiment_counts[news['sentiment']] = sentiment_counts.get(news['sentiment'], 0) + 1
        
        return {
            'total': len(all_news),
            'cache_time': self._cache_time.isoformat() if self._cache_time else None,
            'by_industry': industry_counts,
            'by_sentiment': sentiment_counts,
            'top_headlines': [n['title'] for n in all_news[:5]]
        }


# 全域實例
iek_crawler = IEKNewsCrawler()


def get_iek_news() -> List[Dict]:
    """取得 IEK 產業新聞"""
    return iek_crawler.fetch_daily_news()


def get_iek_news_for_stock(stock_code: str) -> List[Dict]:
    """取得與股票相關的 IEK 產業新聞"""
    return iek_crawler.get_news_for_stock(stock_code)


def get_iek_news_summary() -> Dict:
    """取得 IEK 新聞摘要"""
    return iek_crawler.get_summary()
