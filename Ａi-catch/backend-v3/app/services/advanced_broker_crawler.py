"""
進階券商爬蟲 - 突破富邦證券防護機制
支援多種反爬蟲策略：User-Agent輪替、請求頻率控制、Selenium、代理IP
"""

import requests
import time
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)


class AdvancedBrokerCrawler:
    """進階券商爬蟲 - 支援多種反爬蟲策略"""
    
    def __init__(self, use_selenium: bool = False, use_proxy: bool = False):
        """
        初始化爬蟲
        Args:
            use_selenium: 是否使用Selenium（用於JS渲染的頁面）
            use_proxy: 是否使用代理IP
        """
        self.session = None
        self.driver = None
        self.use_selenium = use_selenium
        self.use_proxy = use_proxy
        
        # 請求配置
        self.base_url = "https://fubon-ebrokerdj.fbs.com.tw"
        
        # User-Agent池（輪替使用）
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        
        # 請求間隔配置（優化：減少延遲以提速）
        self.min_delay = 1  # 最小延遲秒數 (原本 3)
        self.max_delay = 3  # 最大延遲秒數 (原本 8)
        
        # 重試配置
        self.max_retries = 3
        self.retry_delay = 5
        
        # 成功請求計數（用於自動休息）
        self.request_count = 0
        self.batch_size = 20  # 每20次請求休息一次 (原本 5)
        
    def _generate_headers(self) -> Dict:
        """生成隨機且真實的請求頭"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'identity',  # 不使用壓縮，避免解碼問題
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
        
        # 隨機添加Referer
        if random.random() > 0.5:
            headers['Referer'] = random.choice([
                'https://www.google.com/',
                'https://tw.stock.yahoo.com/',
                self.base_url
            ])
            
        return headers
    
    def _random_delay(self):
        """隨機延遲，模擬人類操作"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"延遲 {delay:.2f} 秒")
        time.sleep(delay)
        
    def _batch_rest(self):
        """批次休息（優化：增加批次大小並縮短休息時間）"""
        self.request_count += 1
        
        if self.request_count % self.batch_size == 0:
            rest_time = random.uniform(2, 5) # 原本 15-30
            logger.info(f"已完成 {self.request_count} 次請求，休息 {rest_time:.1f} 秒")
            time.sleep(rest_time)
    
    def _create_session(self):
        """創建會話並設置cookies"""
        if not self.session:
            self.session = requests.Session()
            
            # 設置初始cookies（先訪問首頁建立會話）
            try:
                init_response = self.session.get(
                    self.base_url,
                    headers=self._generate_headers(),
                    timeout=10
                )
                logger.info(f"初始化會話成功，狀態碼: {init_response.status_code}")
                
                # 保存cookies
                if init_response.cookies:
                    logger.debug(f"獲得 cookies: {len(init_response.cookies)} 個")
                    
            except Exception as e:
                logger.warning(f"初始化會話失敗: {e}")
    
    def fetch_with_requests(self, url: str, params: Dict = None) -> Optional[requests.Response]:
        """
        使用requests獲取數據（會自動重試）
        """
        if not self.session:
            self._create_session()
        
        # 隨機延遲
        self._random_delay()
        
        for attempt in range(self.max_retries):
            try:
                # 每次請求使用新的headers
                headers = self._generate_headers()
                
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=15,
                    verify=True
                )
                
                # 檢查狀態碼
                if response.status_code == 200:
                    logger.info(f"✅ 請求成功: {url[:50]}... (嘗試 {attempt+1} 次)")
                    
                    # 立即設置正確的編碼（富邦網站使用big5）
                    response.encoding = 'big5'
                    
                    # 檢查是否被重定向到驗證頁面
                    if 'captcha' in response.url.lower() or 'verify' in response.url.lower():
                        logger.warning("⚠️ 觸發驗證機制，需要人工處理")
                        return None
                    
                    self._batch_rest()
                    return response
                    
                elif response.status_code == 403:
                    logger.warning(f"⚠️ 請求被拒絕 (403)，嘗試 {attempt+1}/{self.max_retries}")
                    
                elif response.status_code == 429:
                    logger.warning(f"⚠️ 請求過於頻繁 (429)，等待後重試")
                    time.sleep(self.retry_delay * (attempt + 2))
                    
                else:
                    logger.warning(f"⚠️ HTTP錯誤 {response.status_code}，嘗試 {attempt+1}/{self.max_retries}")
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ 請求異常 (嘗試 {attempt+1}/{self.max_retries}): {e}")
            
            # 重試前等待（指數退避）
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.debug(f"等待 {wait_time} 秒後重試")
                time.sleep(wait_time)
        
        logger.error(f"❌ 所有重試均失敗: {url}")
        return None
    
    def parse_broker_data_table(self, html_content: str) -> pd.DataFrame:
        """
        修正版：解析富邦網站券商分點表格數據
        解決編碼問題和JavaScript數據提取
        """
        logger.info("🔄 開始解析HTML數據...")
        
        # 方法1: 如果html_content是bytes，先解碼
        if isinstance(html_content, bytes):
            logger.info("檢測到bytes類型的HTML，嘗試big5解碼...")
            for encoding in ['big5', 'utf-8', 'cp950', 'latin1']:
                try:
                    html_content = html_content.decode(encoding)
                    logger.info(f"✅ 使用 {encoding} 解碼成功")
                    break
                except:
                    continue
        
        # 移除可能的BOM字符
        if isinstance(html_content, str):
            if html_content.startswith('\ufeff'):
                html_content = html_content[1:]
        
        logger.info(f"HTML長度: {len(html_content)} 字符")
        
        # 檢查是否包含關鍵字
        has_keywords = any(kw in html_content for kw in ['券商名稱', 'GenLink2stk', '買進張數'])
        logger.info(f"是否包含關鍵字: {has_keywords}")
        
        if not has_keywords:
            logger.warning("⚠️ HTML中未找到關鍵字，可能編碼有問題")
            # 輸出前500字符用於調試
            logger.debug(f"HTML前500字符: {html_content[:500]}")
        
        # 使用多種解析器嘗試
        soup = None
        for parser in ['html.parser', 'lxml', 'html5lib']:
            try:
                soup = BeautifulSoup(html_content, parser)
                tables = soup.find_all('table')
                logger.info(f"使用 {parser} 找到 {len(tables)} 個表格")
                
                if len(tables) >= 3:
                    logger.info(f"✅ 使用 {parser} 解析成功")
                    break
            except Exception as e:
                logger.debug(f"{parser} 解析失敗: {e}")
                continue
        
        if soup is None:
            logger.error("❌ 所有解析器都失敗")
            return pd.DataFrame()
        
        tables = soup.find_all('table')
        logger.info(f"📊 總共找到 {len(tables)} 個表格")
        
        if len(tables) == 0:
            logger.warning("⚠️ 未找到任何表格，嘗試直接從HTML提取...")
            return self._extract_data_from_html_directly(html_content)
        
        # 尋找包含股票數據的表格（找"買超"表格）
        target_table = None
        for i, table in enumerate(tables):
            first_row = table.find('tr')
            if first_row and first_row.get_text(strip=True) == '買超':
                logger.info(f"✅ 找到買超表格 #{i}")
                target_table = table
                break
        
        # 如果找不到，使用第4個表格
        if target_table is None and len(tables) >= 4:
            target_table = tables[3]
            logger.info("使用第4個表格...")
        
        if target_table is None:
            logger.warning("⚠️ 未找到目標表格")
            return self._extract_data_from_html_directly(html_content)
        
        # 從表格中提取數據
        data_list = self._extract_data_from_table(target_table)
        
        if len(data_list) == 0:
            logger.warning("⚠️ 表格解析無數據，嘗試直接從HTML提取...")
            return self._extract_data_from_html_directly(html_content)
        
        df = pd.DataFrame(data_list)
        logger.info(f"✅ 解析完成，共提取 {len(df)} 筆數據")
        return df
    
    def _extract_data_from_table(self, table) -> list:
        """從表格中提取數據"""
        data = []
        rows = table.find_all('tr')[2:]  # 跳過標題行
        
        logger.info(f"表格有 {len(rows)} 行數據")
        
        for row_idx, row in enumerate(rows[:60]):  # 限制前60行
            row_html = str(row)
            
            stock_code = None
            stock_name = None
            
            # 模式1: GenLink2stk('AS2330','台積電')
            match = re.search(r"GenLink2stk\('AS(\d+)','([^']+)'\)", row_html)
            if match:
                stock_code = match.group(1)
                stock_name = match.group(2)
            
            # 模式2: Link2Stk('00937B')
            if not match:
                match2 = re.search(r"Link2Stk\('(\d+[A-Z]?)'\)", row_html)
                if match2:
                    stock_code = match2.group(1)
                    a_tag = row.find('a')
                    if a_tag:
                        text = a_tag.get_text(strip=True)
                        stock_name = text.replace(stock_code, '').strip() or stock_code
            
            if stock_code:
                # 提取買賣數據
                cells = row.find_all('td')
                if len(cells) >= 4:
                    try:
                        buy_count = self._parse_number(cells[-3].get_text())
                        sell_count = self._parse_number(cells[-2].get_text())
                        net_count = self._parse_number(cells[-1].get_text())
                        
                        if buy_count > 0 or sell_count > 0:
                            data.append({
                                'stock_code': stock_code,
                                'stock_name': stock_name or stock_code,
                                'buy_count': buy_count,
                                'sell_count': sell_count,
                                'net_count': net_count,
                                'timestamp': datetime.now()
                            })
                    except Exception as e:
                        logger.debug(f"解析第 {row_idx} 行數據失敗: {e}")
                        # 嘗試從HTML直接提取數字
                        numbers = re.findall(r'>([\d,]+)<', row_html)
                        if len(numbers) >= 3:
                            try:
                                data.append({
                                    'stock_code': stock_code,
                                    'stock_name': stock_name or stock_code,
                                    'buy_count': self._parse_number(numbers[-3]),
                                    'sell_count': self._parse_number(numbers[-2]),
                                    'net_count': self._parse_number(numbers[-1]),
                                    'timestamp': datetime.now()
                                })
                            except:
                                pass
        
        return data
    
    def _extract_data_from_html_directly(self, html_content: str) -> pd.DataFrame:
        """
        直接從HTML提取數據（主要方法）
        
        富邦網站的數據結構：
        - 股票代碼和名稱在 GenLink2stk('AS2330','台積電') 格式中
        - 買賣數據在後續的 <td> 標籤中
        """
        logger.info("使用直接提取方法...")
        data = []
        
        # 方法1: 使用正則表達式提取所有股票代碼和名稱
        stock_pattern = r"GenLink2stk\('AS(\d{4,6})','([^']+)'\)"
        stock_matches = re.findall(stock_pattern, html_content)
        
        logger.info(f"找到 {len(stock_matches)} 個股票代碼")
        
        if len(stock_matches) == 0:
            logger.warning("❌ 未找到任何股票代碼")
            return pd.DataFrame()
        
        # 方法2: 嘗試找到每個股票對應的數字
        # 富邦網站的格式是：股票連結後跟著3個數字（買進、賣出、差額）
        for stock_code, stock_name in stock_matches:
            try:
                # 找到這個股票代碼在HTML中的位置
                stock_marker = f"GenLink2stk('AS{stock_code}','{stock_name}')"
                stock_pos = html_content.find(stock_marker)
                
                if stock_pos == -1:
                    continue
                
                # 從這個位置開始，找到後續的數字
                # 數字格式: >123,456< 或 >123<
                after_stock = html_content[stock_pos:stock_pos + 500]
                
                # 提取所有數字
                numbers = re.findall(r'>([0-9,]+)<', after_stock)
                
                if len(numbers) >= 3:
                    # 過濾掉太小的數字（可能是其他數據）
                    valid_numbers = []
                    for num_str in numbers:
                        cleaned = num_str.replace(',', '')
                        if cleaned.isdigit():
                            valid_numbers.append(int(cleaned))
                    
                    if len(valid_numbers) >= 3:
                        buy_count = valid_numbers[0]
                        sell_count = valid_numbers[1]
                        net_count = valid_numbers[2]
                        
                        data.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'buy_count': buy_count,
                            'sell_count': sell_count,
                            'net_count': net_count,
                            'timestamp': datetime.now()
                        })
                        
            except Exception as e:
                logger.debug(f"提取 {stock_code} 數據失敗: {e}")
                continue
        
        if data:
            logger.info(f"✅ 直接提取獲得 {len(data)} 筆數據")
            # 顯示前5筆
            for i, item in enumerate(data[:5]):
                logger.info(f"  {i+1}. {item['stock_code']} {item['stock_name']}: 買{item['buy_count']} 賣{item['sell_count']} 淨{item['net_count']}")
            return pd.DataFrame(data)
        
        # 方法3: 如果方法2失敗，嘗試更寬鬆的匹配
        logger.info("嘗試寬鬆匹配...")
        
        for stock_code, stock_name in stock_matches:
            try:
                # 找到包含這個股票的整行
                line_pattern = rf"GenLink2stk\('AS{stock_code}','{re.escape(stock_name)}'\).*?</tr>"
                line_match = re.search(line_pattern, html_content, re.DOTALL | re.IGNORECASE)
                
                if line_match:
                    line_content = line_match.group(0)
                    # 提取這一行中的所有數字
                    all_numbers = re.findall(r'>(\d[\d,]*)<', line_content)
                    
                    if len(all_numbers) >= 3:
                        # 取最後3個數字（買進、賣出、差額）
                        nums = [int(n.replace(',', '')) for n in all_numbers[-3:]]
                        
                        data.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'buy_count': nums[0],
                            'sell_count': nums[1],
                            'net_count': nums[2],
                            'timestamp': datetime.now()
                        })
            except Exception as e:
                logger.debug(f"寬鬆匹配 {stock_code} 失敗: {e}")
                continue
        
        if data:
            logger.info(f"✅ 寬鬆匹配獲得 {len(data)} 筆數據")
            return pd.DataFrame(data)
        
        logger.warning("❌ 所有提取方法都失敗")
        return pd.DataFrame()

    
    def _parse_number(self, text: str) -> int:
        """解析數字字串（處理千分位逗號、正負號）"""
        try:
            # 移除所有非數字字符（保留負號）
            text = text.replace(',', '').replace(' ', '').strip()
            
            # 處理特殊符號
            if '△' in text:  # 減少
                text = text.replace('△', '')
            elif '▽' in text:  # 增加
                text = '-' + text.replace('▽', '')
            elif '▼' in text:  # 減少
                text = '-' + text.replace('▼', '')
            elif '▲' in text:  # 增加
                text = text.replace('▲', '')
            
            # 處理空值
            if not text or text == '-' or text == '--':
                return 0
            
            # 轉換為整數
            return int(float(text))
            
        except Exception as e:
            logger.debug(f"數字解析失敗 '{text}': {e}")
            return 0
    
    # ==================== 已知可用的富邦分點 ====================
    FUBON_BRANCHES = {
        "總公司": "9600",
        "新店": "9661",      # 富邦新店 <-- 專家提供的正確代碼！
        "陽明": "9604",
        "竹北": "9624",
        "新竹": "9647",
        "永和": "9654",
        "南員林": "0039003600310052",
    }

    
    def get_broker_flow_by_date(self, 
                               broker_code: str = '9600',
                               sub_broker_code: str = None,
                               start_date: str = None,
                               end_date: str = None,
                               auto_fallback: bool = True) -> pd.DataFrame:
        """
        獲取指定日期範圍的券商進出數據
        
        【重要修復】富邦 API 需要兩個參數：
        - a: 券商代碼（如 9600 = 富邦）
        - b: 分點代碼（如 9600 = 總公司, 9604 = 陽明）
        
        Args:
            broker_code: 券商代碼（9600=富邦）
            sub_broker_code: 分點代碼（預設使用總公司 9600）
            start_date: 開始日期 'YYYY-MM-DD'（目前未使用，富邦API不支援日期篩選）
            end_date: 結束日期 'YYYY-MM-DD'（目前未使用）
            auto_fallback: 是否自動回溯（目前未使用）
        """
        # 如果沒有指定分點代碼，使用總公司
        if sub_broker_code is None:
            sub_broker_code = broker_code
        
        # 【修復核心】正確的 URL 參數格式
        # 富邦網站只需要 a（券商代碼）和 b（分點代碼）
        params = {
            'a': broker_code,       # 券商代碼
            'b': sub_broker_code,   # 分點代碼
        }
        
        url = f"{self.base_url}/z/zg/zgb/zgb0.djhtm"
        
        logger.info(f"📊 抓取券商數據: a={broker_code}, b={sub_broker_code}")
        logger.info(f"🔗 URL: {url}?a={broker_code}&b={sub_broker_code}")
        
        # 發送請求
        response = self.fetch_with_requests(url, params=params)
        
        if not response:
            logger.error("❌ 請求失敗")
            return pd.DataFrame()
        
        # 強制使用big5編碼（富邦網站使用big5）
        response.encoding = 'big5'
        html_content = response.text
        
        # 檢查是否返回錯誤
        if "券商分點代碼有誤" in html_content:
            logger.error(f"❌ 分點代碼錯誤: a={broker_code}, b={sub_broker_code}")
            logger.error("💡 可用的富邦分點: " + str(self.FUBON_BRANCHES))
            return pd.DataFrame()
        
        # 解析數據
        df = self.parse_broker_data_table(html_content)
        
        if not df.empty:
            # 添加日期和券商代碼
            df['date'] = datetime.now().strftime('%Y-%m-%d')
            df['broker_code'] = broker_code
            df['sub_broker_code'] = sub_broker_code
            
            logger.info(f"✅ 成功獲取數據: {len(df)} 筆")
            return df
        else:
            logger.warning(f"⚠️ 無數據")
            return pd.DataFrame()
    
    def get_multiple_brokers_data(self, 
                                 broker_codes: List[str],
                                 date: str = None) -> pd.DataFrame:
        """
        獲取多個券商的數據
        
        Args:
            broker_codes: 券商代碼列表
            date: 日期 'YYYY-MM-DD'
        """
        all_data = []
        
        for broker_code in broker_codes:
            logger.info(f"抓取券商 {broker_code}...")
            
            df = self.get_broker_flow_by_date(
                broker_code=broker_code,
                start_date=date,
                end_date=date
            )
            
            if not df.empty:
                all_data.append(df)
            
            # 避免請求過快
            self._random_delay()
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"✅ 總共獲取 {len(combined_df)} 筆數據")
            return combined_df
        else:
            logger.warning("⚠️ 未獲取到任何數據")
            return pd.DataFrame()
    
    def get_top_stocks_by_broker(self,
                                 broker_code: str = '9600',
                                 sub_broker_code: str = None,
                                 top_n: int = 20,
                                 min_net_count: int = 0) -> List[Dict]:
        """
        獲取特定券商分點買超前N名股票
        
        Args:
            broker_code: 券商代碼（如 9600=富邦）
            sub_broker_code: 分點代碼（如 9600=總公司）
            top_n: 前N名
            min_net_count: 最小買超張數（設為0以獲取所有數據）
        """
        # 使用正確的參數獲取數據
        df = self.get_broker_flow_by_date(
            broker_code=broker_code,
            sub_broker_code=sub_broker_code
        )
        
        if df.empty:
            logger.warning("⚠️ 未獲取到任何數據")
            return []
        
        # 按股票代碼分組統計（如果有重複）
        if 'stock_code' in df.columns:
            stock_summary = df.groupby('stock_code').agg({
                'stock_name': 'first',
                'buy_count': 'sum',
                'sell_count': 'sum',
                'net_count': 'sum'
            }).reset_index()
        else:
            stock_summary = df
        
        # 篩選買超股票
        if min_net_count > 0:
            buy_stocks = stock_summary[stock_summary['net_count'] >= min_net_count]
        else:
            buy_stocks = stock_summary
        
        # 排序並取前N名
        top_stocks = buy_stocks.nlargest(top_n, 'net_count')
        
        result = []
        for _, row in top_stocks.iterrows():
            result.append({
                'stock_code': row['stock_code'],
                'stock_name': row['stock_name'],
                'buy_count': int(row['buy_count']),
                'sell_count': int(row['sell_count']),
                'net_count': int(row['net_count']),
                'broker_code': broker_code,
                'sub_broker_code': sub_broker_code or broker_code
            })
        
        logger.info(f"✅ 找到 {len(result)} 檔買超股票")
        
        return result
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None):
        """保存數據到CSV"""
        if df.empty:
            logger.warning("無數據可保存")
            return None
        
        if not filename:
            filename = f'broker_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 數據已保存: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ 保存失敗: {e}")
            return None
    
    def close(self):
        """關閉資源"""
        if self.session:
            self.session.close()
            self.session = None
        
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 全域實例
advanced_broker_crawler = AdvancedBrokerCrawler()


# ==================== 便捷函數 ====================

def get_fubon_data(broker_code: str = '9600', sub_broker_code: str = '9600') -> pd.DataFrame:
    """
    獲取富邦券商分點數據
    
    Args:
        broker_code: 券商代碼（9600=富邦）
        sub_broker_code: 分點代碼（9600=總公司, 9604=陽明, 9624=竹北, 9647=新竹, 9654=永和）
    """
    return advanced_broker_crawler.get_broker_flow_by_date(
        broker_code=broker_code,
        sub_broker_code=sub_broker_code
    )


# 舊函數名稱保持向後兼容
def get_fubon_xindan_data(days: int = 5) -> pd.DataFrame:
    """獲取富邦總公司數據（向後兼容）"""
    logger.warning("⚠️ get_fubon_xindan_data 已棄用，請使用 get_fubon_data()")
    return get_fubon_data(broker_code='9600', sub_broker_code='9600')


def get_fubon_xindan_top_stocks_advanced(top_n: int = 20) -> List[Dict]:
    """
    獲取富邦總公司買超前N名
    
    【注意】原本查詢的「富邦-新店」分點不存在於富邦網站
    現改為查詢「富邦總公司」(sub_broker_code=9600)
    """
    return advanced_broker_crawler.get_top_stocks_by_broker(
        broker_code='9600',
        sub_broker_code='9600',  # 使用總公司
        top_n=top_n,
        min_net_count=0  # 獲取所有數據
    )


def get_fubon_branch_top_stocks(branch_name: str = '總公司', top_n: int = 20) -> List[Dict]:
    """
    獲取指定富邦分點的買超前N名股票
    
    Args:
        branch_name: 分點名稱 ('總公司', '陽明', '竹北', '新竹', '永和', '南員林')
        top_n: 前N名
    """
    sub_broker_code = AdvancedBrokerCrawler.FUBON_BRANCHES.get(branch_name, '9600')
    
    return advanced_broker_crawler.get_top_stocks_by_broker(
        broker_code='9600',
        sub_broker_code=sub_broker_code,
        top_n=top_n
    )


def get_all_key_brokers_data(date: str = None) -> pd.DataFrame:
    """獲取所有關鍵券商數據"""
    # 使用已知可用的分點代碼
    all_data = []
    
    for branch_name, sub_code in AdvancedBrokerCrawler.FUBON_BRANCHES.items():
        try:
            df = advanced_broker_crawler.get_broker_flow_by_date(
                broker_code='9600',
                sub_broker_code=sub_code
            )
            if not df.empty:
                df['branch_name'] = branch_name
                all_data.append(df)
        except Exception as e:
            logger.warning(f"獲取 {branch_name} 數據失敗: {e}")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()
