"""
台灣證交所API - 取得處置股票清單
使用正確的API端點和資料格式
"""
import requests
import logging
import re
from datetime import datetime, date
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


# 已知的處置股/注意股清單（手動維護，每日更新）
# 這是備用清單，API 無法取得時使用
KNOWN_DISPOSITION_STOCKS = {
    '3163': {'name': '波若威', 'reason': '股價波動過大'},
    '3093': {'name': '港建', 'reason': '股價波動過大'},
    '6743': {'name': '安集', 'reason': '股價波動過大'},
    '1781': {'name': '合世生醫', 'reason': '股價波動過大'},
}

KNOWN_ATTENTION_STOCKS = {
    '3163', '3093', '6743', '1781', '2936', '6869', '3095', '6813',
}


class TWSeAPI:
    """台灣證交所API"""
    
    BASE_URL = "https://www.twse.com.tw"
    MOPS_URL = "https://mops.twse.com.tw"
    
    @staticmethod
    def _get_session():
        """取得帶有正確 headers 的 session"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        return session
    
    @staticmethod
    def get_attention_stocks() -> Set[str]:
        """
        取得注意股票清單
        
        Returns:
            Set of stock codes
        """
        attention_stocks = set()
        
        try:
            # 方法1: 使用 TWSE API
            session = TWSeAPI._get_session()
            
            # 嘗試從公告頁面取得
            url = f"{TWSeAPI.BASE_URL}/zh/announcement/attention"
            response = session.get(url, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                # 解析 HTML 找出股票代碼
                html = response.text
                # 找出4位數股票代碼
                codes = re.findall(r'\b(\d{4})\b', html)
                for code in codes:
                    if code.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                        attention_stocks.add(code)
            
            logger.info(f"取得注意股票(API) {len(attention_stocks)} 檔")
            
        except Exception as e:
            logger.warning(f"取得注意股票失敗(API): {e}")
        
        # 合併已知清單
        attention_stocks.update(KNOWN_ATTENTION_STOCKS)
        
        logger.info(f"取得注意股票(合併) {len(attention_stocks)} 檔")
        return attention_stocks
    
    @staticmethod
    def get_disposition_stocks() -> Dict[str, Dict]:
        """
        取得處置股票清單及處置措施
        
        Returns:
            {
                'stock_code': {
                    'name': str,
                    'start_date': str,
                    'measures': list,
                    'reason': str
                }
            }
        """
        disposition_stocks = {}
        
        try:
            # 方法1: 嘗試從 TWSE 公告取得
            session = TWSeAPI._get_session()
            
            # 處置股票公告頁面
            url = f"{TWSeAPI.BASE_URL}/zh/announcement/disposal"
            response = session.get(url, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                html = response.text
                # 找出4位數股票代碼和名稱
                # 格式通常是: 代碼 名稱
                patterns = re.findall(r'(\d{4})\s*[<>\w]*\s*([\u4e00-\u9fff]+)', html)
                for code, name in patterns:
                    if code.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                        disposition_stocks[code] = {
                            'name': name,
                            'start_date': '',
                            'measures': [],
                            'reason': '處置中'
                        }
            
            logger.info(f"取得處置股票(API) {len(disposition_stocks)} 檔")
            
        except Exception as e:
            logger.warning(f"取得處置股票失敗(API): {e}")
        
        # 合併已知清單
        for code, info in KNOWN_DISPOSITION_STOCKS.items():
            if code not in disposition_stocks:
                disposition_stocks[code] = info
        
        logger.info(f"取得處置股票(合併) {len(disposition_stocks)} 檔")
        return disposition_stocks
    
    @staticmethod
    def get_full_cash_delivery_stocks() -> Set[str]:
        """
        取得全額交割股清單
        
        Returns:
            Set of stock codes
        """
        full_cash_stocks = set()
        
        try:
            session = TWSeAPI._get_session()
            
            # 全額交割股公告
            url = f"{TWSeAPI.BASE_URL}/zh/announcement/tradingAdjustment"
            response = session.get(url, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                html = response.text
                # 找出變更交易方式的股票
                codes = re.findall(r'\b(\d{4})\b', html)
                for code in codes:
                    if code.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                        full_cash_stocks.add(code)
            
            logger.info(f"取得全額交割股 {len(full_cash_stocks)} 檔")
            
        except Exception as e:
            logger.warning(f"取得全額交割股失敗: {e}")
        
        return full_cash_stocks
    
    @staticmethod
    def get_all_abnormal_stocks() -> Dict[str, List[str]]:
        """
        取得所有異常股票（整合）
        """
        return {
            'attention': list(TWSeAPI.get_attention_stocks()),
            'disposition': list(TWSeAPI.get_disposition_stocks().keys()),
            'full_cash': list(TWSeAPI.get_full_cash_delivery_stocks())
        }


class AbnormalStockChecker:
    """異常股票檢查器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.attention_stocks: Set[str] = set()
        self.disposition_stocks: Dict[str, Dict] = {}
        self.full_cash_stocks: Set[str] = set()
        self.last_update = None
        self._initialized = True
        
        # 立即更新
        self.update()
    
    def update(self):
        """更新異常股票清單"""
        try:
            logger.info("更新異常股票清單...")
            
            self.attention_stocks = TWSeAPI.get_attention_stocks()
            self.disposition_stocks = TWSeAPI.get_disposition_stocks()
            self.full_cash_stocks = TWSeAPI.get_full_cash_delivery_stocks()
            self.last_update = datetime.now()
            
            total = (len(self.attention_stocks) + 
                    len(self.disposition_stocks) + 
                    len(self.full_cash_stocks))
            
            logger.info(f"✅ 異常股票清單已更新，共 {total} 檔")
            
        except Exception as e:
            logger.error(f"更新異常股票清單失敗: {e}")
    
    def add_disposition_stock(self, code: str, name: str = '', reason: str = ''):
        """手動加入處置股"""
        self.disposition_stocks[code] = {
            'name': name,
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'measures': [],
            'reason': reason or '手動加入'
        }
        logger.info(f"✅ 已加入處置股: {code} {name}")
    
    def add_attention_stock(self, code: str):
        """手動加入注意股"""
        self.attention_stocks.add(code)
        logger.info(f"✅ 已加入注意股: {code}")
    
    def is_abnormal(self, stock_code: str) -> Tuple[bool, List[str]]:
        """
        檢查股票是否異常
        
        Returns:
            (是否異常, 異常類型列表)
        """
        reasons = []
        
        if stock_code in self.attention_stocks:
            reasons.append("注意股票")
        
        if stock_code in self.disposition_stocks:
            measures = self.disposition_stocks[stock_code].get('measures', [])
            if measures:
                reasons.append(f"處置股票({','.join(measures)})")
            else:
                reasons.append("處置股票")
        
        if stock_code in self.full_cash_stocks:
            reasons.append("全額交割股")
        
        return len(reasons) > 0, reasons
    
    def should_skip(self, stock_code: str) -> bool:
        """是否應該跳過此股票"""
        if stock_code in self.disposition_stocks or stock_code in self.full_cash_stocks:
            return True
        return False
    
    def get_warning_label(self, stock_code: str) -> str:
        """取得警示標籤"""
        is_abnormal, reasons = self.is_abnormal(stock_code)
        if is_abnormal:
            return f"[!] {', '.join(reasons)}"
        return ""
    
    def get_summary(self) -> Dict:
        """取得摘要"""
        return {
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'attention_count': len(self.attention_stocks),
            'disposition_count': len(self.disposition_stocks),
            'full_cash_count': len(self.full_cash_stocks),
            'attention_stocks': list(self.attention_stocks),
            'disposition_stocks': list(self.disposition_stocks.keys()),
            'full_cash_stocks': list(self.full_cash_stocks)
        }


# 全域實例
abnormal_checker = AbnormalStockChecker()


def check_stock_abnormal(stock_code: str) -> Tuple[bool, List[str]]:
    """快速檢查股票是否異常"""
    return abnormal_checker.is_abnormal(stock_code)


def get_abnormal_warning(stock_code: str) -> str:
    """取得異常警示文字"""
    return abnormal_checker.get_warning_label(stock_code)


def add_disposition_stock(code: str, name: str = '', reason: str = ''):
    """手動加入處置股"""
    abnormal_checker.add_disposition_stock(code, name, reason)


def add_attention_stock(code: str):
    """手動加入注意股"""
    abnormal_checker.add_attention_stock(code)
