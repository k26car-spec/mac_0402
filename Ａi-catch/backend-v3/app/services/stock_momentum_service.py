"""
股票動能監控服務
目標：捕捉新聞來不及報導的異動股機會

功能：
1. 漲停/跌停監控
2. 成交量異常偵測
3. 主力買超追蹤
4. 產業連動分析
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# 擴展產業-股票映射，納入更多中小型股
EXTENDED_INDUSTRY_MAP = {
    # === 半導體測試/封測 ===
    '半導體測試': {
        'description': '半導體測試代工與設備',
        'stocks': [
            {'code': '2449', 'name': '京元電子', 'role': '測試代工', 'cap': '中'},
            {'code': '3264', 'name': '欣銓', 'role': '測試代工', 'cap': '中'},
            {'code': '8021', 'name': '尖點', 'role': '測試設備', 'cap': '小'},
            {'code': '6239', 'name': '力成', 'role': '封測', 'cap': '大'},
            {'code': '3711', 'name': '日月光', 'role': '封測', 'cap': '大'},
            {'code': '2351', 'name': '順德', 'role': '封測設備', 'cap': '中'},
        ],
        'triggers': ['測試產能', '封測', 'AI晶片測試', 'CoWoS'],
    },
    
    # === LED/驅動IC ===
    'LED驅動IC': {
        'description': 'LED驅動晶片設計',
        'stocks': [
            {'code': '5472', 'name': '聚積', 'role': '驅動IC設計', 'cap': '中'},
            {'code': '3231', 'name': '緯創', 'role': 'LED模組', 'cap': '大'},
            {'code': '2393', 'name': '億光', 'role': 'LED封裝', 'cap': '中'},
        ],
        'triggers': ['LED', 'Mini LED', 'Micro LED', '背光'],
    },
    
    # === PCB/軟板 ===
    'PCB軟板': {
        'description': 'PCB與軟性電路板',
        'stocks': [
            {'code': '5498', 'name': '凱崴', 'role': '軟板', 'cap': '小'},
            {'code': '3037', 'name': '欣興', 'role': 'ABF載板', 'cap': '大'},
            {'code': '4958', 'name': '臻鼎-KY', 'role': 'PCB', 'cap': '大'},
            {'code': '6153', 'name': '嘉聯益', 'role': '軟板', 'cap': '中'},
            {'code': '3189', 'name': '景碩', 'role': 'IC載板', 'cap': '大'},
        ],
        'triggers': ['PCB', '軟板', 'ABF載板', 'IC載板', 'FPC'],
    },
    
    # === 其他潛力產業 ===
    'IP設計服務': {
        'description': '矽智財與IC設計服務',
        'stocks': [
            {'code': '3661', 'name': '世芯-KY', 'role': 'ASIC設計', 'cap': '大'},
            {'code': '3443', 'name': '創意', 'role': 'IC設計服務', 'cap': '中'},
            {'code': '6770', 'name': '力積電', 'role': '晶圓代工', 'cap': '中'},
        ],
        'triggers': ['ASIC', 'IP', '客製化晶片'],
    },
}

# 股票代碼到產業的反向查找表
def build_stock_to_industry_map():
    result = {}
    for industry, data in EXTENDED_INDUSTRY_MAP.items():
        for stock in data['stocks']:
            code = stock['code']
            if code not in result:
                result[code] = []
            result[code].append({
                'industry': industry,
                'role': stock['role'],
                'cap': stock['cap'],
            })
    return result

STOCK_TO_INDUSTRY = build_stock_to_industry_map()


class StockMomentumService:
    """股票動能監控服務"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = None
        
    async def analyze_limit_up_stocks(self, limit_up_codes: List[str]) -> Dict:
        """
        分析漲停股的產業關聯
        
        Args:
            limit_up_codes: 漲停股票代碼列表
            
        Returns:
            分析結果，包含產業聚合、連動股票等
        """
        result = {
            'totalStocks': len(limit_up_codes),
            'industryBreakdown': {},
            'chainReaction': [],  # 產業連動效應
            'hiddenOpportunities': [],  # 同產業未漲停的股票
            'timestamp': datetime.now().isoformat(),
        }
        
        # 分析每檔漲停股的產業
        industry_counts = {}
        covered_stocks = set()
        
        for code in limit_up_codes:
            industries = STOCK_TO_INDUSTRY.get(code, [])
            for ind_info in industries:
                industry = ind_info['industry']
                if industry not in industry_counts:
                    industry_counts[industry] = {
                        'count': 0,
                        'stocks': [],
                    }
                industry_counts[industry]['count'] += 1
                industry_counts[industry]['stocks'].append({
                    'code': code,
                    'role': ind_info['role'],
                })
                covered_stocks.add(code)
        
        result['industryBreakdown'] = industry_counts
        
        # 找出產業連動效應（多檔同產業漲停）
        for industry, data in industry_counts.items():
            if data['count'] >= 2:
                result['chainReaction'].append({
                    'industry': industry,
                    'limitUpCount': data['count'],
                    'stocks': data['stocks'],
                    'signal': '🔥 產業熱點',
                    'description': f'{industry}板塊有{data["count"]}檔漲停，關注同產業其他標的',
                })
        
        # 找出同產業未漲停的機會股
        for industry, data in industry_counts.items():
            if data['count'] >= 1:
                ind_data = EXTENDED_INDUSTRY_MAP.get(industry, {})
                all_stocks = ind_data.get('stocks', [])
                
                for stock in all_stocks:
                    if stock['code'] not in limit_up_codes:
                        result['hiddenOpportunities'].append({
                            'code': stock['code'],
                            'name': stock['name'],
                            'industry': industry,
                            'role': stock['role'],
                            'cap': stock['cap'],
                            'reason': f'同產業{data["count"]}檔漲停',
                        })
        
        return result
    
    async def get_related_stocks(self, stock_code: str) -> Dict:
        """
        取得某股票的關聯股票
        
        Args:
            stock_code: 股票代碼
            
        Returns:
            關聯股票資訊
        """
        industries = STOCK_TO_INDUSTRY.get(stock_code, [])
        
        result = {
            'stockCode': stock_code,
            'industries': industries,
            'relatedStocks': [],
        }
        
        for ind_info in industries:
            industry = ind_info['industry']
            ind_data = EXTENDED_INDUSTRY_MAP.get(industry, {})
            
            for stock in ind_data.get('stocks', []):
                if stock['code'] != stock_code:
                    result['relatedStocks'].append({
                        'code': stock['code'],
                        'name': stock['name'],
                        'industry': industry,
                        'role': stock['role'],
                    })
        
        return result


# 創建服務實例
stock_momentum_service = StockMomentumService()
