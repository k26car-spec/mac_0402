import logging
import json
import os
from datetime import datetime
import asyncio
import httpx

logger = logging.getLogger(__name__)

class TWSECalendar:
    def __init__(self):
        self.holiday_url = "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule"
        # 緩存文件路徑
        self.cache_file = os.path.join(os.path.dirname(__file__), "twse_holidays.json")
        # 內存快取 (set of date strings 'YYYY-MM-DD')
        self.holidays = set()
        self._loaded = False
        self._lock = asyncio.Lock()

    def _roc_to_west_date(self, roc_date_str: str) -> str:
        """轉換民國年月日 (如 1150101) 為西元 (如 2026-01-01)"""
        if len(roc_date_str) < 7:
            return ""
        try:
            year = int(roc_date_str[:-4]) + 1911
            month = roc_date_str[-4:-2]
            day = roc_date_str[-2:]
            return f"{year}-{month}-{day}"
        except ValueError:
            return ""

    async def _fetch_from_api(self):
        """從金管會/證交所 API 獲取休假日"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.holiday_url)
                if response.status_code == 200:
                    data = response.json()
                    holidays = set()
                    for item in data:
                        name = item.get("Name", "")
                        desc = item.get("Description", "")
                        # 排除掉「開始交易」或特定文字，因為那些反而是交易日，大部分列表中的是休市日
                        if "開始交易" in name or "開始交易" in desc:
                            continue
                            
                        date_str = item.get("Date", "")
                        west_date = self._roc_to_west_date(date_str)
                        if west_date:
                            holidays.add(west_date)
                    
                    if holidays:
                        self.holidays = holidays
                        # 寫入本地快取文件
                        with open(self.cache_file, 'w') as f:
                            json.dump(list(self.holidays), f)
                        self._loaded = True
                        logger.info(f"[TWSECalendar] 成功從 API 更新了 {len(holidays)} 天休假日")
                        return True
        except Exception as e:
            logger.error(f"[TWSECalendar] 抓取休市日曆失敗: {e}")
        return False

    async def _load_cache(self):
        """從本地快取加載"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.holidays = set(data)
                    self._loaded = True
                    logger.info(f"[TWSECalendar] 成功從本地快取載入 {len(self.holidays)} 天休假日")
                    return True
            except Exception as e:
                logger.error(f"[TWSECalendar] 讀取本地快取失敗: {e}")
        return False

    async def initialize(self):
        """初始化日曆 (優先讀快取，若無則抓 API)"""
        async with self._lock:
            if self._loaded:
                return

            # 先嘗試從本地加載
            if await self._load_cache():
                # 異步更新 API (不阻塞)
                asyncio.create_task(self._fetch_from_api())
            else:
                # 本地沒有，必須等 API
                await self._fetch_from_api()
        
    def is_trading_day(self, date: datetime = None) -> bool:
        """
        判斷是否為交易日
        1. 週末 (星期六=5, 星期日=6) 預設為非交易日 
           (注意：台灣偶爾有補班補課，但股市通常不補開盤，若有例外，API資料會有影響)
        2. 檢查是否在休市名單內
        """
        if date is None:
            date = datetime.now()
            
        # 週末不開盤
        if date.weekday() >= 5:
            return False
            
        date_str = date.strftime("%Y-%m-%d")
        
        # 若在休市名單內，必定不開盤
        if date_str in self.holidays:
            return False
            
        return True
        
    def is_market_open(self, now: datetime = None) -> bool:
        """
        判斷當下是否為盤中時間 (09:00 - 13:30)，且為交易日
        """
        if now is None:
            now = datetime.now()
            
        if not self.is_trading_day(now):
            return False
            
        current_time = now.time()
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("13:30", "%H:%M").time()
        
        return market_open <= current_time <= market_close

# 全域單例
twse_calendar = TWSECalendar()
