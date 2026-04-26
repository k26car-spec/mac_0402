"""
總經循環定位系統 v2.0
自動化檢測當前經濟週期階段，提供資產配置建議

系統名稱：循環驅動多因子投資系統
模組1：總經循環定位模組
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, Tuple, List
import warnings
import os

warnings.filterwarnings('ignore')

# 設定中文字體
try:
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft JhengHei', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


class EconomicCycleDetector:
    """
    經濟循環檢測器
    使用關鍵總經指標判斷當前所處經濟週期階段
    """
    
    def __init__(self, fred_api_key: str = None):
        """
        初始化檢測器
        
        Parameters:
        -----------
        fred_api_key : str
            FRED API金鑰，如果沒有則使用備用數據源
        """
        self.fred_api_key = fred_api_key
        self.indicators = {}
        self.current_stage = None
        self.stage_confidence = 0.0
        self.last_update = None
        
        # 定義階段權重參數（可調整）
        self.weights = {
            'pmi': 0.30,
            'yield_curve': 0.25,
            'unemployment': 0.15,
            'inflation': 0.15,
            'gdp_growth': 0.15
        }
        
        # 階段定義
        self.stages = {
            'recovery': {
                'name': '復甦期',
                'description': '經濟開始復甦，企業獲利改善',
                'color': 'green',
                'tw_sectors': ['科技', '金融', '非必需消費'],
                'us_etf': ['QQQ', 'XLF', 'XLY']
            },
            'expansion': {
                'name': '擴張期',
                'description': '經濟穩定成長，就業市場強勁',
                'color': 'blue',
                'tw_sectors': ['工業', '材料', '科技'],
                'us_etf': ['XLI', 'XLB', 'SPY']
            },
            'overheat': {
                'name': '過熱期',
                'description': '通膨壓力上升，央行可能緊縮',
                'color': 'orange',
                'tw_sectors': ['能源', '必需消費', '原物料'],
                'us_etf': ['XLE', 'XLP', 'DBC']
            },
            'recession': {
                'name': '衰退期',
                'description': '經濟收縮，企業獲利下滑',
                'color': 'red',
                'tw_sectors': ['必需消費', '醫療保健', '公用事業'],
                'us_etf': ['XLP', 'XLV', 'XLU', 'TLT']
            },
            'slowdown': {
                'name': '放緩期',
                'description': '成長動能減弱，但不至於衰退',
                'color': 'yellow',
                'tw_sectors': ['公用事業', '電信', '高股息'],
                'us_etf': ['XLU', 'VZ', 'VYM']
            }
        }
        
        # 台股產業代表股票
        self.tw_sector_stocks = {
            '科技': [
                {'symbol': '2330', 'name': '台積電'},
                {'symbol': '2454', 'name': '聯發科'},
                {'symbol': '2303', 'name': '聯電'}
            ],
            '金融': [
                {'symbol': '2882', 'name': '國泰金'},
                {'symbol': '2881', 'name': '富邦金'},
                {'symbol': '2886', 'name': '兆豐金'}
            ],
            '工業': [
                {'symbol': '2308', 'name': '台達電'},
                {'symbol': '2382', 'name': '廣達'},
                {'symbol': '2317', 'name': '鴻海'}
            ],
            '必需消費': [
                {'symbol': '1216', 'name': '統一'},
                {'symbol': '2912', 'name': '統一超'},
                {'symbol': '1301', 'name': '台塑'}
            ],
            '公用事業': [
                {'symbol': '2412', 'name': '中華電'},
                {'symbol': '9933', 'name': '中鼎'},
                {'symbol': '2002', 'name': '中鋼'}
            ],
            '醫療保健': [
                {'symbol': '1795', 'name': '美時'},
                {'symbol': '6446', 'name': '藥華藥'},
                {'symbol': '4142', 'name': '國光生'}
            ],
            'AI伺服器': [
                {'symbol': '2382', 'name': '廣達'},
                {'symbol': '3231', 'name': '緯創'},
                {'symbol': '6669', 'name': '緯穎'}
            ]
        }
    
    def fetch_all_indicators(self) -> Dict:
        """
        獲取所有關鍵總經指標
        """
        print("📊 正在獲取經濟指標數據...")
        
        try:
            # 1. 美國ISM製造業PMI
            pmi_data = self._fetch_pmi()
            self.indicators['pmi'] = pmi_data
            print(f"  ✅ PMI: {pmi_data.get('current', 'N/A')}")
            
            # 2. 公債殖利率與利率曲線
            yield_data = self._fetch_yield_data()
            self.indicators['yield_data'] = yield_data
            spread = yield_data.get('yield_curve', {}).get('spread', 'N/A')
            print(f"  ✅ 殖利率曲線利差: {spread}")
            
            # 3. 就業數據
            employment_data = self._fetch_employment_data()
            self.indicators['employment'] = employment_data
            print(f"  ✅ 失業率: {employment_data.get('unemployment_rate', 'N/A')}%")
            
            # 4. 通膨數據
            inflation_data = self._fetch_inflation_data()
            self.indicators['inflation'] = inflation_data
            print(f"  ✅ CPI年增率: {inflation_data.get('cpi_yoy', 'N/A')}%")
            
            # 5. GDP成長率
            gdp_data = self._fetch_gdp_data()
            self.indicators['gdp'] = gdp_data
            print(f"  ✅ GDP成長率: {gdp_data.get('us_gdp_growth', 'N/A')}%")
            
            # 6. 消費者信心
            confidence_data = self._fetch_confidence_data()
            self.indicators['confidence'] = confidence_data
            print(f"  ✅ 消費者信心: {confidence_data.get('consumer_confidence', 'N/A')}")
            
            # 7. 台灣經濟指標
            tw_data = self._fetch_taiwan_indicators()
            self.indicators['taiwan'] = tw_data
            print(f"  ✅ 台灣: PMI={tw_data.get('pmi', 'N/A')}, 出口={tw_data.get('export_growth', 'N/A')}%")
            
            self.last_update = datetime.now()
            print("\n✅ 數據獲取完成！")
            
            return self.indicators
            
        except Exception as e:
            print(f"⚠️ 獲取數據時發生錯誤: {e}")
            return self._fetch_backup_data()
    
    def _fetch_pmi(self) -> Dict:
        """獲取PMI數據"""
        try:
            if self.fred_api_key:
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    'series_id': 'MANEMP',  # 製造業就業作為PMI替代
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': 3
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'observations' in data and len(data['observations']) >= 2:
                        current = float(data['observations'][0]['value'])
                        previous = float(data['observations'][1]['value'])
                        # 轉換為PMI形式（50為中立）
                        pmi_current = 50 + (current - previous) / 10
                        return {
                            'current': round(pmi_current, 1),
                            'previous': 50.0,
                            'change': round(pmi_current - 50, 1),
                            'trend': 'up' if pmi_current > 50 else 'down',
                            'date': data['observations'][0]['date'],
                            'source': 'FRED'
                        }
        except Exception as e:
            print(f"    PMI API錯誤: {e}")
        
        # 模擬數據（基於最新市場狀況）
        return {
            'current': 52.8,
            'previous': 51.5,
            'change': 1.3,
            'trend': 'up',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'threshold': 50.0,
            'source': 'simulated'
        }
    
    def _fetch_yield_data(self) -> Dict:
        """獲取公債殖利率數據"""
        try:
            symbols = {
                '10y': '^TNX',
                '2y': '^FVX',
                '3m': '^IRX'
            }
            
            yield_data = {}
            for key, symbol in symbols.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='1mo')
                if not hist.empty:
                    current = float(hist['Close'].iloc[-1])
                    previous = float(hist['Close'].iloc[0])
                    yield_data[key] = {
                        'current': round(current, 2),
                        'previous': round(previous, 2),
                        'change': round(current - previous, 2)
                    }
            
            # 計算利率曲線（10年-2年利差）
            if '10y' in yield_data and '2y' in yield_data:
                spread = yield_data['10y']['current'] - yield_data['2y']['current']
                yield_data['yield_curve'] = {
                    'spread': round(spread, 2),
                    'is_inverted': spread < 0,
                    'strength': 'steep' if spread > 1.0 else 'normal' if spread > 0 else 'flat' if spread > -0.5 else 'inverted'
                }
            
            return yield_data
            
        except Exception as e:
            print(f"    殖利率數據錯誤: {e}")
            return {
                '10y': {'current': 4.35, 'previous': 4.20, 'change': 0.15},
                '2y': {'current': 4.15, 'previous': 4.05, 'change': 0.10},
                'yield_curve': {'spread': 0.20, 'is_inverted': False, 'strength': 'normal'}
            }
    
    def _fetch_employment_data(self) -> Dict:
        """獲取就業數據"""
        try:
            if self.fred_api_key:
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    'series_id': 'UNRATE',
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': 3
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'observations' in data and len(data['observations']) >= 2:
                        current = float(data['observations'][0]['value'])
                        previous = float(data['observations'][1]['value'])
                        return {
                            'unemployment_rate': current,
                            'previous_unemployment': previous,
                            'trend': 'improving' if current < previous else 'worsening' if current > previous else 'stable',
                            'date': data['observations'][0]['date'],
                            'source': 'FRED'
                        }
        except Exception as e:
            print(f"    就業數據錯誤: {e}")
        
        return {
            'unemployment_rate': 4.1,
            'previous_unemployment': 4.2,
            'nonfarm_payrolls': 185000,
            'previous_payrolls': 165000,
            'trend': 'improving',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'simulated'
        }
    
    def _fetch_inflation_data(self) -> Dict:
        """獲取通膨數據"""
        try:
            if self.fred_api_key:
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    'series_id': 'CPIAUCSL',
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': 13
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'observations' in data and len(data['observations']) >= 13:
                        current = float(data['observations'][0]['value'])
                        year_ago = float(data['observations'][12]['value'])
                        cpi_yoy = ((current - year_ago) / year_ago) * 100
                        return {
                            'cpi_yoy': round(cpi_yoy, 1),
                            'trend': 'declining' if cpi_yoy < 3.5 else 'rising',
                            'fed_target': 2.0,
                            'date': data['observations'][0]['date'],
                            'source': 'FRED'
                        }
        except Exception as e:
            print(f"    通膨數據錯誤: {e}")
        
        return {
            'cpi_yoy': 2.9,
            'previous_cpi': 3.1,
            'core_cpi_yoy': 3.3,
            'previous_core_cpi': 3.5,
            'trend': 'declining',
            'fed_target': 2.0,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'simulated'
        }
    
    def _fetch_gdp_data(self) -> Dict:
        """獲取GDP數據"""
        try:
            if self.fred_api_key:
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    'series_id': 'A191RL1Q225SBEA',  # Real GDP Growth
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': 2
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'observations' in data and len(data['observations']) >= 2:
                        current = float(data['observations'][0]['value'])
                        previous = float(data['observations'][1]['value'])
                        return {
                            'us_gdp_growth': current,
                            'previous_us_gdp': previous,
                            'trend': 'improving' if current > previous else 'stable',
                            'date': data['observations'][0]['date'],
                            'source': 'FRED'
                        }
        except Exception as e:
            print(f"    GDP數據錯誤: {e}")
        
        return {
            'us_gdp_growth': 2.8,
            'previous_us_gdp': 3.0,
            'trend': 'stable',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'simulated'
        }
    
    def _fetch_confidence_data(self) -> Dict:
        """獲取消費者信心數據"""
        return {
            'consumer_confidence': 108.5,
            'previous_confidence': 105.0,
            'change': 3.5,
            'trend': 'improving',
            'source': 'simulated'
        }
    
    def _fetch_taiwan_indicators(self) -> Dict:
        """獲取台灣經濟指標"""
        return {
            'pmi': 53.2,
            'export_growth': 8.5,
            'industrial_production': 5.2,
            'consumer_confidence': 72.5,
            'leading_indicator': 101.5,
            'trend': 'expanding',
            'source': 'simulated'
        }
    
    def _fetch_backup_data(self) -> Dict:
        """備用數據源"""
        print("⚠️ 使用模擬數據進行分析...")
        
        self.indicators = {
            'pmi': {'current': 52.8, 'previous': 51.5, 'trend': 'up', 'source': 'backup'},
            'yield_data': {
                '10y': {'current': 4.35},
                '2y': {'current': 4.15},
                'yield_curve': {'spread': 0.20, 'is_inverted': False, 'strength': 'normal'}
            },
            'employment': {'unemployment_rate': 4.1, 'trend': 'improving'},
            'inflation': {'cpi_yoy': 2.9, 'trend': 'declining', 'fed_target': 2.0},
            'gdp': {'us_gdp_growth': 2.8, 'trend': 'stable'},
            'confidence': {'consumer_confidence': 108.5, 'trend': 'improving'},
            'taiwan': {'pmi': 53.2, 'export_growth': 8.5, 'trend': 'expanding'}
        }
        
        self.last_update = datetime.now()
        return self.indicators
    
    def analyze_cycle(self) -> Tuple[str, float, Dict]:
        """
        分析當前經濟循環階段
        
        Returns:
        --------
        stage : str
            當前階段代碼
        confidence : float
            信心度 (0-1)
        scores : Dict
            各階段詳細分數
        """
        
        # 初始化分數
        scores = {stage: 0.0 for stage in self.stages.keys()}
        
        # 1. PMI分析
        pmi = self.indicators.get('pmi', {})
        pmi_current = pmi.get('current', 50)
        pmi_trend = pmi.get('trend', 'stable')
        
        if pmi_current > 55 and pmi_trend == 'up':
            scores['overheat'] += self.weights['pmi'] * 100 * 0.7
            scores['expansion'] += self.weights['pmi'] * 100 * 0.3
        elif pmi_current > 52 and pmi_trend == 'up':
            scores['recovery'] += self.weights['pmi'] * 100 * 0.8
            scores['expansion'] += self.weights['pmi'] * 100 * 0.2
        elif pmi_current > 50 and pmi_trend in ['stable', 'up']:
            scores['expansion'] += self.weights['pmi'] * 100
        elif pmi_current < 50 and pmi_trend == 'down':
            scores['recession'] += self.weights['pmi'] * 100 * 0.7
            scores['slowdown'] += self.weights['pmi'] * 100 * 0.3
        elif pmi_current < 45:
            scores['recession'] += self.weights['pmi'] * 100
        else:
            scores['slowdown'] += self.weights['pmi'] * 100
        
        # 2. 利率曲線分析
        yield_data = self.indicators.get('yield_data', {})
        yield_curve = yield_data.get('yield_curve', {})
        spread = yield_curve.get('spread', 0)
        
        if spread > 1.0:
            scores['recovery'] += self.weights['yield_curve'] * 100
        elif spread > 0.3:
            scores['expansion'] += self.weights['yield_curve'] * 100 * 0.7
            scores['recovery'] += self.weights['yield_curve'] * 100 * 0.3
        elif spread > -0.2:
            scores['slowdown'] += self.weights['yield_curve'] * 100
        else:
            scores['recession'] += self.weights['yield_curve'] * 100
        
        # 3. 失業率分析
        employment = self.indicators.get('employment', {})
        unemployment = employment.get('unemployment_rate', 4.0)
        emp_trend = employment.get('trend', 'stable')
        
        if unemployment < 4.0 and emp_trend == 'improving':
            scores['expansion'] += self.weights['unemployment'] * 100
        elif unemployment < 5.0 and emp_trend in ['stable', 'improving']:
            scores['recovery'] += self.weights['unemployment'] * 100
        elif unemployment > 6.0 and emp_trend == 'worsening':
            scores['recession'] += self.weights['unemployment'] * 100
        elif unemployment > 5.0:
            scores['slowdown'] += self.weights['unemployment'] * 100
        else:
            scores['expansion'] += self.weights['unemployment'] * 100 * 0.5
            scores['recovery'] += self.weights['unemployment'] * 100 * 0.5
        
        # 4. 通膨分析
        inflation = self.indicators.get('inflation', {})
        cpi = inflation.get('cpi_yoy', 2.5)
        inf_trend = inflation.get('trend', 'stable')
        
        if cpi > 5.0 and inf_trend == 'rising':
            scores['overheat'] += self.weights['inflation'] * 100
        elif cpi > 3.5 and inf_trend == 'rising':
            scores['overheat'] += self.weights['inflation'] * 100 * 0.6
            scores['expansion'] += self.weights['inflation'] * 100 * 0.4
        elif cpi < 1.5 and inf_trend == 'declining':
            scores['recession'] += self.weights['inflation'] * 100 * 0.5
            scores['slowdown'] += self.weights['inflation'] * 100 * 0.5
        elif 1.5 <= cpi <= 3.5:
            scores['expansion'] += self.weights['inflation'] * 100
        
        # 5. GDP成長分析
        gdp = self.indicators.get('gdp', {})
        gdp_growth = gdp.get('us_gdp_growth', 2.0)
        gdp_trend = gdp.get('trend', 'stable')
        
        if gdp_growth > 3.0 and gdp_trend == 'improving':
            scores['expansion'] += self.weights['gdp_growth'] * 100
        elif gdp_growth > 2.0 and gdp_trend in ['improving', 'stable']:
            scores['recovery'] += self.weights['gdp_growth'] * 100 * 0.6
            scores['expansion'] += self.weights['gdp_growth'] * 100 * 0.4
        elif gdp_growth < 0:
            scores['recession'] += self.weights['gdp_growth'] * 100
        elif gdp_growth < 1.0:
            scores['slowdown'] += self.weights['gdp_growth'] * 100
        else:
            scores['expansion'] += self.weights['gdp_growth'] * 100 * 0.5
            scores['recovery'] += self.weights['gdp_growth'] * 100 * 0.5
        
        # 找出最高分階段
        max_score = max(scores.values())
        total_score = sum(scores.values())
        
        if total_score > 0:
            confidence = max_score / total_score
        else:
            confidence = 0.0
        
        # 確定當前階段
        for stage, score in scores.items():
            if score == max_score:
                self.current_stage = stage
                self.stage_confidence = confidence
                break
        
        return self.current_stage, confidence, scores
    
    def get_asset_allocation(self) -> Dict:
        """
        根據當前階段提供資產配置建議
        """
        allocation_templates = {
            'recovery': {
                'tw_stocks': 50,
                'us_stocks': 25,
                'bonds': 15,
                'cash': 10,
                'focus': ['成長股', 'AI概念', '半導體']
            },
            'expansion': {
                'tw_stocks': 45,
                'us_stocks': 25,
                'bonds': 20,
                'cash': 10,
                'focus': ['價值股', '工業', '原物料']
            },
            'overheat': {
                'tw_stocks': 35,
                'us_stocks': 20,
                'bonds': 30,
                'cash': 15,
                'focus': ['能源', '必需消費', '高股息']
            },
            'slowdown': {
                'tw_stocks': 30,
                'us_stocks': 15,
                'bonds': 40,
                'cash': 15,
                'focus': ['公用事業', '電信', '防禦型']
            },
            'recession': {
                'tw_stocks': 20,
                'us_stocks': 10,
                'bonds': 45,
                'cash': 25,
                'focus': ['現金', '公債', '黃金']
            }
        }
        
        base_allocation = allocation_templates.get(
            self.current_stage,
            {'tw_stocks': 40, 'us_stocks': 20, 'bonds': 30, 'cash': 10, 'focus': []}
        )
        
        # 根據信心度調整
        if self.stage_confidence < 0.6:
            # 低信心度時增加現金比例
            adjustment = 5
            base_allocation['tw_stocks'] -= adjustment
            base_allocation['cash'] += adjustment
        
        return base_allocation
    
    def get_sector_recommendations(self) -> List[Dict]:
        """
        獲取產業配置建議
        """
        sector_recommendations = {
            'recovery': [
                {'sector': '科技/半導體', 'action': '加碼', 'weight': 30, 'reason': '利率環境改善，創新周期啟動'},
                {'sector': '金融', 'action': '加碼', 'weight': 20, 'reason': '利率曲線正常化有利淨利差'},
                {'sector': 'AI伺服器', 'action': '加碼', 'weight': 25, 'reason': 'AI需求持續強勁'},
                {'sector': '非必需消費', 'action': '持有', 'weight': 15, 'reason': '消費者信心回升'},
                {'sector': '公用事業', 'action': '減碼', 'weight': 10, 'reason': '防禦性需求降低'}
            ],
            'expansion': [
                {'sector': '工業', 'action': '加碼', 'weight': 25, 'reason': '資本支出增加'},
                {'sector': '材料/原物料', 'action': '加碼', 'weight': 20, 'reason': '需求持續成長'},
                {'sector': '科技', 'action': '持有', 'weight': 25, 'reason': '估值可能偏高但基本面仍佳'},
                {'sector': '金融', 'action': '持有', 'weight': 20, 'reason': '經濟穩健支撐'},
                {'sector': '能源', 'action': '觀望', 'weight': 10, 'reason': '供需動態觀察'}
            ],
            'overheat': [
                {'sector': '能源', 'action': '加碼', 'weight': 25, 'reason': '通膨環境有利'},
                {'sector': '必需消費', 'action': '加碼', 'weight': 25, 'reason': '抗通膨特性'},
                {'sector': '原物料', 'action': '持有', 'weight': 20, 'reason': '通膨對沖'},
                {'sector': '科技', 'action': '減碼', 'weight': 15, 'reason': '高估值風險'},
                {'sector': '金融', 'action': '持有', 'weight': 15, 'reason': '升息環境有利有弊'}
            ],
            'slowdown': [
                {'sector': '公用事業', 'action': '加碼', 'weight': 25, 'reason': '穩定現金流'},
                {'sector': '電信', 'action': '加碼', 'weight': 20, 'reason': '防禦性強'},
                {'sector': '必需消費', 'action': '加碼', 'weight': 20, 'reason': '需求穩定'},
                {'sector': '高股息', 'action': '加碼', 'weight': 25, 'reason': '現金流保護'},
                {'sector': '非必需消費', 'action': '減碼', 'weight': 10, 'reason': '需求敏感'}
            ],
            'recession': [
                {'sector': '必需消費', 'action': '加碼', 'weight': 25, 'reason': '需求剛性'},
                {'sector': '醫療保健', 'action': '加碼', 'weight': 25, 'reason': '防禦性強'},
                {'sector': '公用事業', 'action': '加碼', 'weight': 20, 'reason': '高股息防禦'},
                {'sector': '公債/債券', 'action': '加碼', 'weight': 20, 'reason': '避險資產'},
                {'sector': '科技', 'action': '減碼', 'weight': 10, 'reason': '景氣敏感'}
            ]
        }
        
        return sector_recommendations.get(self.current_stage, [])
    
    def get_stock_picks(self) -> Dict:
        """
        根據當前階段獲取推薦股票
        """
        stage_info = self.stages.get(self.current_stage, {})
        recommended_sectors = stage_info.get('tw_sectors', [])
        
        picks = {
            'taiwan': [],
            'us_etf': stage_info.get('us_etf', [])
        }
        
        for sector in recommended_sectors:
            if sector in self.tw_sector_stocks:
                picks['taiwan'].extend(self.tw_sector_stocks[sector])
        
        # 加入 AI 相關股票（當前熱門）
        if self.current_stage in ['recovery', 'expansion']:
            picks['taiwan'].extend(self.tw_sector_stocks.get('AI伺服器', []))
        
        return picks
    
    def check_warnings(self) -> List[Dict]:
        """檢查潛在風險警告"""
        warnings = []
        
        # PMI警告
        pmi = self.indicators.get('pmi', {}).get('current', 50)
        if pmi < 48:
            warnings.append({
                'level': 'high',
                'category': 'PMI',
                'message': f'PMI={pmi}，低於50萎縮線，製造業可能收縮',
                'action': '減少景氣循環股配置'
            })
        elif pmi < 50:
            warnings.append({
                'level': 'medium',
                'category': 'PMI',
                'message': f'PMI={pmi}，接近萎縮區間，需密切關注',
                'action': '維持防禦性配置'
            })
        
        # 利率曲線警告
        spread = self.indicators.get('yield_data', {}).get('yield_curve', {}).get('spread', 0)
        if spread < -0.5:
            warnings.append({
                'level': 'high',
                'category': '殖利率曲線',
                'message': f'利差={spread}%，曲線倒掛超過0.5%，衰退風險大增',
                'action': '增加現金和防禦性資產'
            })
        elif spread < 0:
            warnings.append({
                'level': 'medium',
                'category': '殖利率曲線',
                'message': f'利差={spread}%，曲線小幅倒掛，注意衰退訊號',
                'action': '逐步減少風險資產'
            })
        
        # 通膨警告
        cpi = self.indicators.get('inflation', {}).get('cpi_yoy', 2.0)
        if cpi > 5.0:
            warnings.append({
                'level': 'high',
                'category': '通膨',
                'message': f'CPI={cpi}%，通膨壓力嚴重，央行可能大幅升息',
                'action': '增加抗通膨資產（能源、必需消費）'
            })
        elif cpi > 4.0:
            warnings.append({
                'level': 'medium',
                'category': '通膨',
                'message': f'CPI={cpi}%，通膨高於Fed目標，注意利率政策',
                'action': '減少利率敏感股（科技成長股）'
            })
        
        # 失業率警告
        unemployment = self.indicators.get('employment', {}).get('unemployment_rate', 4.0)
        if unemployment > 5.5:
            warnings.append({
                'level': 'high',
                'category': '就業市場',
                'message': f'失業率={unemployment}%，就業市場惡化明顯',
                'action': '增加防禦性配置'
            })
        
        return warnings
    
    def generate_report(self) -> str:
        """
        生成分析報告
        """
        stage_info = self.stages.get(self.current_stage, {})
        
        report = f"""
{'='*70}
🌐 總經循環定位分析報告
📅 生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

📊 【當前經濟階段】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
階段: {stage_info.get('name', '未知')} ({self.current_stage})
信心度: {self.stage_confidence:.1%}
描述: {stage_info.get('description', '')}

📈 【關鍵指標現況】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 製造業PMI: {self.indicators.get('pmi', {}).get('current', 'N/A')} 
   趨勢: {self.indicators.get('pmi', {}).get('trend', 'N/A')} | 榮枯線: 50
   
2. 殖利率曲線(10Y-2Y): {self.indicators.get('yield_data', {}).get('yield_curve', {}).get('spread', 'N/A')}%
   狀態: {self.indicators.get('yield_data', {}).get('yield_curve', {}).get('strength', 'N/A')}
   10年期: {self.indicators.get('yield_data', {}).get('10y', {}).get('current', 'N/A')}%
   2年期: {self.indicators.get('yield_data', {}).get('2y', {}).get('current', 'N/A')}%
   
3. 失業率: {self.indicators.get('employment', {}).get('unemployment_rate', 'N/A')}%
   趨勢: {self.indicators.get('employment', {}).get('trend', 'N/A')}
   
4. CPI年增率: {self.indicators.get('inflation', {}).get('cpi_yoy', 'N/A')}%
   趨勢: {self.indicators.get('inflation', {}).get('trend', 'N/A')} | Fed目標: 2.0%
   
5. GDP成長率: {self.indicators.get('gdp', {}).get('us_gdp_growth', 'N/A')}%
   趨勢: {self.indicators.get('gdp', {}).get('trend', 'N/A')}

6. 台灣經濟指標:
   PMI: {self.indicators.get('taiwan', {}).get('pmi', 'N/A')}
   出口成長: {self.indicators.get('taiwan', {}).get('export_growth', 'N/A')}%

💰 【資產配置建議】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        allocation = self.get_asset_allocation()
        report += f"""
台股: {allocation.get('tw_stocks', 0)}%
美股: {allocation.get('us_stocks', 0)}%
債券: {allocation.get('bonds', 0)}%
現金: {allocation.get('cash', 0)}%

投資重點: {', '.join(allocation.get('focus', []))}

📈 【產業配置建議】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        sectors = self.get_sector_recommendations()
        for sector in sectors:
            action_emoji = '🟢' if sector['action'] == '加碼' else '🟡' if sector['action'] == '持有' else '🔴'
            report += f"{action_emoji} {sector['sector']}: {sector['action']} ({sector['weight']}%)\n"
            report += f"   └─ {sector['reason']}\n"
        
        report += f"""
🎯 【推薦標的】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        picks = self.get_stock_picks()
        report += "台股:\n"
        for stock in picks.get('taiwan', [])[:10]:
            report += f"  • {stock['symbol']} {stock['name']}\n"
        
        report += f"\n美股ETF: {', '.join(picks.get('us_etf', []))}\n"
        
        # 風險警告
        warnings = self.check_warnings()
        if warnings:
            report += f"""
⚠️ 【風險警告】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            for warning in warnings:
                level_emoji = '🔴' if warning['level'] == 'high' else '🟡'
                report += f"{level_emoji} [{warning['category']}] {warning['message']}\n"
                report += f"   建議: {warning['action']}\n"
        
        report += f"""
📋 【監控重點】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. PMI 跌破 50 → 考慮轉向防禦
2. 殖利率曲線倒掛持續 3 個月 → 衰退風險增加
3. 失業率連續上升 → 企業獲利可能承壓
4. CPI 持續高於 3% → 央行可能緊縮

📅 【建議更新頻率】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每月更新一次，特別注意：
- PMI數據（每月第1個工作日）
- 非農就業（每月第1個星期五）
- CPI數據（每月中旬）
- Fed利率決議（每6週）

{'='*70}
"""
        return report
    
    def save_report(self, directory: str = "reports"):
        """保存報告到檔案"""
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, f"economic_cycle_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 報告已保存至: {filename}")
        return filename
    
    def to_dict(self) -> Dict:
        """將分析結果轉換為字典（用於API輸出）"""
        return {
            'stage': self.current_stage,
            'stage_name': self.stages.get(self.current_stage, {}).get('name', ''),
            'stage_description': self.stages.get(self.current_stage, {}).get('description', ''),
            'confidence': round(self.stage_confidence, 3),
            'indicators': self.indicators,
            'allocation': self.get_asset_allocation(),
            'sector_recommendations': self.get_sector_recommendations(),
            'stock_picks': self.get_stock_picks(),
            'warnings': self.check_warnings(),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


def main():
    """主程式"""
    print("=" * 70)
    print("🌐 總經循環定位系統 v2.0")
    print("=" * 70)
    
    # 從 config 讀取 API 金鑰（如果存在）
    FRED_API_KEY = ""
    try:
        from config import FRED_API_KEY
    except ImportError:
        print("💡 提示: 若有 FRED API 金鑰，請在 config.py 中設定以獲取真實數據")
    
    # 初始化檢測器
    detector = EconomicCycleDetector(fred_api_key=FRED_API_KEY)
    
    # 獲取數據
    print("\n[步驟1] 獲取經濟數據...")
    indicators = detector.fetch_all_indicators()
    
    # 分析循環階段
    print("\n[步驟2] 分析經濟循環階段...")
    stage, confidence, scores = detector.analyze_cycle()
    
    # 顯示結果
    stage_info = detector.stages.get(stage, {})
    print(f"\n✅ 分析結果:")
    print(f"   當前階段: {stage_info.get('name')} ({stage})")
    print(f"   信心度: {confidence:.1%}")
    print(f"   描述: {stage_info.get('description')}")
    
    print(f"\n📊 各階段分數:")
    for s, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        name = detector.stages.get(s, {}).get('name', s)
        bar = '█' * int(score / 5) + '░' * (20 - int(score / 5))
        print(f"   {name}: {bar} {score:.1f}")
    
    # 顯示配置建議
    print(f"\n💰 資產配置建議:")
    allocation = detector.get_asset_allocation()
    for asset, percent in allocation.items():
        if asset != 'focus':
            print(f"   {asset}: {percent}%")
    print(f"   重點: {', '.join(allocation.get('focus', []))}")
    
    # 生成完整報告
    print(f"\n[步驟3] 生成完整報告...")
    report = detector.generate_report()
    print(report)
    
    # 保存報告
    detector.save_report(directory="reports")
    
    print("\n" + "=" * 70)
    print("✅ 分析完成！")
    print("=" * 70)
    
    return detector


if __name__ == "__main__":
    main()
