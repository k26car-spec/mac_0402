"""
新聞分析服務 - 整合 IEK + Perplexity + 其他新聞來源
支援手動更新 Perplexity 新聞（避免 API 費用）
"""
import json
import os
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# === 股票代碼對照表（產業新聞關鍵詞對應） ===
KEYWORD_STOCK_MAP = {
    # 半導體
    '台積電': '2330', '台積': '2330', 'TSMC': '2330',
    '聯發科': '2454', 'MediaTek': '2454',
    '聯電': '2303', '日月光': '3711', '力成': '6239',
    '矽品': '2325', '世芯': '3661', '創意': '3443',
    '祥碩': '5269', '信驊': '5274', '瑞昱': '2379',
    '聯詠': '3034', '群聯': '8299', '華邦電': '2344',
    # 測試/封裝
    '欣銓': '3264', '京元電': '2449', '南茂': '8150', 
    '穎崴': '6515', '雍智': '6955', '精測': '6510',
    
    # AI / 伺服器
    '廣達': '2382', '緯創': '3231', '英業達': '2356',
    '緯穎': '6669', '神達': '3706', '技嘉': '2376',
    '微星': '2377', '華碩': '2357', '仁寶': '2324',
    
    # 電子代工
    '鴻海': '2317', '和碩': '4938', '台達電': '2308',
    '光寶科': '2301', '研華': '2395',
    
    # 零組件
    '國巨': '2327', '欣興': '3037', '臻鼎': '4958',
    '景碩': '3189', '嘉澤': '3533', '健策': '3653',
    '雙鴻': '3324', '奇鋐': '3017', 'BBU': None,
    
    # 面板 / 光電
    '群創': '3481', '友達': '2409', '彩晶': '6116',
    '瀚宇彩晶': '6116', '元太': '8069', '達興': '5234',
    '榮創': '3455', '凌巨': '8105', '南電': '8046',
    '面板股': None, 'TV面板': None,
    
    # 被動元件
    '華新科': '2492', '奇力新': '2456', '大毅': '2478',
    '禾伸堂': '3026', '凱美': '2375',
    
    # 光通訊 / 矽光子
    '矽光子': None, '光通訊': None, '聯鈞': '3450',
    '波若威': '3163', '華星光': '4979', '眾達': '4977',
    '上銓': '3363',
    
    # 航運
    '長榮': '2603', '陽明': '2609', '萬海': '2615',
    '長榮航': '2618', '華航': '2610',
    
    # 金融
    '國泰金': '2882', '富邦金': '2881', '中信金': '2891',
    '兆豐金': '2886', '玉山金': '2884', '台新金': '2887',
    '第一金': '2892', '華南金': '2880', '開發金': '2883',
    
    # 汽車 / 電動車
    '鴻華先進': '2258', '東陽': '1319', '裕隆': '2201',
    '和泰車': '2207', '堤維西': '1522',
    
    # 機械
    '易發': '8045', '上銀': '2049', '大銀微系統': '4576',
    
    # 其他
    '金益鼎': '8390', '東聯': '1710', '晶呈': '4768',
    '太普高': '4947', '駱泰': '8415',
    
    # 營建 / 無塵室
    '亞翔': '6139', '漢唐': '2404', '帆宣': '6196',
    '聖暉': '5765', '千附': '8383',
    
    # 半導體材料
    '中砂': '1560', '環球晶': '6488', '合晶': '6182',
    
    # PCB
    '燿華': '2367', '嘉聯益': '6153', '華通': '2313',
}

# 產業關鍵詞對應股票群組（基礎版）
INDUSTRY_KEYWORDS = {
    '半導體': ['2330', '2454', '2303', '3711', '6239', '3661', '3443', '2379', '3034'],
    'AI': ['2382', '3231', '2356', '6669', '3706', '2376', '2377'],
    '矽光子': ['3450', '3163', '4979', '4977', '3363'],
    '伺服器': ['2382', '3231', '6669', '3706', '2376', '2377', '2357'],
    '電動車': ['2258', '1319', '2201', '2207', '1522'],
    '航運': ['2603', '2609', '2615'],
    '記憶體': ['2337', '2344', '8299', '3450'],
    '散熱': ['3324', '3017'],
    'PCB': ['3037', '4958', '3189'],
    '被動元件': ['2327'],
}

# === 完整產業-股票詳細映射表 ===
INDUSTRY_STOCK_DETAILS = {
    'AI伺服器': {
        'description': 'AI server and GPU related stocks',
        'stocks': [
            {'code': '2382', 'name': '廣達', 'role': '代工組裝', 'tier': 1},
            {'code': '3231', 'name': '緯創', 'role': '代工組裝', 'tier': 1},
            {'code': '2356', 'name': '英業達', 'role': '代工組裝', 'tier': 2},
            {'code': '6669', 'name': '緯穎', 'role': '雲端伺服器', 'tier': 1},
            {'code': '3706', 'name': '神達', 'role': 'AI系統整合', 'tier': 2},
            {'code': '2376', 'name': '技嘉', 'role': 'GPU伺服器', 'tier': 2},
            {'code': '2377', 'name': '微星', 'role': 'GPU系統', 'tier': 3},
        ],
        'related_concepts': ['輝達供應鏈', '雲端運算', 'ChatGPT'],
    },
    '半導體': {
        'description': 'Semiconductor manufacturing and design',
        'stocks': [
            {'code': '2330', 'name': '台積電', 'role': '晶圓代工', 'tier': 1},
            {'code': '2454', 'name': '聯發科', 'role': 'IC設計', 'tier': 1},
            {'code': '2303', 'name': '聯電', 'role': '晶圓代工', 'tier': 2},
            {'code': '3711', 'name': '日月光', 'role': '封測', 'tier': 1},
            {'code': '3661', 'name': '世芯-KY', 'role': 'ASIC設計', 'tier': 1},
            {'code': '3443', 'name': '創意', 'role': 'IC設計服務', 'tier': 2},
            {'code': '6239', 'name': '力成', 'role': '封測', 'tier': 2},
        ],
        'related_concepts': ['先進製程', 'CoWoS', '封測'],
    },
    '矽光子': {
        'description': 'Silicon photonics and optical communication',
        'stocks': [
            {'code': '3450', 'name': '聯鈞', 'role': '光收發模組', 'tier': 1},
            {'code': '3163', 'name': '波若威', 'role': '光通訊元件', 'tier': 1},
            {'code': '4979', 'name': '華星光', 'role': '光纖連接器', 'tier': 2},
            {'code': '4977', 'name': '眾達-KY', 'role': '光通訊IC', 'tier': 2},
            {'code': '3363', 'name': '上諭', 'role': '光通訊模組', 'tier': 3},
        ],
        'related_concepts': ['光通訊', 'AI資料中心', '高速傳輸'],
    },
    '記憶體': {
        'description': 'Memory chips including DRAM and NAND',
        'stocks': [
            {'code': '2337', 'name': '旺宏', 'role': 'NOR Flash', 'tier': 2},
            {'code': '2344', 'name': '華邦電', 'role': 'DRAM/Flash', 'tier': 1},
            {'code': '8299', 'name': '群聯', 'role': 'Flash控制IC', 'tier': 1},
            {'code': '3450', 'name': '南亞科', 'role': 'DRAM', 'tier': 1},
        ],
        'related_concepts': ['HBM', 'DDR5', 'NAND'],
    },
    '散熱': {
        'description': 'Thermal management solutions',
        'stocks': [
            {'code': '3324', 'name': '雙鴻', 'role': '散熱模組', 'tier': 1},
            {'code': '3017', 'name': '奇鋐', 'role': '散熱模組', 'tier': 1},
            {'code': '6279', 'name': '胡連', 'role': '散熱材料', 'tier': 2},
        ],
        'related_concepts': ['液冷', '熱管', 'AI散熱'],
    },
    '電動車': {
        'description': 'Electric vehicle and related components',
        'stocks': [
            {'code': '2258', 'name': '鴻華先進', 'role': '電動車製造', 'tier': 1},
            {'code': '2201', 'name': '裕隆', 'role': '車廠', 'tier': 1},
            {'code': '1319', 'name': '東陽', 'role': '車燈', 'tier': 2},
            {'code': '2207', 'name': '和泰車', 'role': '車商', 'tier': 2},
        ],
        'related_concepts': ['自駕', '電池', '充電樁'],
    },
    '金融': {
        'description': 'Financial institutions',
        'stocks': [
            {'code': '2882', 'name': '國泰金', 'role': '金控', 'tier': 1},
            {'code': '2881', 'name': '富邦金', 'role': '金控', 'tier': 1},
            {'code': '2891', 'name': '中信金', 'role': '金控', 'tier': 1},
            {'code': '2886', 'name': '兆豐金', 'role': '金控', 'tier': 2},
        ],
        'related_concepts': ['升息', '壽險', '銀行'],
    },
    'PCB': {
        'description': 'Printed circuit board manufacturing',
        'stocks': [
            {'code': '3037', 'name': '欣興', 'role': 'ABF載板', 'tier': 1},
            {'code': '4958', 'name': '臻鼎-KY', 'role': 'PCB製造', 'tier': 1},
            {'code': '3189', 'name': '景碩', 'role': 'IC載板', 'tier': 1},
            {'code': '3533', 'name': '嘉澤', 'role': '連接器', 'tier': 2},
        ],
        'related_concepts': ['ABF載板', 'HDI', 'AI伺服器PCB'],
    },
}

# 股票代碼到名稱的快速查找表（含中小型股）
STOCK_CODE_TO_NAME = {
    # 半導體權值
    '2330': '台積電', '2454': '聯發科', '2303': '聯電', '3711': '日月光',
    # AI伺服器
    '2382': '廣達', '3231': '緯創', '2356': '英業達', '6669': '緯穎',
    '3706': '神達', '2376': '技嘉', '2377': '微星', '2357': '華碩',
    '2317': '鴻海', '4938': '和碩', '2308': '台達電', '2301': '光寶科',
    # 矽光子
    '3450': '聯鈞', '3163': '波若威', '4979': '華星光', '4977': '眾達-KY',
    # 記憶體
    '2337': '旺宏', '2344': '華邦電', '8299': '群聯',
    # 散熱
    '3324': '雙鴻', '3017': '奇鋐',
    # 航運
    '2603': '長榮', '2609': '陽明', '2615': '萬海',
    # 金融
    '2882': '國泰金', '2881': '富邦金', '2891': '中信金', '2886': '兆豐金',
    # PCB
    '3037': '欣興', '4958': '臻鼎-KY', '3189': '景碩',
    # 電動車
    '2258': '鴻華先進', '2201': '裕隆', '1319': '東陽',
    # IC設計服務
    '3661': '世芯-KY', '3443': '創意', '6239': '力成',
    
    # === 新增：半導體測試/封測（中小型股）===
    '2449': '京元電子', '3264': '欣銓', '8021': '尖點', '2351': '順德',
    '6147': '頎邦', '2369': '菱生', '6215': '和桐',
    
    # === 新增：LED/驅動IC ===
    '5472': '聚積', '2393': '億光', '3217': '優群', '3545': '敦泰',
    
    # === 新增：PCB/軟板（中小型股）===
    '5498': '凱崴', '6153': '嘉聯益', '3553': '力達-KY', '8046': '南電',
    
    # === 新增：其他熱門中小型股 ===
    '6770': '力積電', '3529': '力旺', '6669': '緯穎', '3017': '奇鋐',
}


class NewsAnalysisService:
    """新聞分析與股票推薦服務"""
    
    def __init__(self):
        self.data_dir = Path("/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/data/news")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.perplexity_file = self.data_dir / "perplexity_news.json"
        self.manual_news_file = self.data_dir / "manual_news.json"
        
        # 新聞快取
        self._iek_cache: Optional[List[Dict]] = None
        self._iek_cache_time: Optional[datetime] = None
        self._cache_ttl = 1800  # 30 分鐘
    
    # === IEK 新聞 ===
    
    def get_iek_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得 IEK 產業新聞（即時爬取）"""
        from app.services.iek_news_crawler import iek_crawler
        
        # 如果沒有快取或快取過期，強制刷新
        if self._iek_cache is None or len(self._iek_cache) == 0:
            force_refresh = True
        
        # 檢查快取
        if not force_refresh and self._iek_cache and self._iek_cache_time:
            elapsed = (datetime.now() - self._iek_cache_time).seconds
            if elapsed < self._cache_ttl and len(self._iek_cache) > 0:
                logger.info(f"使用 IEK 新聞快取 ({len(self._iek_cache)} 則)")
                return self._iek_cache
        
        # 直接呼叫爬蟲
        news = iek_crawler.fetch_daily_news(force_refresh=True)
        
        # 更新快取
        self._iek_cache = news
        self._iek_cache_time = datetime.now()
        
        logger.info(f"✅ 取得 IEK 新聞 {len(news)} 則")
        return news
    
    # === 外部新聞 (台視財經、CMoney) ===
    
    def get_external_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得外部新聞來源 (台視財經、CMoney)"""
        try:
            from app.services.multi_source_news_crawler import multi_source_crawler
            return multi_source_crawler.get_all_news(force_refresh)
        except Exception as e:
            logger.error(f"取得外部新聞失敗: {e}")
            return []
    
    def get_ttv_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得台視財經新聞"""
        try:
            from app.services.multi_source_news_crawler import get_ttv_news
            return get_ttv_news(force_refresh)
        except Exception as e:
            logger.error(f"取得台視財經新聞失敗: {e}")
            return []
    
    def get_cmoney_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得 CMoney 新聞"""
        try:
            from app.services.multi_source_news_crawler import get_cmoney_news
            return get_cmoney_news(force_refresh)
        except Exception as e:
            logger.error(f"取得 CMoney 新聞失敗: {e}")
            return []
    
    def get_udn_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得經濟日報新聞（熱門排行榜）"""
        try:
            from app.services.multi_source_news_crawler import get_udn_news
            return get_udn_news(force_refresh)
        except Exception as e:
            logger.error(f"取得經濟日報新聞失敗: {e}")
            return []
    
    def get_technews_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得科技新報新聞"""
        try:
            from app.services.multi_source_news_crawler import get_technews_news
            return get_technews_news(force_refresh, pages=2)
        except Exception as e:
            logger.error(f"取得科技新報新聞失敗: {e}")
            return []
    
    def get_pocket_news(self, force_refresh: bool = False) -> List[Dict]:
        """取得口袋證券研報"""
        try:
            from app.services.pocket_crawler import get_pocket_news
            return get_pocket_news(force_refresh)
        except Exception as e:
            logger.error(f"取得口袋證券研報失敗: {e}")
            return []
    
    # === Perplexity 新聞（手動更新）===
    
    def get_perplexity_news(self) -> List[Dict]:
        """取得 Perplexity 新聞（從本地 JSON 檔案）"""
        if not self.perplexity_file.exists():
            return []
        
        try:
            with open(self.perplexity_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('news', [])
        except Exception as e:
            logger.error(f"讀取 Perplexity 新聞失敗: {e}")
            return []
    
    def save_perplexity_news(self, news_items: List[Dict]) -> bool:
        """儲存 Perplexity 新聞（手動輸入）"""
        try:
            data = {
                'updated_at': datetime.now().isoformat(),
                'source': 'perplexity',
                'news': news_items
            }
            with open(self.perplexity_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 儲存 Perplexity 新聞 {len(news_items)} 則")
            return True
        except Exception as e:
            logger.error(f"儲存 Perplexity 新聞失敗: {e}")
            return False
    
    def add_perplexity_news(self, title: str, content: str = '', stocks: List[str] = None, 
                            sentiment: str = 'neutral', source_url: str = '') -> Dict:
        """新增一則 Perplexity 新聞"""
        existing = self.get_perplexity_news()
        
        new_item = {
            'id': f"perplexity_{len(existing)+1}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'title': title,
            'content': content,
            'stocks': stocks or [],
            'sentiment': sentiment,
            'source': 'Perplexity AI',
            'source_url': source_url,
            'created_at': datetime.now().isoformat(),
        }
        
        existing.insert(0, new_item)  # 插入最前面
        self.save_perplexity_news(existing)
        
        return new_item
    
    # === 其他手動新聞 ===
    
    def get_manual_news(self) -> List[Dict]:
        """取得手動輸入的新聞"""
        if not self.manual_news_file.exists():
            return []
        
        try:
            with open(self.manual_news_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('news', [])
        except Exception as e:
            logger.error(f"讀取手動新聞失敗: {e}")
            return []
    
    def add_manual_news(self, title: str, content: str = '', stocks: List[str] = None,
                        sentiment: str = 'neutral', category: str = '其他') -> Dict:
        """新增手動新聞"""
        existing = self.get_manual_news()
        
        new_item = {
            'id': f"manual_{len(existing)+1}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'title': title,
            'content': content,
            'stocks': stocks or [],
            'sentiment': sentiment,
            'category': category,
            'source': '手動輸入',
            'created_at': datetime.now().isoformat(),
        }
        
        existing.insert(0, new_item)
        
        try:
            data = {
                'updated_at': datetime.now().isoformat(),
                'news': existing
            }
            with open(self.manual_news_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存手動新聞失敗: {e}")
        
        return new_item
    
    # === 分析功能 ===
    
    def extract_stocks_from_text(self, text: str) -> List[str]:
        """從文字中提取股票代碼（適用於標題或內容）"""
        if not text:
            return []
            
        stocks = set()
        
        # 方法1: 直接匹配關鍵詞
        for keyword, code in KEYWORD_STOCK_MAP.items():
            if keyword in text and code:
                stocks.add(code)
        
        # 方法2: 匹配產業關鍵詞（僅用於標題，避免內容過度匹配）
        # 這會在調用處單獨處理
        
        # 方法3: 匹配股票代碼 (4位數字)
        code_matches = re.findall(r'\\b(\\d{4})\\b', text)
        for code in code_matches:
            if code.startswith(('1', '2', '3', '4', '5', '6', '8', '9')):
                stocks.add(code)
        
        return list(stocks)
    
    def extract_stocks_from_title(self, title: str, content: str = '') -> List[str]:
        """從標題和內容中提取股票代碼
        
        改進邏輯：
        1. 優先提取標題中明確提到的股票（公司名稱或代碼）
        2. 只有在標題沒有找到任何特定股票時，才使用產業關鍵詞推斷
        3. 這樣避免「AI催動 亞翔訂單新高」被誤關聯到廣達、緯創
        """
        stocks = set()
        
        # 從標題提取明確提到的股票
        title_stocks = self.extract_stocks_from_text(title)
        stocks.update(title_stocks)
        
        # 從內容提取（如果有內容）
        if content:
            content_stocks = self.extract_stocks_from_text(content)
            stocks.update(content_stocks)
        
        # 【重要修正】只有在標題和內容都沒有找到任何特定股票時，
        # 才使用產業關鍵詞推斷相關股票
        # 這樣可以避免「AI催動 亞翔訂單新高」被錯誤地關聯到廣達、緯創等
        if len(stocks) == 0:
            for industry, codes in INDUSTRY_KEYWORDS.items():
                if industry in title:
                    # 產業推斷時，每個產業最多取2檔代表性股票
                    for code in codes[:2]:
                        stocks.add(code)
        
        return list(stocks)
    
    def analyze_news_sentiment(self, title: str) -> Tuple[str, float]:
        """分析新聞標題情緒 - 改進版：更準確的關鍵詞匹配"""
        
        # 強正面關鍵詞 (權重 1.5)
        strong_positive = [
            '創高', '創新高', '飆漲', '暴漲', '大漲', '狂飆', '噴發', '井噴',
            '漲停', '強攻', '狂拉', '秒殺', '搶翻', '熱銷', '大賺', '暴增',
            '爆發', '翻倍', '猛攻', '狂飆', '勇冠', '稱霸'
        ]
        
        # 正面關鍵詞 (權重 1.0)
        positive_keywords = [
            '上漲', '成長', '增長', '利多', '突破', '看好', '上揚', '旺',
            '加持', '商機', '贏家', '亮眼', '優於', '買超', '進場', '擴產',
            '滿載', '續旺', '擴大', '發酵', '受惠', '沾光', '有利', '動能',
            '回升', '反彈', '轉強', '走揚', '攀升', '升溫', '題材', '契機'
        ]
        
        # 強負面關鍵詞 (權重 -1.5)
        strong_negative = [
            '暴跌', '崩盤', '重挫', '慘跌', '大跌', '狂瀉', '腰斬', '血洗',
            '跌停', '崩潰', '破產', '倒閉', '虧損', '爆雷', '踩雷', '慘賠',
            '血流', '殺盤', '恐慌', '潰敗', '崩跌'
        ]
        
        # 負面關鍵詞 (權重 -1.0)
        negative_keywords = [
            '下跌', '利空', '衰退', '減少', '警告', '警示', '風險', '限制',
            '禁令', '危機', '跌', '賣超', '出場', '下滑', '縮減', '弱勢',
            '疲軟', '放緩', '萎縮', '走弱', '承壓', '觀望', '謹慎', '憂',
            '拖累', '壓力', '調降', '下修', '不樂觀', '利空', '制裁',
            '停產', '砍單', '裁員', '關廠', '遇冷', '降溫', '退燒'
        ]
        
        # 中性/事實性關鍵詞 (不計分)
        neutral_keywords = [
            '展望', '預期', '預估', '分析', '報告', '公布', '發布', '調查',
            '法人', '外資', '投信', '自營', '除息', '配息', '換股'
        ]
        
        # 計算分數
        score = 0.0
        
        # 強正面
        for kw in strong_positive:
            if kw in title:
                score += 1.5
        
        # 正面
        for kw in positive_keywords:
            if kw in title:
                score += 1.0
        
        # 強負面
        for kw in strong_negative:
            if kw in title:
                score -= 1.5
        
        # 負面
        for kw in negative_keywords:
            if kw in title:
                score -= 1.0
        
        # 決定情緒
        if score >= 1.0:
            return 'positive', min(score * 0.15, 1.0)
        elif score <= -1.0:
            return 'negative', max(score * 0.15, -1.0)
        else:
            return 'neutral', 0.0
    
    def get_all_news_with_analysis(self) -> Dict:
        """取得所有新聞並進行分析"""
        # 1. 取得各來源新聞
        iek_news = self.get_iek_news()
        external_news = self.get_external_news()  # 台視財經 + CMoney
        perplexity_news = self.get_perplexity_news()
        manual_news = self.get_manual_news()
        
        # 2. 分析並整合
        all_news = []
        stock_mentions = {}  # 股票被提及次數
        
        # 處理 IEK 新聞
        for news in iek_news:
            title = news.get('title', '')
            stocks = self.extract_stocks_from_title(title)
            sentiment, score = self.analyze_news_sentiment(title)
            
            processed = {
                'id': f"iek_{hash(title) % 100000}",
                'title': title,
                'source': news.get('source', 'IEK 產業情報網'),
                'sourceType': 'iek',
                'url': news.get('url', ''),
                'date': news.get('date', datetime.now().strftime('%Y-%m-%d')),
                'industry': news.get('industry', '其他'),
                'stocks': stocks,
                'sentiment': sentiment,
                'sentimentScore': score,
            }
            all_news.append(processed)
            
            # 統計股票提及
            for stock in stocks:
                if stock not in stock_mentions:
                    stock_mentions[stock] = {'count': 0, 'positive': 0, 'negative': 0, 'news': []}
                stock_mentions[stock]['count'] += 1
                stock_mentions[stock]['news'].append(title[:50])
                if sentiment == 'positive':
                    stock_mentions[stock]['positive'] += 1
                elif sentiment == 'negative':
                    stock_mentions[stock]['negative'] += 1
        
        # 處理外部新聞 (台視財經、CMoney、經濟日報等) - 修正：重新分析情緒
        for news in external_news:
            title = news.get('title', '')
            stocks = self.extract_stocks_from_title(title)
            # 重新分析情緒，確保「漲停」等關鍵詞被正確識別
            sentiment, score = self.analyze_news_sentiment(title)
            
            processed = {
                'id': news.get('id', f"ext_{hash(title) % 100000}"),
                'title': title,
                'source': news.get('source', '外部來源'),
                'sourceType': news.get('sourceType', 'external'),
                'url': news.get('url', ''),
                'date': news.get('date', datetime.now().strftime('%Y-%m-%d')),
                'industry': news.get('industry', '其他'),
                'stocks': stocks,
                'sentiment': sentiment,
                'sentimentScore': score,
            }
            all_news.append(processed)
            
            # 統計股票提及
            for stock in stocks:
                if stock not in stock_mentions:
                    stock_mentions[stock] = {'count': 0, 'positive': 0, 'negative': 0, 'news': []}
                stock_mentions[stock]['count'] += 1
                stock_mentions[stock]['news'].append(title[:50])
                if sentiment == 'positive':
                    stock_mentions[stock]['positive'] += 1
                elif sentiment == 'negative':
                    stock_mentions[stock]['negative'] += 1
        
        # 處理 Perplexity 新聞
        for news in perplexity_news:
            title = news.get('title', '')
            stocks = news.get('stocks', []) or self.extract_stocks_from_title(title)
            
            processed = {
                'id': news.get('id', ''),
                'title': title,
                'content': news.get('content', ''),
                'source': 'Perplexity AI',
                'sourceType': 'perplexity',
                'url': news.get('source_url', ''),
                'date': news.get('created_at', ''),
                'stocks': stocks,
                'sentiment': news.get('sentiment', 'neutral'),
                'sentimentScore': 0.5 if news.get('sentiment') == 'positive' else -0.5 if news.get('sentiment') == 'negative' else 0,
            }
            all_news.append(processed)
            
            for stock in stocks:
                if stock not in stock_mentions:
                    stock_mentions[stock] = {'count': 0, 'positive': 0, 'negative': 0, 'news': []}
                stock_mentions[stock]['count'] += 1
                stock_mentions[stock]['news'].append(title[:50])
        
        # 處理手動新聞
        for news in manual_news:
            title = news.get('title', '')
            stocks = news.get('stocks', []) or self.extract_stocks_from_title(title)
            
            processed = {
                'id': news.get('id', ''),
                'title': title,
                'content': news.get('content', ''),
                'source': news.get('category', '手動輸入'),
                'sourceType': 'manual',
                'date': news.get('created_at', ''),
                'stocks': stocks,
                'sentiment': news.get('sentiment', 'neutral'),
            }
            all_news.append(processed)
        
        # 統計各來源數量
        ttv_count = len([n for n in all_news if n.get('sourceType') == 'ttv'])
        cmoney_count = len([n for n in all_news if n.get('sourceType') == 'cmoney'])
        udn_count = len([n for n in all_news if n.get('sourceType') == 'udn'])
        technews_count = len([n for n in all_news if n.get('sourceType') == 'technews'])
        pocket_count = len([n for n in all_news if n.get('sourceType') == 'pocket'])
        
        # 3. 產生股票推薦
        recommendations = self._generate_stock_recommendations(stock_mentions)
        
        # 4. 情緒統計分析
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        for news in all_news:
            sentiment = news.get('sentiment', 'neutral')
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
        
        total_news_count = len(all_news)
        sentiment_analysis = {
            'positive': {
                'count': sentiment_counts['positive'],
                'ratio': round(sentiment_counts['positive'] / total_news_count * 100, 1) if total_news_count > 0 else 0
            },
            'neutral': {
                'count': sentiment_counts['neutral'],
                'ratio': round(sentiment_counts['neutral'] / total_news_count * 100, 1) if total_news_count > 0 else 0
            },
            'negative': {
                'count': sentiment_counts['negative'],
                'ratio': round(sentiment_counts['negative'] / total_news_count * 100, 1) if total_news_count > 0 else 0
            },
            'overall': 'bullish' if sentiment_counts['positive'] > sentiment_counts['negative'] * 1.5 else
                       'bearish' if sentiment_counts['negative'] > sentiment_counts['positive'] * 1.5 else 'neutral',
            'confidence': round(abs(sentiment_counts['positive'] - sentiment_counts['negative']) / max(total_news_count, 1) * 100, 1)
        }
        
        # 5. 熱門產業/關鍵字分析
        industry_mentions = {}
        keyword_mentions = {}
        
        # 產業關鍵字
        industry_keywords = {
            'AI伺服器': ['AI', '伺服器', '人工智慧', 'GPU', '輝達', 'NVIDIA', 'ChatGPT'],
            '半導體': ['半導體', '晶圓', '台積電', 'TSMC', '封測', '先進製程', 'CoWoS'],
            '矽光子': ['矽光子', '光通訊', '光模組', '光纖'],
            '電動車': ['電動車', 'EV', '特斯拉', 'Tesla', '新能源車', '電池'],
            '綠能': ['綠能', '太陽能', '風電', '儲能', '碳中和'],
            '航運': ['航運', '貨櫃', '長榮', '陽明', '運價'],
            '金融': ['金融', '銀行', '壽險', '升息', '利率'],
            '散熱': ['散熱', '熱管', '液冷', '水冷'],
            '記憶體': ['記憶體', 'DRAM', 'NAND', 'HBM', 'DDR5'],
            'PCB': ['PCB', '印刷電路板', '載板', 'ABF'],
        }
        
        for news in all_news:
            title = news.get('title', '')
            industry = news.get('industry', '')
            
            # 統計產業
            if industry and industry != '其他':
                industry_mentions[industry] = industry_mentions.get(industry, 0) + 1
            
            # 統計關鍵字
            for keyword_group, keywords in industry_keywords.items():
                for kw in keywords:
                    if kw in title:
                        keyword_mentions[keyword_group] = keyword_mentions.get(keyword_group, 0) + 1
                        break  # 每則新聞每個主題只計算一次
        
        # 排序熱門產業/關鍵字（取前10）
        hot_industries = sorted(industry_mentions.items(), key=lambda x: -x[1])[:10]
        hot_keywords = sorted(keyword_mentions.items(), key=lambda x: -x[1])[:10]
        
        # 6. 生成智能摘要
        smart_summary = self._generate_smart_summary(
            sentiment_analysis, 
            hot_keywords[:3], 
            recommendations[:3],
            total_news_count
        )
        
        # 7. 生成可行動洞察報告
        actionable_insights = self._generate_actionable_insights(
            all_news,
            hot_keywords,
            recommendations,
            sentiment_analysis
        )
        
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'totalNews': len(all_news),
                'iekCount': len(iek_news),
                'ttvCount': ttv_count,
                'cmoneyCount': cmoney_count,
                'udnCount': udn_count,
                'technewsCount': technews_count,
                'pocketCount': pocket_count,
                'perplexityCount': len(perplexity_news),
                'manualCount': len(manual_news),
                'stocksMentioned': len(stock_mentions),
            },
            # 新增：情緒分析
            'sentimentAnalysis': sentiment_analysis,
            # 新增：熱門產業
            'hotIndustries': [{'name': k, 'count': v} for k, v in hot_industries],
            # 新增：熱門關鍵字
            'hotKeywords': [{'name': k, 'count': v} for k, v in hot_keywords],
            # 新增：智能摘要
            'smartSummary': smart_summary,
            # 新增：可行動洞察報告（核心！）
            'actionableInsights': actionable_insights,
            'news': {
                'all': all_news,
                'iek': [n for n in all_news if n['sourceType'] == 'iek'],
                'ttv': [n for n in all_news if n['sourceType'] == 'ttv'],
                'cmoney': [n for n in all_news if n['sourceType'] == 'cmoney'],
                'udn': [n for n in all_news if n['sourceType'] == 'udn'],
                'technews': [n for n in all_news if n['sourceType'] == 'technews'],
                'pocket': [n for n in all_news if n['sourceType'] == 'pocket'],
                'perplexity': [n for n in all_news if n['sourceType'] == 'perplexity'],
                'manual': [n for n in all_news if n['sourceType'] == 'manual'],
            },
            'stockMentions': stock_mentions,
            'recommendations': recommendations,
        }
    
    def _generate_smart_summary(self, sentiment_analysis: Dict, top_keywords: List, 
                                 top_stocks: List, total_news: int) -> Dict:
        """生成智能市場摘要"""
        
        # 市場情緒描述
        overall = sentiment_analysis.get('overall', 'neutral')
        positive_ratio = sentiment_analysis.get('positive', {}).get('ratio', 0)
        negative_ratio = sentiment_analysis.get('negative', {}).get('ratio', 0)
        
        if overall == 'bullish':
            mood = '樂觀'
            mood_emoji = '📈'
            mood_color = 'green'
        elif overall == 'bearish':
            mood = '謹慎'
            mood_emoji = '📉'
            mood_color = 'red'
        else:
            mood = '中性'
            mood_emoji = '➖'
            mood_color = 'gray'
        
        # 熱門主題
        hot_topics = [kw[0] for kw in top_keywords] if top_keywords else ['一般產業']
        hot_topics_str = '、'.join(hot_topics[:3])
        
        # 關注股票
        watch_stocks = [s.get('symbol', '') + s.get('name', '') for s in top_stocks] if top_stocks else []
        watch_stocks_str = '、'.join(watch_stocks[:3]) if watch_stocks else '待分析'
        
        # 生成摘要文字
        if total_news > 0:
            summary_text = (
                f"今日市場情緒{mood}，正面消息佔比 {positive_ratio}%，負面消息佔比 {negative_ratio}%。"
                f"市場焦點集中在【{hot_topics_str}】等產業題材，"
                f"建議關注 {watch_stocks_str} 等相關個股動態。"
            )
        else:
            summary_text = "今日新聞資料更新中，請稍後再查看完整分析報告。"
        
        # 行動建議
        if overall == 'bullish' and positive_ratio > 50:
            action_advice = "市場氛圍偏多，可適度關注強勢股機會"
        elif overall == 'bearish' and negative_ratio > 40:
            action_advice = "市場存在不確定性，建議謹慎操作、控制倉位"
        else:
            action_advice = "市場觀望氣氛濃厚，建議等待明確方向再行動"
        
        return {
            'mood': mood,
            'moodEmoji': mood_emoji,
            'moodColor': mood_color,
            'hotTopics': hot_topics,
            'summaryText': summary_text,
            'actionAdvice': action_advice,
            'dataPoints': {
                'totalNews': total_news,
                'positiveRatio': positive_ratio,
                'negativeRatio': negative_ratio,
            }
        }
    
    def _generate_actionable_insights(self, all_news: List[Dict], hot_keywords: List, 
                                       recommendations: List[Dict], sentiment_analysis: Dict) -> Dict:
        """生成可行動的投資洞察報告"""
        
        insights = {
            'corePoints': [],       # 核心觀點（3點給忙碌投資人）
            'opportunities': [],     # 機會標記
            'risks': [],            # 風險警示
            'industryActions': [],   # 產業行動建議
            'updateTime': datetime.now().strftime('%H:%M'),
        }
        
        # === 1. 生成核心觀點（3點建議）===
        
        # 觀點1：今日最熱門的產業機會
        if hot_keywords and len(hot_keywords) > 0:
            top_industry = hot_keywords[0][0]
            top_count = hot_keywords[0][1]
            
            # 找出該產業相關的推薦股票
            related_stocks = []
            industry_stock_map = {
                'AI伺服器': ['2382', '3231', '2356', '6669'],
                '半導體': ['2330', '2454', '2303', '3711'],
                '矽光子': ['3450', '3163', '4979'],
                '記憶體': ['2337', '2344', '8299'],
                '電動車': ['2258', '1319', '2201'],
                '散熱': ['3324', '3017'],
            }
            
            target_codes = industry_stock_map.get(top_industry, [])
            for rec in recommendations[:10]:
                if rec.get('symbol') in target_codes:
                    related_stocks.append(f"{rec.get('symbol')}{rec.get('name', '')}")
            
            related_str = '、'.join(related_stocks[:3]) if related_stocks else '相關概念股'
            
            insights['corePoints'].append({
                'type': 'opportunity',
                'icon': '🔥',
                'title': f'【{top_industry}】產業持續受關注',
                'summary': f'今日共 {top_count} 則相關新聞，市場熱度最高',
                'action': f'建議關注：{related_str}',
                'priority': 1
            })
        
        # 觀點2：市場情緒與建議
        overall = sentiment_analysis.get('overall', 'neutral')
        pos_ratio = sentiment_analysis.get('positive', {}).get('ratio', 0)
        neg_ratio = sentiment_analysis.get('negative', {}).get('ratio', 0)
        
        if overall == 'bullish':
            mood_point = {
                'type': 'info',
                'icon': '📈',
                'title': '市場情緒偏多，正面消息主導',
                'summary': f'正面新聞佔比 {pos_ratio}%，明顯高於負面 {neg_ratio}%',
                'action': '可積極關注領漲族群，但注意追高風險',
                'priority': 2
            }
        elif overall == 'bearish':
            mood_point = {
                'type': 'warning',
                'icon': '⚠️',
                'title': '市場情緒謹慎，負面訊號增加',
                'summary': f'負面新聞佔比 {neg_ratio}%，建議審慎評估',
                'action': '建議降低持股比重，等待明確訊號',
                'priority': 2
            }
        else:
            mood_point = {
                'type': 'info',
                'icon': '📊',
                'title': '市場觀望，多空拉鋸中',
                'summary': f'正面 {pos_ratio}% vs 負面 {neg_ratio}%，方向不明確',
                'action': '建議選股不選市，聚焦個股題材',
                'priority': 2
            }
        insights['corePoints'].append(mood_point)
        
        # 觀點3：首選關注標的
        if recommendations and len(recommendations) > 0:
            top_stock = recommendations[0]
            insights['corePoints'].append({
                'type': 'action',
                'icon': '🎯',
                'title': f'首選關注：{top_stock.get("symbol")} {top_stock.get("name", "")}',
                'summary': f'被 {top_stock.get("mentionCount", 0)} 則新聞提及，情緒{("正面" if top_stock.get("positiveCount", 0) > top_stock.get("negativeCount", 0) else "中性")}',
                'action': top_stock.get('relatedNews', ['查看相關新聞'])[0][:40] + '...' if top_stock.get('relatedNews') else '點擊查看詳情',
                'priority': 3
            })
        
        # === 2. 機會標記 ===
        # 找出新進榜或熱度上升的產業
        for kw, count in hot_keywords[:5]:
            if count >= 5:
                insights['opportunities'].append({
                    'industry': kw,
                    'signal': '熱度高',
                    'newsCount': count,
                    'description': f'{kw}今日新聞量達 {count} 則，市場關注度高'
                })
        
        # === 3. 風險警示 ===
        # 檢查是否有負面情緒集中的產業
        industry_sentiment = {}
        for news in all_news:
            industry = news.get('industry', '其他')
            sentiment = news.get('sentiment', 'neutral')
            if industry not in industry_sentiment:
                industry_sentiment[industry] = {'positive': 0, 'negative': 0, 'neutral': 0}
            industry_sentiment[industry][sentiment] = industry_sentiment[industry].get(sentiment, 0) + 1
        
        for industry, counts in industry_sentiment.items():
            total = counts['positive'] + counts['negative'] + counts['neutral']
            if total >= 3 and counts['negative'] >= total * 0.4:
                insights['risks'].append({
                    'industry': industry,
                    'signal': '負面情緒上升',
                    'negativeRatio': round(counts['negative'] / total * 100, 1),
                    'description': f'{industry}產業負面消息佔比達 {round(counts["negative"]/total*100, 1)}%，建議謹慎'
                })
        
        # === 4. 產業行動建議 ===
        for kw, count in hot_keywords[:3]:
            if count >= 3:
                # 找出該產業的情緒
                ind_sent = industry_sentiment.get(kw, {})
                pos = ind_sent.get('positive', 0)
                neg = ind_sent.get('negative', 0)
                
                if pos > neg:
                    action = '積極關注'
                    color = 'green'
                elif neg > pos:
                    action = '謹慎觀察'
                    color = 'red'
                else:
                    action = '中性觀望'
                    color = 'gray'
                
                insights['industryActions'].append({
                    'industry': kw,
                    'newsCount': count,
                    'action': action,
                    'color': color,
                    'positiveCount': pos,
                    'negativeCount': neg
                })
        
        # === 5. 產業詳細資料（熱門產業的相關股票） ===
        insights['industryDetails'] = []
        for kw, count in hot_keywords[:5]:
            # 嘗試匹配到 INDUSTRY_STOCK_DETAILS
            industry_key = kw
            if kw == 'AI伺服器' or kw == 'AI':
                industry_key = 'AI伺服器'
            
            if industry_key in INDUSTRY_STOCK_DETAILS:
                detail = INDUSTRY_STOCK_DETAILS[industry_key]
                stocks_info = []
                for stock in detail['stocks'][:5]:  # 最多5檔
                    # 檢查這檔股票在推薦清單中的情緒
                    stock_sentiment = 'neutral'
                    for rec in recommendations:
                        if rec.get('symbol') == stock['code']:
                            if rec.get('positiveCount', 0) > rec.get('negativeCount', 0):
                                stock_sentiment = 'positive'
                            elif rec.get('negativeCount', 0) > rec.get('positiveCount', 0):
                                stock_sentiment = 'negative'
                            break
                    
                    stocks_info.append({
                        'code': stock['code'],
                        'name': stock['name'],
                        'role': stock['role'],
                        'tier': stock['tier'],
                        'sentiment': stock_sentiment
                    })
                
                insights['industryDetails'].append({
                    'industry': kw,
                    'newsCount': count,
                    'description': detail.get('description', ''),
                    'stocks': stocks_info,
                    'relatedConcepts': detail.get('related_concepts', []),
                    'sentiment': industry_sentiment.get(kw, {}),
                })
        
        # === 6. 主題聚合偵測 - 識別正在發酵的投資主題 ===
        insights['trendingThemes'] = []
        
        # 定義熱門主題關鍵詞組
        theme_keywords = {
            '輝達供應鏈': ['輝達', 'NVIDIA', 'GB200', 'H100', 'AI晶片', 'GPU'],
            'AI伺服器需求': ['AI伺服器', '伺服器', 'server', '資料中心', 'datacenter'],
            '半導體漲價': ['漲價', '報價', '調漲', '價格'],
            'CoWoS擴產': ['CoWoS', '先進封裝', '2.5D', '3D封裝'],
            '電動車商機': ['電動車', 'EV', '特斯拉', 'Tesla', '新能源車'],
            '記憶體復甦': ['記憶體', 'DRAM', 'HBM', 'DDR5', 'NAND'],
            '矽光子概念': ['矽光子', '光通訊', '光模組', '800G'],
            '散熱需求': ['散熱', '液冷', '熱管', 'cooling'],
        }
        
        # 定義每個主題的核心相關股票（確保顯示真正相關的股票）
        theme_core_stocks = {
            '輝達供應鏈': ['2382', '3231', '2356', '6669', '3706'],  # AI伺服器代工
            'AI伺服器需求': ['2382', '3231', '2356', '6669', '3706', '2376'],
            '半導體漲價': ['2330', '2303', '2454', '3711', '6239'],  # 半導體
            'CoWoS擴產': ['2330', '3711', '6239'],  # 台積電、封測
            '電動車商機': ['2258', '1319', '2201', '2207'],  # 電動車
            '記憶體復甦': ['2337', '2344', '8299', '3450'],  # 記憶體真正的股票
            '矽光子概念': ['3450', '3163', '4979', '4977'],  # 光通訊
            '散熱需求': ['3324', '3017', '6279'],  # 散熱模組
        }
        
        # 統計每個主題在新聞中出現的次數
        theme_counts = {}
        theme_news = {}
        theme_stocks = {}
        
        for news in all_news:
            title = news.get('title', '')
            content = news.get('content', '')
            text = title + ' ' + content
            stocks = news.get('stocks', [])
            
            for theme, keywords in theme_keywords.items():
                for kw in keywords:
                    if kw in text:
                        if theme not in theme_counts:
                            theme_counts[theme] = 0
                            theme_news[theme] = []
                            theme_stocks[theme] = set()
                        theme_counts[theme] += 1
                        if len(theme_news[theme]) < 3:
                            theme_news[theme].append({
                                'title': title[:50],
                                'source': news.get('source', ''),
                                'sentiment': news.get('sentiment', 'neutral')
                            })
                        for s in stocks:
                            theme_stocks[theme].add(s)
                        break  # 每則新聞每個主題只計算一次
        
        # 篩選熱度高的主題（至少3則新聞）
        for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
            if count >= 3:
                # 計算情緒
                pos_count = sum(1 for n in theme_news[theme] if n['sentiment'] == 'positive')
                neg_count = sum(1 for n in theme_news[theme] if n['sentiment'] == 'negative')
                
                if pos_count > neg_count:
                    sentiment = 'positive'
                    sentiment_label = '正面情緒主導'
                elif neg_count > pos_count:
                    sentiment = 'negative'
                    sentiment_label = '負面情緒警示'
                else:
                    sentiment = 'neutral'
                    sentiment_label = '情緒中性'
                
                # 找出相關股票名稱 - 優先使用核心股票
                stock_names = []
                core_stocks = theme_core_stocks.get(theme, [])
                
                # 先加入新聞中提到且屬於核心股票的
                for code in list(theme_stocks[theme]):
                    if code in core_stocks:
                        name = STOCK_CODE_TO_NAME.get(code, code)
                        stock_names.append(f"{code} {name}")
                
                # 如果核心股票不足，補充其他核心股票（即使新聞沒直接提到）
                if len(stock_names) < 3:
                    for code in core_stocks:
                        if f"{code} {STOCK_CODE_TO_NAME.get(code, code)}" not in stock_names:
                            name = STOCK_CODE_TO_NAME.get(code, code)
                            stock_names.append(f"{code} {name}")
                            if len(stock_names) >= 3:
                                break
                
                insights['trendingThemes'].append({
                    'theme': theme,
                    'newsCount': count,
                    'sentiment': sentiment,
                    'sentimentLabel': sentiment_label,
                    'relatedStocks': stock_names[:5],
                    'sampleNews': theme_news[theme][:2],
                    'heatLevel': '🔥🔥🔥' if count >= 10 else '🔥🔥' if count >= 5 else '🔥',
                })
        
        # 只保留前5個主題
        insights['trendingThemes'] = insights['trendingThemes'][:5]
        
        return insights
    
    def _generate_stock_recommendations(self, stock_mentions: Dict) -> List[Dict]:
        """根據新聞分析產生股票推薦 - 改進版：更保守、更準確"""
        
        # 自動取得股票名稱 (使用 API)
        stock_names = self._fetch_stock_names(list(stock_mentions.keys()))
        
        recommendations = []
        
        for stock_code, data in stock_mentions.items():
            mention_count = data['count']
            positive = data['positive']
            negative = data['negative']
            neutral = mention_count - positive - negative
            
            # 計算情緒分數 - 改進公式
            total_sentiment = positive + negative
            if total_sentiment > 0:
                sentiment_ratio = (positive - negative) / total_sentiment
            else:
                sentiment_ratio = 0
            
            # 計算情緒強度 (有多少是有情緒的新聞)
            sentiment_intensity = total_sentiment / mention_count if mention_count > 0 else 0
            
            # 計算風險等級
            risk_level = 'low'
            risk_warning = ''
            
            # 風險評估條件
            if negative > positive:
                risk_level = 'high'
                risk_warning = '⚠️ 負面消息較多'
            elif negative >= 2 and negative >= positive * 0.5:
                risk_level = 'medium'
                risk_warning = '⚡ 存在負面消息'
            elif mention_count >= 5 and sentiment_ratio < 0.3:
                risk_level = 'medium'
                risk_warning = '📊 情緒偏中性'
            
            # 計算推薦分數 - 調整公式
            # 基礎分 = 提及次數 * 8 (提高提及次數權重)
            # 正面加分 = 正面數 * 15 (直接獎勵正面新聞)
            # 情緒分 = 情緒比例 * 情緒強度 * 30
            # 負面懲罰 = 負面數 * -20 (嚴厲懲罰負面消息)
            base_score = mention_count * 8
            positive_bonus = positive * 15
            sentiment_score = sentiment_ratio * sentiment_intensity * 30
            negative_penalty = negative * -20
            
            score = base_score + positive_bonus + sentiment_score + negative_penalty
            
            # 決定推薦等級 - 調整門檻
            # 強力關注：有2+正面新聞且無負面，或分數>=45
            if (positive >= 2 and negative == 0) or (score >= 45 and sentiment_ratio >= 0.5 and negative == 0):
                action = '強力關注'
                color = 'red'
            elif score >= 30 and sentiment_ratio >= 0.3 and negative <= 1:
                action = '值得關注'
                color = 'orange'
            elif score >= 15 and sentiment_ratio >= 0:
                action = '觀察'
                color = 'yellow'
            elif sentiment_ratio < 0 or negative > positive:
                action = '⚠️ 謹慎'
                color = 'gray'
            else:
                action = '低度關注'
                color = 'gray'
            
            # 取得股票名稱
            stock_name = stock_names.get(stock_code, '')
            
            recommendations.append({
                'symbol': stock_code,
                'name': stock_name,
                'mentionCount': mention_count,
                'positiveCount': positive,
                'negativeCount': negative,
                'neutralCount': neutral,
                'sentimentRatio': round(sentiment_ratio, 2),
                'sentimentIntensity': round(sentiment_intensity, 2),
                'score': round(score, 1),
                'action': action,
                'color': color,
                'riskLevel': risk_level,
                'riskWarning': risk_warning,
                'relatedNews': data['news'][:3],  # 最多3則相關新聞
            })
        
        # 按分數排序，但優先考慮風險等級
        recommendations.sort(key=lambda x: (
            0 if x['riskLevel'] == 'low' else (1 if x['riskLevel'] == 'medium' else 2),
            -x['score']
        ))
        
        return recommendations[:20]  # 最多返回20檔
    
    def _fetch_stock_names(self, stock_codes: List[str]) -> Dict[str, str]:
        """批次取得股票名稱 (使用多種 API 來源)"""
        result = {}
        
        # 基本名稱字典 (作為快取)
        basic_names = {
            '2330': '台積電', '2454': '聯發科', '2317': '鴻海', '2382': '廣達',
            '3231': '緯創', '6669': '緯穎', '3706': '神達', '2376': '技嘉',
            '2377': '微星', '2356': '英業達', '3324': '雙鴻', '3017': '奇鋐',
            '3037': '欣興', '3189': '景碩', '3533': '嘉澤', '3653': '健策',
            '2303': '聯電', '3711': '日月光投控', '6239': '力成', '3661': '世芯',
            '3443': '創意', '2379': '瑞昱', '3034': '聯詠', '2603': '長榮',
            '2609': '陽明', '2615': '萬海', '2344': '華邦電', '2327': '國巨',
            '4958': '臻鼎', '3450': '聯鈞', '8045': '易發', '2258': '鴻華先進',
            '1319': '東陽', '8390': '金益鼎', '2337': '旺宏', '8299': '群聯',
        }
        
        # 需要查詢的股票
        codes_to_lookup = []
        for code in stock_codes:
            if code in basic_names:
                result[code] = basic_names[code]
            else:
                codes_to_lookup.append(code)
        
        # 使用 API 查詢未知的股票名稱
        if codes_to_lookup:
            try:
                from stock_mappings import get_stock_name
                for code in codes_to_lookup:
                    name = get_stock_name(code)
                    if name and name != code:
                        result[code] = name
                        # 動態新增到基本名稱字典
                        basic_names[code] = name
                    else:
                        result[code] = ''
            except Exception as e:
                logger.warning(f"查詢股票名稱失敗: {e}")
                for code in codes_to_lookup:
                    result[code] = ''
        
        return result
    
    def get_stocks_to_watch(self) -> List[Dict]:
        """取得今日應關注的股票"""
        analysis = self.get_all_news_with_analysis()
        return analysis.get('recommendations', [])


# 全域實例
news_analysis_service = NewsAnalysisService()


# === 便捷函數 ===

def get_news_analysis() -> Dict:
    """取得新聞分析結果"""
    return news_analysis_service.get_all_news_with_analysis()

def get_stocks_to_watch() -> List[Dict]:
    """取得今日應關注股票"""
    return news_analysis_service.get_stocks_to_watch()

def add_perplexity_news(title: str, content: str = '', stocks: List[str] = None, 
                       sentiment: str = 'neutral') -> Dict:
    """新增 Perplexity 新聞"""
    return news_analysis_service.add_perplexity_news(title, content, stocks, sentiment)
