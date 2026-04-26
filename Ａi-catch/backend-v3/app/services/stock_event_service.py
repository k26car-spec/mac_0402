"""
股票事件與法人連買資訊服務
包含：月營收公告、法說會、季財報、除權息、法人連買天數
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf

logger = logging.getLogger(__name__)


class StockEventService:
    """股票事件服務"""
    
    # 月營收公告日（通常每月10日前公告）
    REVENUE_ANNOUNCE_DAY = 10
    
    # 季財報公告日
    QUARTERLY_REPORT_DATES = {
        'Q1': '05-15',  # 第一季：5/15前
        'Q2': '08-14',  # 第二季：8/14前
        'Q3': '11-14',  # 第三季：11/14前
        'Q4': '03-31',  # 年報：隔年3/31前
    }
    
    @staticmethod
    def get_next_revenue_date() -> str:
        """取得下次月營收公告日期"""
        today = datetime.now()
        
        if today.day <= StockEventService.REVENUE_ANNOUNCE_DAY:
            # 本月還沒公告
            announce_date = today.replace(day=StockEventService.REVENUE_ANNOUNCE_DAY)
        else:
            # 已過公告日，等下個月
            if today.month == 12:
                announce_date = today.replace(year=today.year + 1, month=1, day=StockEventService.REVENUE_ANNOUNCE_DAY)
            else:
                announce_date = today.replace(month=today.month + 1, day=StockEventService.REVENUE_ANNOUNCE_DAY)
        
        return announce_date.strftime('%Y-%m-%d')
    
    @staticmethod
    def get_last_revenue_month() -> str:
        """取得最近公告的營收月份"""
        today = datetime.now()
        
        if today.day >= StockEventService.REVENUE_ANNOUNCE_DAY:
            # 本月已公告，顯示上個月營收
            if today.month == 1:
                return f"{today.year - 1}年12月"
            else:
                return f"{today.year}年{today.month - 1}月"
        else:
            # 本月尚未公告，顯示上上個月營收
            if today.month <= 2:
                return f"{today.year - 1}年{12 + today.month - 2}月"
            else:
                return f"{today.year}年{today.month - 2}月"
    
    @staticmethod
    def get_current_quarter() -> str:
        """取得當前財報季度"""
        today = datetime.now()
        month = today.month
        
        if month <= 3:
            return "Q4"  # 等Q4(年報)
        elif month <= 5:
            return "Q1"  # 等Q1
        elif month <= 8:
            return "Q2"  # 等Q2
        elif month <= 11:
            return "Q3"  # 等Q3
        else:
            return "Q4"  # 等Q4(年報)
    
    @staticmethod
    def get_next_quarterly_report_date() -> Tuple[str, str]:
        """取得下次季財報公告日期"""
        today = datetime.now()
        year = today.year
        
        for quarter, date_str in StockEventService.QUARTERLY_REPORT_DATES.items():
            month, day = map(int, date_str.split('-'))
            
            if quarter == 'Q4':
                report_date = datetime(year + 1, month, day)
            else:
                report_date = datetime(year, month, day)
            
            if report_date > today:
                return quarter, report_date.strftime('%Y-%m-%d')
        
        # 如果都過了，返回明年Q1
        return 'Q1', f"{year + 1}-05-15"
    
    @staticmethod
    def get_dividend_info(stock_code: str) -> Dict:
        """
        取得除權息資訊
        
        Returns:
            {
                'ex_dividend_date': str,  # 除息日
                'ex_rights_date': str,     # 除權日
                'cash_dividend': float,    # 現金股利
                'stock_dividend': float,   # 股票股利
                'dividend_yield': float    # 殖利率
            }
        """
        try:
            # 使用 patch_yfinance 取得正確的後綴
            try:
                from app.patch_yfinance import fix_taiwan_symbol
                symbol = fix_taiwan_symbol(stock_code)
            except ImportError:
                symbol = f"{stock_code}.TW"
            
            ticker = yf.Ticker(symbol)
            
            # 取得股利資訊
            dividends = ticker.dividends
            
            if dividends.empty:
                return {}
            
            # 取得最近一次股利
            last_dividend = dividends.iloc[-1] if len(dividends) > 0 else 0
            last_date = dividends.index[-1].strftime('%Y-%m-%d') if len(dividends) > 0 else ''
            
            # 取得當前價格計算殖利率
            info = ticker.info
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            
            # 計算年度股利總和
            year_ago = datetime.now() - timedelta(days=365)
            
            # 處理時區問題：將 index 轉換為無時區格式進行比較
            try:
                # 將 dividends index 轉換為無時區的 datetime
                dividends_reset = dividends.copy()
                dividends_reset.index = dividends_reset.index.tz_localize(None) if dividends_reset.index.tz is not None else dividends_reset.index
                recent_dividends = dividends_reset[dividends_reset.index >= year_ago]
            except Exception:
                # 如果轉換失敗，使用最後一筆股利
                recent_dividends = dividends.tail(4)  # 取最近4次股利
            
            annual_dividend = recent_dividends.sum() if not recent_dividends.empty else 0
            
            dividend_yield = (annual_dividend / current_price * 100) if current_price > 0 else 0
            
            return {
                'last_ex_date': last_date,
                'last_dividend': float(last_dividend),
                'annual_dividend': float(annual_dividend),
                'dividend_yield': round(dividend_yield, 2)
            }
            
        except Exception as e:
            logger.warning(f"取得 {stock_code} 除權息資訊失敗: {e}")
            return {}
    
    @staticmethod
    def get_events_summary(stock_code: str) -> Dict:
        """取得股票事件摘要"""
        quarter, quarter_date = StockEventService.get_next_quarterly_report_date()
        
        dividend_info = StockEventService.get_dividend_info(stock_code)
        
        return {
            'next_revenue_date': StockEventService.get_next_revenue_date(),
            'last_revenue_month': StockEventService.get_last_revenue_month(),
            'next_quarterly_report': {
                'quarter': quarter,
                'deadline': quarter_date
            },
            'dividend': dividend_info
        }


class InstitutionalTradingService:
    """法人連買資訊服務"""
    
    # 快取法人資料
    _cache: Dict[str, Dict] = {}
    _cache_time: Dict[str, datetime] = {}
    CACHE_TTL = 1800  # 30分鐘
    
    @staticmethod
    def get_consecutive_days(stock_code: str) -> Dict[str, int]:
        """
        取得三大法人連續買賣天數
        
        Returns:
            {
                'foreign': int,    # 外資連買天數 (負數為連賣)
                'trust': int,      # 投信連買天數
                'dealer': int,     # 自營商連買天數
                'total': int       # 合計連買天數
            }
        """
        try:
            # 嘗試使用 twstock 或爬蟲取得歷史資料
            # 這裡使用模擬邏輯，實際需要連接證交所 API
            
            # 檢查快取
            cache_key = f"consecutive_{stock_code}"
            if cache_key in InstitutionalTradingService._cache:
                cache_time = InstitutionalTradingService._cache_time.get(cache_key)
                if cache_time and (datetime.now() - cache_time).seconds < InstitutionalTradingService.CACHE_TTL:
                    return InstitutionalTradingService._cache[cache_key]
            
            # 從 comprehensive analyzer 取得今日資料
            # 這裡需要實際的歷史資料來計算連續天數
            # 目前先返回佔位資料
            
            result = {
                'foreign': 0,
                'trust': 0,
                'dealer': 0,
                'total': 0,
                'note': '需連接證交所歷史資料'
            }
            
            # 更新快取
            InstitutionalTradingService._cache[cache_key] = result
            InstitutionalTradingService._cache_time[cache_key] = datetime.now()
            
            return result
            
        except Exception as e:
            logger.error(f"取得 {stock_code} 法人連買天數失敗: {e}")
            return {'foreign': 0, 'trust': 0, 'dealer': 0, 'total': 0}
    
    @staticmethod
    def get_institutional_trend(stock_code: str, inst_data: Dict) -> Dict:
        """
        根據法人買賣超資料判斷趨勢
        
        Args:
            stock_code: 股票代碼
            inst_data: 法人買賣超資料 {'foreign_net': x, 'trust_net': y, 'dealer_net': z}
        
        Returns:
            趨勢分析結果
        """
        foreign = inst_data.get('foreign_net', 0)
        trust = inst_data.get('trust_net', 0)
        dealer = inst_data.get('dealer_net', 0)
        total = foreign + trust + dealer
        
        # 判斷主力態度
        if total > 0:
            if foreign > 0 and trust > 0:
                trend = "外資投信同步買超"
                strength = "強"
            elif foreign > 0:
                trend = "外資買超主導"
                strength = "中"
            elif trust > 0:
                trend = "投信買超主導"
                strength = "中"
            else:
                trend = "自營商買超"
                strength = "弱"
        elif total < 0:
            if foreign < 0 and trust < 0:
                trend = "外資投信同步賣超"
                strength = "強"
            elif foreign < 0:
                trend = "外資賣超主導"
                strength = "中"
            elif trust < 0:
                trend = "投信賣超主導"
                strength = "中"
            else:
                trend = "自營商賣超"
                strength = "弱"
        else:
            trend = "法人觀望"
            strength = "中性"
        
        return {
            'trend': trend,
            'strength': strength,
            'foreign_direction': '買' if foreign > 0 else '賣' if foreign < 0 else '平',
            'trust_direction': '買' if trust > 0 else '賣' if trust < 0 else '平',
            'dealer_direction': '買' if dealer > 0 else '賣' if dealer < 0 else '平',
            'consecutive_days': InstitutionalTradingService.get_consecutive_days(stock_code)
        }


# 全域實例
stock_event_service = StockEventService()
institutional_service = InstitutionalTradingService()


def get_stock_events(stock_code: str) -> Dict:
    """取得股票事件資訊"""
    return stock_event_service.get_events_summary(stock_code)


def get_institutional_analysis(stock_code: str, inst_data: Dict) -> Dict:
    """取得法人分析"""
    return institutional_service.get_institutional_trend(stock_code, inst_data)
