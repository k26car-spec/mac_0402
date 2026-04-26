"""
口袋證券研究報告爬蟲
使用 Playwright 爬取動態載入的頁面
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 快取
_pocket_cache: List[Dict] = []
_pocket_cache_time: Optional[datetime] = None
_pocket_cache_ttl = 1800  # 30 分鐘


async def crawl_pocket_reports_async(force_refresh: bool = False) -> List[Dict]:
    """
    異步爬取口袋證券研究報告
    來源: https://www.pocket.tw/school/report/?main=SCHOOL
    """
    global _pocket_cache, _pocket_cache_time
    
    # 檢查快取
    if not force_refresh and _pocket_cache and _pocket_cache_time:
        elapsed = (datetime.now() - _pocket_cache_time).total_seconds()
        if elapsed < _pocket_cache_ttl:
            logger.info(f"使用口袋證券快取 ({len(_pocket_cache)} 則)")
            return _pocket_cache
    
    news_list = []
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 導航到頁面
            url = "https://www.pocket.tw/school/report/?main=SCHOOL"
            logger.info(f"爬取口袋證券研報: {url}")
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待文章載入
            await page.wait_for_selector('a[href*="/school/report/SCHOOL/"]', timeout=10000)
            
            # 使用 JavaScript 提取文章資訊
            articles = await page.evaluate('''() => {
                const articles = Array.from(document.querySelectorAll('a[href*="/school/report/SCHOOL/"]'));
                return articles.map(a => {
                    // 獲取所有 p 標籤
                    const allPs = Array.from(a.querySelectorAll('p'));
                    
                    // 過濾掉只有日期的 p 標籤（日期格式 2026/1/5）
                    const contentPs = allPs.filter(p => {
                        const text = p.innerText.trim();
                        return text.length > 10 && !/^\\d{4}\\/\\d{1,2}\\/\\d{1,2}$/.test(text);
                    });
                    
                    // 找日期 p 標籤
                    const dateP = allPs.find(p => /^\\d{4}\\/\\d{1,2}\\/\\d{1,2}$/.test(p.innerText.trim()));
                    
                    return {
                        title: contentPs[0] ? contentPs[0].innerText.trim() : null,
                        description: contentPs[1] ? contentPs[1].innerText.trim() : null,
                        date: dateP ? dateP.innerText.trim() : null,
                        url: a.href
                    };
                }).filter(x => x && x.title && x.title.length > 5);
            }''')
            
            await browser.close()
            
            # 處理提取的文章
            seen_titles = set()
            for article in articles:
                title = article.get('title', '')
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                
                # 解析日期
                date_str = article.get('date', '')
                if date_str:
                    # 格式: 2026/1/5 -> 2026-01-05
                    try:
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            date_str = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                    except:
                        date_str = datetime.now().strftime('%Y-%m-%d')
                else:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                # 提取股票代碼
                stocks = extract_stocks_from_pocket(title + ' ' + article.get('description', ''))
                
                # 分析情緒
                sentiment = analyze_pocket_sentiment(title)
                
                news_list.append({
                    'id': f"pocket_{hash(title) % 100000}",
                    'title': title,
                    'url': article.get('url', ''),
                    'source': '口袋證券',
                    'sourceType': 'pocket',
                    'date': date_str,
                    'excerpt': article.get('description', '')[:150] if article.get('description') else '',
                    'industry': detect_industry(title),
                    'sentiment': sentiment,
                    'stocks': stocks,
                })
            
            # 更新快取
            _pocket_cache = news_list
            _pocket_cache_time = datetime.now()
            
            logger.info(f"✅ 取得口袋證券研報 {len(news_list)} 則")
            
    except Exception as e:
        logger.error(f"口袋證券研報爬取失敗: {e}")
        # 如果有舊快取，返回舊快取
        if _pocket_cache:
            logger.info("使用舊快取數據")
            return _pocket_cache
    
    return news_list


def crawl_pocket_reports(force_refresh: bool = False) -> List[Dict]:
    """同步版本的爬蟲 - 在新線程中運行以避免事件循環衝突"""
    global _pocket_cache, _pocket_cache_time
    
    # 檢查快取
    if not force_refresh and _pocket_cache and _pocket_cache_time:
        elapsed = (datetime.now() - _pocket_cache_time).total_seconds()
        if elapsed < _pocket_cache_ttl:
            logger.info(f"使用口袋證券快取 ({len(_pocket_cache)} 則)")
            return _pocket_cache
    
    import concurrent.futures
    
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(crawl_pocket_reports_async(force_refresh))
            return result
        finally:
            loop.close()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        try:
            result = future.result(timeout=60)  # 60秒超時
            return result
        except concurrent.futures.TimeoutError:
            logger.error("口袋證券爬蟲超時")
            return _pocket_cache if _pocket_cache else []
        except Exception as e:
            logger.error(f"口袋證券爬蟲執行失敗: {e}")
            return _pocket_cache if _pocket_cache else []


def extract_stocks_from_pocket(text: str) -> List[str]:
    """從口袋證券研報標題/內容提取股票代碼"""
    stocks = []
    
    # 關鍵詞對照表
    keyword_map = {
        # 半導體
        '台積電': '2330', '聯發科': '2454', '聯電': '2303',
        '日月光': '3711', '力成': '6239', '世芯': '3661',
        '瑞昱': '2379', '聯詠': '3034', '群聯': '8299',
        '華邦電': '2344', '南亞科': '2408', '旺宏': '2337',
        # AI / 伺服器
        '廣達': '2382', '緯創': '3231', '緯穎': '6669',
        '技嘉': '2376', '微星': '2377', '華碩': '2357',
        '鴻海': '2317', '英業達': '2356', '神達': '3706',
        # 面板
        '群創': '3481', '友達': '2409', '彩晶': '6116', '元太': '8069',
        # 零組件
        '國巨': '2327', '欣興': '3037', '台達電': '2308',
        '雙鴻': '3324', '奇鋐': '3017', '臻鼎': '4958',
        '大立光': '3008', '玉晶光': '3406',
        # 光通訊
        '聯鈞': '3450', '波若威': '3163', '華星光': '4979',
        # 金融
        '中信金': '2891', '富邦金': '2881', '國泰金': '2882',
        '兆豐金': '2886', '玉山金': '2884',
        # 航運
        '長榮': '2603', '陽明': '2609', '萬海': '2615',
    }
    
    for keyword, code in keyword_map.items():
        if keyword in text:
            stocks.append(code)
    
    # 匹配括號內的股票代碼，如 (2330)
    code_matches = re.findall(r'\((\d{4})\)', text)
    for code in code_matches:
        if code not in stocks and code.startswith(('1', '2', '3', '4', '5', '6', '8', '9')):
            stocks.append(code)
    
    return list(set(stocks))


def analyze_pocket_sentiment(title: str) -> str:
    """分析口袋證券標題情緒"""
    positive = ['漲停', '飆漲', '噴發', '創高', '攻高', '爆發', '強勢', 
                '利多', '看好', '商機', '受惠', '成長', '擴產', '滿載']
    negative = ['跌停', '暴跌', '重挫', '利空', '下滑', '衰退', '警示']
    
    pos_count = sum(1 for kw in positive if kw in title)
    neg_count = sum(1 for kw in negative if kw in title)
    
    if pos_count > neg_count:
        return 'positive'
    elif neg_count > pos_count:
        return 'negative'
    return 'neutral'


def detect_industry(title: str) -> str:
    """偵測產業分類"""
    industry_keywords = {
        '半導體': ['半導體', '晶片', '晶圓', '台積電', 'TSMC', 'IC', '記憶體'],
        'AI': ['AI', '人工智慧', '伺服器', 'GPU', '輝達'],
        '面板': ['面板', '群創', '友達', 'LCD', 'OLED'],
        '矽光子': ['矽光子', '光通訊', 'CPO', '光模組'],
        '電動車': ['電動車', 'EV', '特斯拉', '電池'],
        '金融': ['金控', '銀行', '壽險', '升息'],
    }
    
    for industry, keywords in industry_keywords.items():
        for kw in keywords:
            if kw in title:
                return industry
    return '其他'


# 便捷函數
def get_pocket_news(force_refresh: bool = False) -> List[Dict]:
    """取得口袋證券研報新聞"""
    return crawl_pocket_reports(force_refresh)
