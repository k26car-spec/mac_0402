"""
GoodInfo 台股資訊爬蟲 (Selenium 版本)
https://goodinfo.tw/

使用 Selenium 繞過 JavaScript 動態載入
支援無頭模式自動運行

提供功能:
1. 每日熱門股票
2. 法人買賣超
3. 個股基本資訊
4. 股票新聞
5. 漲跌幅排行
6. 殖利率排行
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import re
import logging
import random
import time

logger = logging.getLogger(__name__)

# 嘗試導入 Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium 未安裝，GoodInfo 爬蟲不可用")


class GoodInfoCrawler:
    """GoodInfo 爬蟲 (Selenium 版)"""
    
    BASE_URL = "https://goodinfo.tw/tw"
    
    def __init__(self):
        self.driver = None
        self._driver_initialized = False
    
    def _init_driver(self):
        """初始化 Chrome WebDriver"""
        if self._driver_initialized and self.driver:
            return True
        
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium 未安裝")
            return False
        
        try:
            options = Options()
            options.add_argument('--headless')  # 無頭模式
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 自動下載並管理 ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(10)
            
            self._driver_initialized = True
            logger.info("✅ Chrome WebDriver 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebDriver 初始化失敗: {e}")
            return False
    
    def close(self):
        """關閉 WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self._driver_initialized = False
            logger.info("WebDriver 已關閉")
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """獲取網頁內容"""
        if not self._init_driver():
            return None
        
        try:
            # 隨機延遲
            time.sleep(random.uniform(0.5, 1.5))
            
            self.driver.get(url)
            
            # 等待頁面載入
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # 額外等待動態內容
            time.sleep(1)
            
            return self.driver.page_source
            
        except Exception as e:
            logger.error(f"GoodInfo 頁面獲取失敗: {e}")
            return None
    
    # ==================== 個股資訊 ====================
    
    async def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        獲取個股詳細資訊
        
        Args:
            stock_code: 股票代碼 (如: 2330)
        """
        if not self._init_driver():
            return None
        
        url = f"{self.BASE_URL}/StockDetail.asp?STOCK_ID={stock_code}"
        
        try:
            time.sleep(random.uniform(0.5, 1.0))
            self.driver.get(url)
            
            # 等待頁面載入
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            time.sleep(1.5)  # 等待動態內容
            
            info = {"code": stock_code, "source": "GoodInfo"}
            
            # 股票名稱 (從標題取得)
            try:
                title = self.driver.title
                match = re.search(r'(\d{4})\s+(.+?)\s', title)
                if match:
                    info["name"] = match.group(2)
            except:
                pass
            
            # 使用 JavaScript 直接取得價格資訊
            try:
                # 嘗試取得收盤價
                script = """
                    var tables = document.querySelectorAll('table');
                    var result = {};
                    for (var t = 0; t < tables.length; t++) {
                        var rows = tables[t].querySelectorAll('tr');
                        for (var r = 0; r < rows.length; r++) {
                            var cells = rows[r].querySelectorAll('td');
                            for (var c = 0; c < cells.length - 1; c++) {
                                var key = cells[c].innerText.trim();
                                var value = cells[c+1].innerText.trim();
                                if (key.includes('收盤') && !result.price) result.price = value;
                                if (key.includes('漲跌幅')) result.change_pct = value;
                                if (key.includes('漲跌') && !result.change) result.change = value;
                                if (key.includes('成交量') && !result.volume) result.volume = value;
                                if (key.includes('本益比') && !result.pe_ratio) result.pe_ratio = value;
                                if (key.includes('殖利率') && !result.dividend_yield) result.dividend_yield = value;
                            }
                        }
                    }
                    return result;
                """
                js_result = self.driver.execute_script(script)
                if js_result:
                    info.update({k: v for k, v in js_result.items() if v and len(v) < 50})
            except Exception as e:
                logger.debug(f"JavaScript 解析失敗: {e}")
            
            info["updated_at"] = datetime.now().isoformat()
            logger.info(f"✅ GoodInfo 取得 {stock_code} 資訊: {info.get('name', '')}")
            return info
            
        except Exception as e:
            logger.error(f"解析個股資訊失敗: {e}")
            return None
    
    async def get_stock_eps_history(self, stock_code: str) -> List[Dict]:
        """
        獲取個股歷年/季 EPS 與獲利能力
        URL: https://goodinfo.tw/tw/StockCfgDetail.asp?STOCK_ID={stock_code}&SHEET=EPS
        """
        if not self._init_driver():
            return []
        
        # 使用詳細財務報表頁面 (獲利狀況)
        url = f"{self.BASE_URL}/StockCfgDetail.asp?STOCK_ID={stock_code}&SHEET=EPS"
        
        try:
            time.sleep(random.uniform(0.5, 1.0))
            self.driver.get(url)
            
            # 等待表格載入
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "tblDetail"))
            )
            time.sleep(1.0)
            
            # 使用 JS 提取 EPS 表格數據
            script = """
                var rows = document.querySelectorAll('#tblDetail tr');
                var results = [];
                for (var i = 0; i < rows.length; i++) {
                    var cells = rows[i].querySelectorAll('td');
                    if (cells.length >= 10) {
                        var period = cells[0].innerText.trim();
                        if (period.includes('Q') || (period.length == 4 && !isNaN(period))) {
                            results.push({
                                "quarter": period,
                                "eps": parseFloat(cells[3].innerText.trim()) || 0,
                                "roe": parseFloat(cells[6].innerText.trim()) || 0,
                                "net_margin": parseFloat(cells[10].innerText.trim()) || 0
                            });
                        }
                    }
                }
                return results;
            """
            eps_data = self.driver.execute_script(script)
            
            if eps_data:
                logger.info(f"✅ GoodInfo 取得 {stock_code} EPS 歷史: {len(eps_data)} 筆")
                return eps_data[:8] # 取最近 8 季
            return []
            
        except Exception as e:
            logger.error(f"GoodInfo 獲取 EPS 失敗: {e}")
            return []
    
    # ==================== 熱門股票 ====================
    
    async def get_hot_stocks(self) -> List[Dict]:
        """獲取今日熱門股票"""
        url = f"{self.BASE_URL}/index.asp"
        
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, self._fetch_page, url)
        
        if not html:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            hot_stocks = []
            
            # 尋找股票表格
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        try:
                            code = cols[0].get_text(strip=True)
                            name = cols[1].get_text(strip=True)
                            price = cols[2].get_text(strip=True)
                            change = cols[3].get_text(strip=True)
                            
                            if code and len(code) == 4 and code.isdigit():
                                hot_stocks.append({
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "change": change,
                                    "source": "GoodInfo"
                                })
                                
                                if len(hot_stocks) >= 20:
                                    break
                        except:
                            continue
                    
                if len(hot_stocks) >= 20:
                    break
            
            logger.info(f"✅ GoodInfo 取得 {len(hot_stocks)} 檔熱門股")
            return hot_stocks
            
        except Exception as e:
            logger.error(f"解析熱門股票失敗: {e}")
            return []
    
    # ==================== 法人買賣超 ====================
    
    async def get_institutional_trading(self, trade_type: str = "foreign") -> List[Dict]:
        """
        獲取法人買賣超
        
        Args:
            trade_type: foreign / investment_trust / dealer
        """
        type_map = {
            "foreign": "外資買賣超",
            "investment_trust": "投信買賣超",
            "dealer": "自營買賣超",
        }
        
        url = f"{self.BASE_URL}/StockList.asp?MARKET_CAT=全部&INDUSTRY_CAT=全部&SHEET={type_map.get(trade_type, '外資買賣超')}"
        
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, self._fetch_page, url)
        
        if not html:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            
            # 尋找主表格
            table = soup.find('table', id='tblStockList')
            if table:
                rows = table.find_all('tr')
                for row in rows[2:22]:  # 取前20筆
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        try:
                            code = cols[0].get_text(strip=True)
                            name = cols[1].get_text(strip=True)
                            price = cols[2].get_text(strip=True)
                            
                            # 買賣超通常在後面的欄位
                            buy_sell = cols[-1].get_text(strip=True) if len(cols) > 5 else ""
                            
                            if code and len(code) == 4:
                                results.append({
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "buy_sell": buy_sell,
                                    "type": trade_type,
                                    "source": "GoodInfo"
                                })
                        except:
                            continue
            
            logger.info(f"✅ GoodInfo {trade_type} 買賣超取得 {len(results)} 筆")
            return results
            
        except Exception as e:
            logger.error(f"解析法人買賣超失敗: {e}")
            return []
    
    # ==================== 漲跌幅排行 ====================
    
    async def get_price_ranking(self, rank_type: str = "up") -> List[Dict]:
        """獲取漲跌幅排行"""
        sheet_name = "今日漲幅排行" if rank_type == "up" else "今日跌幅排行"
        url = f"{self.BASE_URL}/StockList.asp?MARKET_CAT=上市&INDUSTRY_CAT=全部&SHEET={sheet_name}"
        
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, self._fetch_page, url)
        
        if not html:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            
            table = soup.find('table', id='tblStockList')
            if table:
                rows = table.find_all('tr')
                for row in rows[2:22]:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        try:
                            code = cols[0].get_text(strip=True)
                            name = cols[1].get_text(strip=True)
                            price = cols[2].get_text(strip=True)
                            change = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                            change_pct = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                            
                            if code and len(code) == 4:
                                results.append({
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "change": change,
                                    "change_pct": change_pct,
                                    "rank_type": rank_type,
                                    "source": "GoodInfo"
                                })
                        except:
                            continue
            
            logger.info(f"✅ GoodInfo {rank_type} 排行取得 {len(results)} 筆")
            return results
            
        except Exception as e:
            logger.error(f"解析排行失敗: {e}")
            return []
    
    # ==================== 股票新聞 ====================
    
    async def get_stock_news(self, stock_code: str = None) -> List[Dict]:
        """獲取股票新聞"""
        if stock_code:
            url = f"{self.BASE_URL}/StockNews.asp?STOCK_ID={stock_code}"
        else:
            url = f"{self.BASE_URL}/StockNews.asp"
        
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, self._fetch_page, url)
        
        if not html:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            news_list = []
            
            # 嘗試找新聞表格
            table = soup.find('table', id='tblDetail')
            if not table:
                # 備用: 找所有表格
                tables = soup.find_all('table')
                for t in tables:
                    if '新聞' in t.get_text()[:100]:
                        table = t
                        break
            
            if table:
                rows = table.find_all('tr')
                for row in rows[1:21]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        try:
                            date = cols[0].get_text(strip=True)
                            title_elem = cols[1].find('a')
                            title = title_elem.get_text(strip=True) if title_elem else cols[1].get_text(strip=True)
                            source = cols[2].get_text(strip=True) if len(cols) > 2 else "GoodInfo"
                            
                            if title and len(title) > 5:
                                news_list.append({
                                    "date": date,
                                    "title": title,
                                    "source": source,
                                    "stock_code": stock_code,
                                })
                        except:
                            continue
            
            logger.info(f"✅ GoodInfo 取得 {len(news_list)} 則新聞")
            return news_list
            
        except Exception as e:
            logger.error(f"解析新聞失敗: {e}")
            return []
    
    # ==================== 殖利率排行 ====================
    
    async def get_dividend_ranking(self) -> List[Dict]:
        """獲取殖利率排行"""
        url = f"{self.BASE_URL}/StockList.asp?MARKET_CAT=上市&INDUSTRY_CAT=全部&SHEET=殖利率排行"
        
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, self._fetch_page, url)
        
        if not html:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            
            table = soup.find('table', id='tblStockList')
            if table:
                rows = table.find_all('tr')
                for row in rows[2:22]:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        try:
                            code = cols[0].get_text(strip=True)
                            name = cols[1].get_text(strip=True)
                            price = cols[2].get_text(strip=True)
                            yield_rate = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                            
                            if code and len(code) == 4:
                                results.append({
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "yield_rate": yield_rate,
                                    "source": "GoodInfo"
                                })
                        except:
                            continue
            
            logger.info(f"✅ GoodInfo 殖利率排行取得 {len(results)} 筆")
            return results
            
        except Exception as e:
            logger.error(f"解析殖利率排行失敗: {e}")
            return []
    
    # ==================== 綜合報告 ====================
    
    async def generate_market_report(self) -> Dict:
        """生成市場綜合報告"""
        logger.info("開始生成 GoodInfo 市場報告...")
        
        # 依序執行避免過多請求
        hot_stocks = await self.get_hot_stocks()
        await asyncio.sleep(1)
        
        foreign_trading = await self.get_institutional_trading("foreign")
        await asyncio.sleep(1)
        
        top_gainers = await self.get_price_ranking("up")
        await asyncio.sleep(1)
        
        dividend_ranking = await self.get_dividend_ranking()
        
        report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source": "GoodInfo",
            "hot_stocks": hot_stocks[:10],
            "institutional": {
                "foreign": foreign_trading[:10],
            },
            "rankings": {
                "top_gainers": top_gainers[:10],
                "high_dividend": dividend_ranking[:10],
            },
            "summary": {
                "total_data_points": len(hot_stocks) + len(foreign_trading) + len(top_gainers),
            }
        }
        
        logger.info("GoodInfo 市場報告生成完成")
        return report


# 全域實例
goodinfo_crawler = GoodInfoCrawler()


# ==================== 便捷函數 ====================

async def get_goodinfo_report() -> Dict:
    """獲取 GoodInfo 市場報告"""
    return await goodinfo_crawler.generate_market_report()

async def get_stock_from_goodinfo(stock_code: str) -> Optional[Dict]:
    """獲取個股資訊"""
    return await goodinfo_crawler.get_stock_info(stock_code)


# ==================== 測試 ====================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("GoodInfo 爬蟲測試 (Selenium)")
        print("=" * 60)
        
        crawler = GoodInfoCrawler()
        
        try:
            # 測試個股資訊
            print("\n📊 個股資訊 (台積電 2330):")
            info = await crawler.get_stock_info("2330")
            if info:
                print(f"  名稱: {info.get('name', '-')}")
                print(f"  價格: {info.get('price', '-')}")
                print(f"  漲跌: {info.get('change', '-')} ({info.get('change_pct', '-')})")
                print(f"  本益比: {info.get('pe_ratio', '-')}")
                print(f"  殖利率: {info.get('dividend_yield', '-')}")
            else:
                print("  ❌ 無法取得")
            
            # 測試熱門股票
            print("\n🔥 熱門股票:")
            hot_stocks = await crawler.get_hot_stocks()
            for stock in hot_stocks[:5]:
                print(f"  {stock.get('code', '-')} {stock.get('name', '-')}: {stock.get('price', '-')}")
            
            # 測試新聞
            print("\n📰 最新新聞:")
            news = await crawler.get_stock_news()
            for n in news[:5]:
                print(f"  [{n.get('date', '')}] {n.get('title', '')[:40]}...")
            
        finally:
            crawler.close()
        
        print("\n✅ 測試完成!")
    
    asyncio.run(test())
