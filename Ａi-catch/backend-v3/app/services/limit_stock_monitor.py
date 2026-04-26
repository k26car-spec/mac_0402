"""
漲跌停股票自動監控服務 (修正版)
使用證交所新版 API 抓取當日漲停、跌停股票

功能：
1. 自動抓取當日漲停/跌停股票
2. 分析產業連動效應
3. 找出潛在機會股
"""

import aiohttp
import asyncio
import ssl
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json

logger = logging.getLogger(__name__)


class LimitStockMonitor:
    """漲跌停股票監控服務"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = None
        self.cache_ttl = 300  # 快取5分鐘
        
    def _get_ssl_context(self):
        """建立不驗證 SSL 的連線"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
        
    async def fetch_limit_stocks(self, force_refresh: bool = False) -> Dict:
        """
        抓取當日漲停/跌停股票
        
        Returns:
            包含漲停股、跌停股列表的字典
        """
        now = datetime.now()
        
        # 檢查快取
        if not force_refresh and self.cache_time:
            if (now - self.cache_time).seconds < self.cache_ttl:
                return self.cache
        
        result = {
            'date': now.strftime('%Y-%m-%d'),
            'updateTime': now.strftime('%H:%M:%S'),
            'limitUp': [],
            'limitDown': [],
            'nearLimitUp': [],
            'source': 'twse+tpex',
            'success': True,
        }
        
        try:
            # 1. 從證交所抓取上市股票
            twse_data = await self._fetch_from_twse_new()
            if twse_data:
                result['limitUp'].extend(twse_data.get('limitUp', []))
                result['limitDown'].extend(twse_data.get('limitDown', []))
                result['nearLimitUp'].extend(twse_data.get('nearLimitUp', []))
            
            # 2. 從櫃買中心抓取上櫃股票
            tpex_data = await self._fetch_from_tpex()
            if tpex_data:
                result['limitUp'].extend(tpex_data.get('limitUp', []))
                result['limitDown'].extend(tpex_data.get('limitDown', []))
            
            # 統計
            result['stats'] = {
                'limitUpCount': len(result['limitUp']),
                'limitDownCount': len(result['limitDown']),
                'nearLimitUpCount': len(result['nearLimitUp']),
            }
            
            # 更新快取
            self.cache = result
            self.cache_time = now
            
        except Exception as e:
            logger.error(f"抓取漲跌停股失敗: {e}")
            result['success'] = False
            result['error'] = str(e)
            
        return result
    
    async def _fetch_from_twse_new(self) -> Optional[Dict]:
        """從證交所新版 API 抓取漲跌停股（上市）"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={today}&type=ALL&response=json"
            
            connector = aiohttp.TCPConnector(ssl=self._get_ssl_context())
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }) as resp:
                    if resp.status != 200:
                        logger.warning(f"TWSE API 返回非200狀態碼: {resp.status}，嘗試備用方案")
                        return await self._fetch_twse_via_yfinance()
                    
                    try:
                        data = await resp.json()
                    except Exception as e:
                        logger.warning(f"TWSE API JSON 解析失敗: {e}，嘗試備用方案")
                        return await self._fetch_twse_via_yfinance()
                    
                    if data.get('stat') != 'OK':
                        logger.warning(f"TWSE API 返回非 OK 狀態，嘗試備用方案")
                        return await self._fetch_twse_via_yfinance()
                    
                    # 找到每日收盤行情表格
                    tables = data.get('tables', [])
                    stock_table = None
                    for table in tables:
                        if '每日收盤行情' in table.get('title', ''):
                            stock_table = table
                            break
                    
                    if not stock_table:
                        logger.warning("找不到每日收盤行情表格，嘗試備用方案")
                        return await self._fetch_twse_via_yfinance()
                    
                    result = {'limitUp': [], 'limitDown': [], 'nearLimitUp': []}
                    
                    for row in stock_table.get('data', []):
                        try:
                            code = row[0].strip()
                            name = row[1].strip()
                            
                            # 只處理4位數股票代碼
                            if not code.isdigit() or len(code) != 4:
                                continue
                            
                            close_str = row[8].replace(',', '').strip()
                            change_str = row[10].replace(',', '').strip()
                            
                            if close_str == '--' or change_str == '--' or not close_str:
                                continue
                            
                            close = float(close_str)
                            change = float(change_str)
                            
                            if close <= 0:
                                continue
                            
                            prev_close = close - change
                            if prev_close > 0:
                                change_pct = (change / prev_close) * 100
                                
                                stock_info = {
                                    'code': code,
                                    'name': name,
                                    'close': close,
                                    'change': change,
                                    'changePct': round(change_pct, 2),
                                    'market': 'TWSE',
                                }
                                
                                if change_pct >= 9.5:
                                    result['limitUp'].append(stock_info)
                                elif change_pct >= 8.0:
                                    result['nearLimitUp'].append(stock_info)
                                elif change_pct <= -9.5:
                                    result['limitDown'].append(stock_info)
                                    
                        except (ValueError, IndexError):
                            continue
                    
                    # 如果沒有抓到任何漲停股，嘗試備用方案
                    if len(result['limitUp']) == 0 and len(result['limitDown']) == 0:
                        logger.info("TWSE API 沒有返回漲跌停股，嘗試 yfinance 備用方案")
                        return await self._fetch_twse_via_yfinance()
                    
                    return result
                    
        except Exception as e:
            logger.warning(f"TWSE API 抓取失敗: {e}，嘗試備用方案")
            return await self._fetch_twse_via_yfinance()
    
    async def _fetch_twse_via_yfinance(self) -> Optional[Dict]:
        """使用 yfinance 作為備用方案抓取上市漲停股"""
        try:
            import yfinance as yf
            
            # 常見的上市股票代碼（熱門股、權值股等）
            tw_stocks = [
                # 權值股
                '2330', '2317', '2454', '2303', '2308', '2412', '2882', '2881',
                '2891', '2886', '1301', '1303', '2002', '2912', '3008', '2382',
                '2357', '3711', '2395', '2379', '6505', '2880', '2884', '5880',
                '2892', '1216', '2609', '2603', '2615', '3037', '2327',
                '2377', '3034', '2301', '2345', '6669', '3017', '2618', '2610',
                # 記憶體/半導體
                '2337', '2408', '3443', '6239', '3661', '3529', '2449',
                '2388', '3035', '6415', '5274', '6414', '3653', '2458',
                # 電子代工
                '3706', '3231', '2312', '2324', '2353', '2356', '3481',
                '2409', '2474', '3023', '2385',
                # 金融
                '2883', '2885', '2887', '2888', '2889', '2890', '5876',
                # 傳產
                '1101', '1102', '1326', '1402', '2105', '2201', '2207', '2227',
                '2801', '2834', '9904', '9921', '1590', '4938', '6176', '6285', '8046',
            ]
            
            result = {'limitUp': [], 'limitDown': [], 'nearLimitUp': []}
            
            # 股票名稱對照表
            stock_names = {
                '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2303': '聯電',
                '2308': '台達電', '2412': '中華電', '2882': '國泰金', '2881': '富邦金',
                '2337': '旺宏', '2891': '中信金', '2886': '兆豐金', '1301': '台塑',
                '2408': '南亞科', '3443': '創意', '6239': '力成', '3661': '世芯',
                '2327': '國巨', '3037': '欣興', '2609': '陽明', '2603': '長榮',
                '2615': '萬海', '3034': '聯詠', '2377': '微星', '3017': '奇鋐',
                '6669': '緯穎', '2345': '智邦', '2618': '長榮航', '2610': '華航',
            }
            
            logger.info(f"使用 yfinance 檢查 {len(tw_stocks)} 檔上市股票...")
            
            for code in tw_stocks:
                try:
                    ticker = yf.Ticker(f'{code}.TW')
                    hist = ticker.history(period='2d')
                    
                    if len(hist) >= 2:
                        today_close = float(hist['Close'].iloc[-1])
                        yesterday_close = float(hist['Close'].iloc[-2])
                        change = today_close - yesterday_close
                        change_pct = (change / yesterday_close) * 100
                        
                        stock_info = {
                            'code': code,
                            'name': stock_names.get(code, code),
                            'close': round(today_close, 2),
                            'change': round(change, 2),
                            'changePct': round(change_pct, 2),
                            'market': 'TWSE',
                        }
                        
                        if change_pct >= 9.5:
                            result['limitUp'].append(stock_info)
                            logger.info(f"發現上市漲停: {code} {stock_names.get(code, '')} +{change_pct:.2f}%")
                        elif change_pct >= 8.0:
                            result['nearLimitUp'].append(stock_info)
                        elif change_pct <= -9.5:
                            result['limitDown'].append(stock_info)
                            logger.info(f"發現上市跌停: {code} {stock_names.get(code, '')} {change_pct:.2f}%")
                            
                except Exception as e:
                    # 單個股票抓取失敗不中斷整個流程
                    continue
            
            logger.info(f"yfinance 備用方案: 找到 {len(result['limitUp'])} 檔上市漲停，{len(result['limitDown'])} 檔跌停")
            return result
            
        except Exception as e:
            logger.error(f"yfinance 備用方案失敗: {e}")
            return None
    
    async def _fetch_from_tpex(self) -> Optional[Dict]:
        """從櫃買中心抓取上櫃股漲跌停"""
        try:
            today = datetime.now()
            date_str = f"{today.year - 1911}/{today.month:02d}/{today.day:02d}"
            # 使用每日收盤行情 API
            url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&d={date_str}"
            
            connector = aiohttp.TCPConnector(ssl=self._get_ssl_context())
            timeout = aiohttp.ClientTimeout(total=20)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    result = {'limitUp': [], 'limitDown': []}
                    
                    # 找到主要收盤資料表格
                    tables = data.get('tables', [])
                    stock_table = None
                    for table in tables:
                        if 'data' in table and len(table.get('data', [])) > 100:
                            stock_table = table
                            break
                    
                    if not stock_table:
                        return None
                    
                    for row in stock_table.get('data', []):
                        try:
                            code = str(row[0]).strip()
                            name = str(row[1]).strip()
                            close_str = str(row[2]).replace(',', '').strip()
                            change_str = str(row[3]).replace(',', '').strip()
                            
                            if not code or close_str == '--' or change_str == '--':
                                continue
                            
                            # 只處理4位數股票代碼（排除權證等）
                            if not code.isdigit() or len(code) != 4:
                                continue
                            
                            close = float(close_str)
                            change = float(change_str)
                            
                            prev_close = close - change
                            if prev_close > 0:
                                change_pct = (change / prev_close) * 100
                                
                                stock_info = {
                                    'code': code,
                                    'name': name,
                                    'close': close,
                                    'change': change,
                                    'changePct': round(change_pct, 2),
                                    'market': 'OTC',
                                }
                                
                                if change_pct >= 9.5:
                                    result['limitUp'].append(stock_info)
                                elif change_pct <= -9.5:
                                    result['limitDown'].append(stock_info)
                                    
                        except (ValueError, IndexError):
                            continue
                    
                    return result
                    
        except Exception as e:
            logger.warning(f"TPEX API 抓取失敗: {e}")
            return None
    
    async def get_daily_momentum_report(self) -> Dict:
        """
        生成每日動能報告
        
        包含：漲停股分析、產業連動、機會股建議、相關新聞
        """
        from app.services.stock_momentum_service import stock_momentum_service
        
        # 抓取漲停股
        limit_data = await self.fetch_limit_stocks()
        
        if not limit_data.get('success'):
            return {
                'success': False,
                'error': limit_data.get('error', '無法取得資料'),
            }
        
        # 取得漲停股代碼和名稱
        limit_up_stocks = limit_data.get('limitUp', [])
        limit_up_codes = [s['code'] for s in limit_up_stocks]
        limit_up_names = [s['name'] for s in limit_up_stocks]
        
        # 分析產業連動
        if limit_up_codes:
            analysis = await stock_momentum_service.analyze_limit_up_stocks(limit_up_codes)
        else:
            analysis = {'industryBreakdown': {}, 'chainReaction': [], 'hiddenOpportunities': []}
        
        # 獲取漲停股相關新聞
        related_news = await self._fetch_limit_up_news(limit_up_codes, limit_up_names)
        
        return {
            'success': True,
            'date': limit_data.get('date'),
            'updateTime': limit_data.get('updateTime'),
            'source': limit_data.get('source'),
            'summary': {
                'limitUpCount': limit_data['stats']['limitUpCount'],
                'limitDownCount': limit_data['stats']['limitDownCount'],
                'nearLimitUpCount': limit_data['stats']['nearLimitUpCount'],
            },
            'limitUp': limit_data.get('limitUp', []),
            'limitDown': limit_data.get('limitDown', []),
            'nearLimitUp': limit_data.get('nearLimitUp', []),
            'industryAnalysis': analysis.get('industryBreakdown', {}),
            'chainReaction': analysis.get('chainReaction', []),
            'opportunities': analysis.get('hiddenOpportunities', [])[:10],
            'relatedNews': related_news,
        }
    
    async def _fetch_limit_up_news(self, codes: list, names: list) -> List[Dict]:
        """
        獲取漲停股相關新聞
        
        從 CMoney、Yahoo 等來源抓取與漲停股相關的新聞
        """
        related_news = []
        
        try:
            # 從 CMoney 獲取新聞
            cmoney_news = await self._fetch_cmoney_news()
            
            # 從 Yahoo 股市獲取新聞
            yahoo_news = await self._fetch_yahoo_stock_news()
            
            # 合併所有新聞
            all_news = cmoney_news + yahoo_news
            
            # 篩選與漲停股相關的新聞
            for news in all_news:
                title = news.get('title', '')
                
                # 檢查是否包含漲停股代碼或名稱
                is_related = False
                related_stocks = []
                
                for code, name in zip(codes, names):
                    if code in title or name in title:
                        is_related = True
                        related_stocks.append({'code': code, 'name': name})
                
                # 也檢查是否有「漲停」關鍵字
                if '漲停' in title or '強攻' in title or '衝高' in title:
                    is_related = True
                
                if is_related:
                    news['relatedStocks'] = related_stocks
                    related_news.append(news)
            
            # 按時間排序，最新的在前
            related_news.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            logger.info(f"找到 {len(related_news)} 則漲停股相關新聞")
            
        except Exception as e:
            logger.warning(f"獲取漲停股新聞失敗: {e}")
        
        return related_news[:20]  # 最多返回 20 則
    
    async def _fetch_cmoney_news(self) -> List[Dict]:
        """從 CMoney 抓取台股新聞"""
        news_list = []
        seen_titles = set()
        
        try:
            url = "https://cmnews.com.tw/twstock/twstock_news"
            
            connector = aiohttp.TCPConnector(ssl=self._get_ssl_context())
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }) as resp:
                    if resp.status != 200:
                        logger.warning(f"CMoney 回應狀態碼: {resp.status}")
                        return []
                    
                    html = await resp.text()
                    
                    import re
                    
                    # 方式1: 抓取所有【即時新聞】開頭的標題
                    pattern1 = r'【即時新聞】([^<「」]{10,80})'
                    matches1 = re.findall(pattern1, html)
                    
                    for title in matches1:
                        title = title.strip()
                        # 清理標題（去除多餘的文字）
                        title = re.sub(r'文章頁.*$', '', title)
                        title = re.sub(r'」$', '', title)
                        title = f"【即時新聞】{title}"
                        
                        if title not in seen_titles and len(title) > 15:
                            seen_titles.add(title)
                            news_list.append({
                                'title': title,
                                'url': url,
                                'source': 'CMoney',
                                'timestamp': datetime.now().isoformat(),
                            })
                    
                    # 方式2: 抓取含有漲停、強攻等熱門關鍵字的標題
                    pattern2 = r'>([^<]{5,80}(?:漲停|強攻|飆漲|大漲|衝高|暴漲|噴出)[^<]{0,50})<'
                    matches2 = re.findall(pattern2, html)
                    
                    for title in matches2:
                        title = title.strip()
                        # 清理標題
                        title = re.sub(r'^前往', '', title)  # 移除開頭的「前往」
                        title = re.sub(r'文章頁.*$', '', title)
                        title = title.strip()
                        
                        # 確保不是重複的 (用簡化版本比較)
                        simplified = title.replace('【即時新聞】', '')
                        if simplified not in [t.replace('【即時新聞】', '') for t in seen_titles] and len(title) > 10:
                            seen_titles.add(title)
                            news_list.append({
                                'title': title,
                                'url': url,
                                'source': 'CMoney',
                                'timestamp': datetime.now().isoformat(),
                            })
                    
                    logger.info(f"CMoney 抓取到 {len(news_list)} 則新聞")
                    
        except Exception as e:
            logger.warning(f"CMoney 新聞抓取失敗: {e}")
        
        return news_list[:20]
    
    async def _fetch_yahoo_stock_news(self) -> List[Dict]:
        """從 Yahoo 股市抓取台股新聞"""
        news_list = []
        
        try:
            url = "https://tw.stock.yahoo.com/news/"
            
            connector = aiohttp.TCPConnector(ssl=self._get_ssl_context())
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }) as resp:
                    if resp.status != 200:
                        return []
                    
                    html = await resp.text()
                    
                    import re
                    
                    # Yahoo 股市新聞連結格式
                    pattern = r'<a[^>]*href="(https://tw\.stock\.yahoo\.com/news/[^"]+)"[^>]*>.*?<h3[^>]*>([^<]+)</h3>'
                    matches = re.findall(pattern, html, re.DOTALL)
                    
                    for href, title in matches[:15]:
                        title = title.strip()
                        if title:
                            news_list.append({
                                'title': title,
                                'url': href,
                                'source': 'Yahoo股市',
                                'timestamp': datetime.now().isoformat(),
                            })
                    
                    # 備用模式
                    if not news_list:
                        pattern2 = r'<a[^>]*href="(/news/[^"]+)"[^>]*[^>]*>([^<]{10,80})</a>'
                        matches2 = re.findall(pattern2, html)
                        
                        for href, title in matches2[:15]:
                            title = title.strip()
                            if title and len(title) > 10:
                                news_list.append({
                                    'title': title,
                                    'url': f"https://tw.stock.yahoo.com{href}",
                                    'source': 'Yahoo股市',
                                    'timestamp': datetime.now().isoformat(),
                                })
                    
        except Exception as e:
            logger.warning(f"Yahoo 股市新聞抓取失敗: {e}")
        
        return news_list


# 創建服務實例
limit_stock_monitor = LimitStockMonitor()

