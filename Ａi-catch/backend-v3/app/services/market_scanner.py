"""
全市場強勢股掃描器
Market Scanner - Breakout Stock Finder

功能：
1. 每天開盤後掃描全市場
2. 自動找出漲幅 > 5% 的強勢股
3. 自動加入 ORB 監控清單

掃描來源：
- 台灣上市股票 (約 900+)
- 台灣上櫃股票 (約 700+)
"""

import asyncio
import logging
from datetime import datetime, time as dt_time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# 常用股票繁體中文名稱對照表
STOCK_NAMES_TW = {
    # 半導體
    "2330": "台積電", "2454": "聯發科", "3711": "日月光投控", "2303": "聯電", "3034": "聯詠",
    "6770": "力積電", "3661": "世芯-KY", "2379": "瑞昱", "2344": "華邦電", "2337": "旺宏",
    # PCB / 電子
    "2317": "鴻海", "3037": "欣興", "2313": "華通", "2314": "台揚", "8046": "南電",
    "3706": "神達", "2327": "國巨", "6153": "嘉聯益", "2368": "金像電", "2367": "燿華",
    # 金融
    "2881": "富邦金", "2882": "國泰金", "2891": "中信金", "2884": "玉山金", "2886": "兆豐金",
    "2887": "台新金", "2892": "第一金", "2801": "彰銀", "5880": "合庫金", "2834": "臺企銀",
    # 傳產
    "1301": "台塑", "1303": "南亞", "1326": "台化", "1101": "台泥", "1216": "統一",
    "2912": "統一超", "1605": "華新", "2002": "中鋼", "2207": "和泰車", "9910": "豐泰",
    # 其他
    "3231": "緯創", "2382": "廣達", "3008": "大立光", "2412": "中華電", "3481": "群創",
    "2609": "陽明", "2618": "長榮航", "2377": "微星", "2301": "光寶科", "2408": "南亞科",
    # 中小型股
    "5498": "凱崴", "8074": "鉅橡", "3163": "波若威", "6257": "矽格", "1815": "富喬",
    "8422": "可寧衛", "3265": "台星科", "3363": "上詮", "8155": "博智", "6282": "康舒",
    "5521": "工信", "2312": "金寶", "3443": "創意", "6285": "啟碁", "3529": "力旺",
    "6239": "力成", "3189": "景碩", "2449": "京元電子", "3653": "健策", "6452": "康友-KY"
}


async def get_stock_name_tw(symbol: str) -> str:
    """取得股票繁體中文名稱"""
    # 1. 先查本地字典
    if symbol in STOCK_NAMES_TW:
        return STOCK_NAMES_TW[symbol]
    
    # 2. 嘗試從 API 取得
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"http://localhost:8000/api/stock-analysis/stock-name/{symbol}")
            if resp.status_code == 200:
                data = resp.json()
                name = data.get('name', '')
                if name and not name.isascii():  # 確保是中文
                    return name
    except:
        pass
    
    # 3. 嘗試從 Yahoo 取得
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.TW")
        # 🚀 避免阻塞 Event Loop
        info = await asyncio.to_thread(lambda: ticker.info)
        name = info.get('shortName', '') or info.get('longName', '')
        if name:
            # 嘗試轉換為中文 (如果有對照)
            return name[:10]
    except:
        pass
    
    return symbol  # 最後返回代碼本身


class MarketScanner:
    """全市場強勢股掃描器"""
    
    def __init__(self):
        self.is_running = False
        self.last_scan_date = None
        self.found_stocks: List[Dict] = []
        
        # 掃描設定
        self.min_change_pct = 5.0    # 最低漲幅 5%
        self.min_volume = 500        # 最低成交量 500 張
        self.max_price = 500         # 最高價格 (過濾高價股)
        self.min_price = 10          # 最低價格 (過濾低價股)
        
        # 掃描時間設定
        self.first_scan_time = dt_time(9, 30)   # 第一次掃描 09:30
        self.second_scan_time = dt_time(10, 0)  # 第二次掃描 10:00
        self.third_scan_time = dt_time(10, 30)  # 第三次掃描 10:30
        
    async def start(self):
        """啟動市場掃描器"""
        if self.is_running:
            logger.warning("市場掃描器已在運行中")
            return
        
        self.is_running = True
        logger.info("🔍 全市場強勢股掃描器已啟動")
        logger.info(f"   掃描條件: 漲幅 ≥ {self.min_change_pct}%, 成交量 ≥ {self.min_volume} 張")
        logger.info(f"   掃描時間: 09:30, 10:00, 10:30")
        
        while self.is_running:
            try:
                now = datetime.now()
                current_time = now.time()
                
                # 只在交易日運行（結合假日與週末判斷）
                from app.utils.twse_calendar import twse_calendar
                if not twse_calendar.is_trading_day(now):
                    await asyncio.sleep(60)
                    continue
                
                # 檢查是否到掃描時間
                should_scan = False
                
                if self.last_scan_date != now.date():
                    # 新的一天，重置
                    self.found_stocks = []
                    
                    if current_time >= self.first_scan_time:
                        should_scan = True
                        self.last_scan_date = now.date()
                
                # 定時掃描
                for scan_time in [self.first_scan_time, self.second_scan_time, self.third_scan_time]:
                    if (current_time >= scan_time and 
                        current_time < dt_time(scan_time.hour, scan_time.minute + 5)):
                        should_scan = True
                        break
                
                if should_scan:
                    await self._scan_market()
                    await asyncio.sleep(300)  # 掃描後等待 5 分鐘
                else:
                    await asyncio.sleep(60)  # 每分鐘檢查一次
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"市場掃描器錯誤: {e}")
                await asyncio.sleep(60)
        
        self.is_running = False
        logger.info("🔴 市場掃描器已停止")
    
    def stop(self):
        """停止掃描器"""
        self.is_running = False
    
    async def _scan_market(self):
        """掃描全市場找出強勢股"""
        logger.info("🔍 開始全市場掃描...")
        
        try:
            strong_stocks = []
            
            # 方法1: 使用 Yahoo Finance 掃描台股
            strong_stocks.extend(await self._scan_with_yahoo())
            
            # 方法2: 使用證交所 API (如果 Yahoo 失敗)
            if not strong_stocks:
                strong_stocks.extend(await self._scan_with_twse())
            
            if strong_stocks:
                logger.info(f"✅ 發現 {len(strong_stocks)} 檔強勢股!")
                
                # 加入 ORB 監控清單
                await self._add_to_watchlist(strong_stocks)
                
                # 記錄找到的股票
                self.found_stocks.extend(strong_stocks)
                
                # 發送通知
                await self._send_notification(strong_stocks)
            else:
                logger.info("📊 本次掃描未發現符合條件的強勢股")
                
        except Exception as e:
            logger.error(f"市場掃描失敗: {e}")
    
    async def _scan_with_yahoo(self) -> List[Dict]:
        """使用 Yahoo Finance 掃描"""
        strong_stocks = []
        
        try:
            import yfinance as yf
            
            # 台灣熱門股票清單 (擴大範圍)
            # 實際上可以從證交所取得完整清單
            hot_stocks = [
                # 半導體
                "2330", "2454", "3711", "2303", "3034", "6770", "3661", "2379", "2344", "2337",
                # PCB / 電子
                "2317", "3037", "2313", "2314", "8046", "3706", "2327", "6153", "2368", "2367",
                # 金融
                "2881", "2882", "2891", "2884", "2886", "2887", "2892", "2801", "5880", "2834",
                # 傳產
                "1301", "1303", "1326", "1101", "1216", "2912", "1605", "2002", "2207", "9910",
                # 其他熱門
                "3231", "2382", "3008", "2412", "3481", "2609", "2618", "2377", "2301", "2408",
                # 中小型股
                "5498", "8074", "3163", "6257", "1815", "8422", "3265", "3363", "8155", "6282",
                "5521", "2312", "3443", "6285", "3529", "6239", "3189", "2449", "3653", "6452"
            ]
            
            # 已知上櫃股票列表 (TPEx)
            known_tpex = {
                "5498", "8074", "3163", "3265", "3363", "8155", "5521", "3529",
                "6153", "8299", "8069", "5347", "6147", "3293", "3680", "4966",
                "5274", "6121", "6180", "6488", "8938"
            }
            
            for symbol in hot_stocks:
                try:
                    # 判斷正確的後綴
                    if symbol in known_tpex:
                        ticker_symbol = f"{symbol}.TWO"
                    else:
                        ticker_symbol = f"{symbol}.TW"
                        
                    ticker = yf.Ticker(ticker_symbol)
                    # 🚀 將阻塞的 I/O 操作放入線程池執行
                    hist = await asyncio.to_thread(ticker.history, period="2d")
                    
                    # 如抓取失敗且不是已知上櫃，才嘗試 fallback (但對於 1605 等已知上市股不應嘗試)
                    if (hist.empty or len(hist) < 2) and symbol not in known_tpex:
                         # 這裡可以加入更智慧的判斷，目前先保守跳過，避免 1605.TWO 錯誤日誌
                         # 除非我們非常有把握它是上櫃
                         if symbol in ["8046", "1605", "6282", "3481", "1815", "2327"]: # 強制上市名單
                             continue
                             
                         # 其他未知股票才嘗試 .TWO
                         ticker_two = yf.Ticker(f"{symbol}.TWO")
                         hist_two = await asyncio.to_thread(ticker_two.history, period="2d")
                         if not hist_two.empty and len(hist_two) >= 2:
                             hist = hist_two
                             ticker_symbol = f"{symbol}.TWO"
                         else:
                             continue
                    
                    if hist.empty or len(hist) < 2:
                        continue
                    
                    # 計算漲跌幅
                    today = hist.iloc[-1]
                    yesterday = hist.iloc[-2]
                    
                    price = float(today['Close'])
                    prev_close = float(yesterday['Close'])
                    change_pct = (price - prev_close) / prev_close * 100
                    volume = int(today['Volume'] / 1000)  # 轉換為張
                    
                    # 檢查是否符合條件
                    if (change_pct >= self.min_change_pct and
                        volume >= self.min_volume and
                        self.min_price <= price <= self.max_price):
                        
                        # 🆕 取得繁體中文名稱
                        stock_name = await get_stock_name_tw(symbol)
                        
                        strong_stocks.append({
                            "symbol": symbol,
                            "name": stock_name,
                            "price": round(price, 2),
                            "change_pct": round(change_pct, 2),
                            "volume": volume,
                            "high": round(float(today['High']), 2),
                            "low": round(float(today['Low']), 2),
                            "source": "yahoo",
                            "scan_time": datetime.now().isoformat()
                        })
                        
                        logger.info(f"🚀 發現強勢股: {symbol} {stock_name} +{change_pct:.1f}%")
                        
                except Exception as e:
                    # 靜默跳過單一股票錯誤
                    continue
                
                await asyncio.sleep(0.3)  # 避免 API 限制
                
        except Exception as e:
            logger.error(f"Yahoo 掃描失敗: {e}")
        
        return strong_stocks
    
    async def _scan_with_twse(self) -> List[Dict]:
        """使用證交所 API 掃描"""
        strong_stocks = []
        
        try:
            import httpx
            
            # 證交所每日收盤行情
            today_str = datetime.now().strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today_str}&type=ALLBUT0999"
            
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if data.get('stat') == 'OK' and data.get('data9'):
                        for row in data['data9']:
                            try:
                                symbol = row[0]  # 證券代號
                                name = row[1]    # 證券名稱
                                price_str = row[8].replace(',', '')  # 收盤價
                                change_str = row[10].replace(',', '')  # 漲跌
                                volume_str = row[2].replace(',', '')  # 成交量
                                
                                if not price_str or price_str == '--':
                                    continue
                                
                                price = float(price_str)
                                volume = int(volume_str) / 1000  # 轉換為張
                                
                                # 計算漲跌幅
                                try:
                                    change = float(change_str)
                                    prev_close = price - change
                                    change_pct = (change / prev_close) * 100 if prev_close > 0 else 0
                                except:
                                    continue
                                
                                # 檢查條件
                                if (change_pct >= self.min_change_pct and
                                    volume >= self.min_volume and
                                    self.min_price <= price <= self.max_price):
                                    
                                    strong_stocks.append({
                                        "symbol": symbol,
                                        "name": name,
                                        "price": price,
                                        "change_pct": round(change_pct, 2),
                                        "volume": int(volume),
                                        "source": "twse"
                                    })
                                    
                            except Exception:
                                continue
                                
        except Exception as e:
            logger.error(f"TWSE 掃描失敗: {e}")
        
        return strong_stocks
    
    async def _add_to_watchlist(self, stocks: List[Dict]):
        """將強勢股加入 ORB 監控清單 (遞增添加，不覆蓋原有設定)"""
        try:
            import json
            watchlist_file = "/Users/Mac/Documents/ETF/AI/Ａi-catch/data/orb_watchlist.json"
            
            # 🆕 先從檔案讀取現有清單（確保不會遺失用戶設定）
            current_list = []
            try:
                with open(watchlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    current_list = data.get('watchlist', [])
                    logger.info(f"📋 讀取現有清單: {len(current_list)} 支股票")
            except FileNotFoundError:
                logger.info("📋 監控清單檔案不存在，將建立新檔案")
            except Exception as e:
                logger.warning(f"讀取清單檔案失敗: {e}")
            
            # 遞增添加新發現的強勢股（不重複）
            added = []
            for stock in stocks:
                symbol = stock['symbol']
                if symbol not in current_list:
                    current_list.append(symbol)
                    added.append(f"{symbol} {stock.get('name', '')}")
            
            if added:
                logger.info(f"✅ 新增 {len(added)} 檔強勢股: {added}")
                
                # 保存到檔案
                with open(watchlist_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "watchlist": current_list,
                        "updated_at": datetime.now().isoformat(),
                        "note": f"共 {len(current_list)} 支，最後新增: {added}"
                    }, f, ensure_ascii=False, indent=2)
                
                # 同時更新記憶體中的清單
                try:
                    from app.services.smart_simulation_trader import smart_trader
                    smart_trader.orb_watchlist = current_list
                except:
                    pass
            else:
                logger.info("📋 無新增強勢股（都已在清單中）")
                    
        except Exception as e:
            logger.error(f"加入監控清單失敗: {e}")
    
    async def _send_notification(self, stocks: List[Dict]):
        """發送強勢股通知"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import os
            
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            email_user = os.getenv('EMAIL_USERNAME', '')
            email_pass = os.getenv('EMAIL_PASSWORD', '')
            recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')
            
            if not email_user or not recipients:
                return
            
            # 建立郵件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚀 全市場掃描 - 發現 {len(stocks)} 檔強勢股"
            msg['From'] = email_user
            msg['To'] = ', '.join(recipients)
            
            # HTML 內容
            stock_rows = ""
            for s in sorted(stocks, key=lambda x: x['change_pct'], reverse=True):
                color = "#ff4444" if s['change_pct'] >= 9 else "#ff8800"
                stock_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{s['symbol']}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{s.get('name', '')}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${s['price']:.2f}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; color: {color}; font-weight: bold;">+{s['change_pct']:.1f}%</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{s.get('volume', 0):,} 張</td>
                </tr>
                """
            
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                    <h2 style="margin: 0;">🔍 全市場強勢股掃描</h2>
                    <p style="margin: 5px 0 0 0;">發現 {len(stocks)} 檔符合條件的強勢股</p>
                </div>
                
                <div style="padding: 20px; background: white; border: 1px solid #eee;">
                    <p><strong>掃描條件:</strong> 漲幅 ≥ {self.min_change_pct}%, 成交量 ≥ {self.min_volume} 張</p>
                    <p><strong>掃描時間:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <thead>
                            <tr style="background: #f5f5f5;">
                                <th style="padding: 10px; text-align: left;">代碼</th>
                                <th style="padding: 10px; text-align: left;">名稱</th>
                                <th style="padding: 10px; text-align: left;">價格</th>
                                <th style="padding: 10px; text-align: left;">漲幅</th>
                                <th style="padding: 10px; text-align: left;">成交量</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stock_rows}
                        </tbody>
                    </table>
                    
                    <p style="margin-top: 20px; color: #666; font-size: 12px;">
                        💡 這些股票已自動加入 ORB 監控清單，系統將持續追蹤進出場時機。
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # 發送
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_user, email_pass)
                server.send_message(msg)
            
            logger.info(f"📧 強勢股通知已發送")
            
        except Exception as e:
            logger.error(f"發送通知失敗: {e}")
    
    def get_status(self) -> Dict:
        """取得掃描器狀態"""
        return {
            "is_running": self.is_running,
            "last_scan_date": self.last_scan_date.isoformat() if self.last_scan_date else None,
            "found_stocks_count": len(self.found_stocks),
            "found_stocks": self.found_stocks[-10:],  # 最近 10 檔
            "settings": {
                "min_change_pct": self.min_change_pct,
                "min_volume": self.min_volume,
                "min_price": self.min_price,
                "max_price": self.max_price,
                "scan_times": ["09:30", "10:00", "10:30"]
            }
        }
    
    async def manual_scan(self) -> List[Dict]:
        """手動觸發掃描"""
        logger.info("📊 手動觸發市場掃描...")
        await self._scan_market()
        return self.found_stocks


# 單例實例
market_scanner = MarketScanner()
