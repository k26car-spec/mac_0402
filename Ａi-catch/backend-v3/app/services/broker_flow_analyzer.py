"""
券商分點進出分析服務
專門抓取並分析富邦新店等關鍵券商分點的買賣資料
"""

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import time
import re
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BrokerFlowAnalyzer:
    """券商分點進出分析器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'identity',  # 不使用壓縮，避免解碼問題
            'Connection': 'keep-alive',
        })
        
        # 關鍵券商分點列表（使用正確的分點代碼）
        # 格式: broker_code = 券商代碼, sub_broker_code = 分點代碼
        self.key_brokers = {
            '富邦-新店': {'code': '9600', 'sub_code': '9661', 'type': 'domestic'},  # 新店分點 9661
            '富邦-總公司': {'code': '9600', 'sub_code': '9600', 'type': 'domestic'},
            '富邦-陽明': {'code': '9600', 'sub_code': '9604', 'type': 'domestic'},
            '富邦-竹北': {'code': '9600', 'sub_code': '9624', 'type': 'domestic'},
            '富邦-新竹': {'code': '9600', 'sub_code': '9647', 'type': 'domestic'},
            '富邦-永和': {'code': '9600', 'sub_code': '9654', 'type': 'domestic'},
        }
        
        # 快取機制
        self.cache = {}
        self.cache_duration = 300  # 5分鐘快取
        
    def fetch_fubon_broker_data(self, 
                                broker_code: str = '9600',
                                sub_broker_code: str = '9661',  # 預設使用新店
                                start_date: str = None,
                                end_date: str = None) -> pd.DataFrame:
        """
        抓取富邦券商分點資料（使用進階爬蟲）
        
        Args:
            broker_code: 券商代碼 (9600=富邦)
            sub_broker_code: 分點代碼 (9661=新店, 9600=總公司)
            start_date: 開始日期 (格式: YYYY-MM-DD)
            end_date: 結束日期 (格式: YYYY-MM-DD)
            
        Returns:
            DataFrame 包含券商買賣資料
        """
        try:
            # 使用進階爬蟲
            from .advanced_broker_crawler import advanced_broker_crawler
            
            logger.info(f"🔍 使用進階爬蟲抓取: 券商={broker_code}, 分點={sub_broker_code}")
            
            df = advanced_broker_crawler.get_broker_flow_by_date(
                broker_code=broker_code,
                sub_broker_code=sub_broker_code  # 傳遞正確的分點代碼
            )
            
            if not df.empty:
                logger.info(f"✅ 成功抓取 {len(df)} 筆券商資料")
            else:
                logger.warning("⚠️ 未抓取到資料")
            
            return df
                
        except Exception as e:
            logger.error(f"❌ 抓取富邦券商資料失敗: {e}")
            return pd.DataFrame()
    
    def _fetch_fubon_broker_data_fallback(self, 
                                          broker_code: str = '9600',
                                          start_date: str = None,
                                          end_date: str = None) -> pd.DataFrame:
        """備用抓取方法"""
        try:
            # 設定日期範圍
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
            
            # 富邦證券分點查詢網址
            url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"
            
            params = {
                'a': broker_code,
                'b': broker_code,
                'c': 'E',
                'e': start_date,
                'f': end_date
            }
            
            logger.info(f"🔍 備用方案抓取: {broker_code}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            response.encoding = 'big5'
            
            # 簡化解析
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if not tables:
                return pd.DataFrame()
            
            # 保存HTML以供調試
            debug_file = f'debug_broker_{broker_code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"已保存HTML到 {debug_file}")
            
            return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ 備用方案也失敗: {e}")
            return pd.DataFrame()
    
    def _parse_number(self, text: str) -> int:
        """解析數字字串"""
        try:
            # 移除逗號和空白
            cleaned = text.replace(',', '').replace(' ', '').strip()
            if cleaned == '' or cleaned == '-':
                return 0
            return int(cleaned)
        except:
            return 0
    
    def get_broker_flow_summary(self, 
                               stock_code: str,
                               days: int = 5) -> Dict:
        """
        獲取特定股票的券商進出摘要
        
        Args:
            stock_code: 股票代碼
            days: 分析天數
            
        Returns:
            券商進出分析結果
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            all_broker_data = []
            
            # 抓取所有關鍵券商的資料
            for broker_name, broker_info in self.key_brokers.items():
                broker_code = broker_info['code']
                sub_broker_code = broker_info.get('sub_code', broker_code)
                
                df = self.fetch_fubon_broker_data(
                    broker_code=broker_code,
                    sub_broker_code=sub_broker_code
                )
                
                if not df.empty:
                    # 篩選特定股票
                    stock_df = df[df['stock_code'] == stock_code].copy()  # 使用 .copy() 避免警告
                    
                    if not stock_df.empty:
                        stock_df.loc[:, 'broker_name'] = broker_name  # 使用 .loc 避免警告
                        all_broker_data.append(stock_df)
                
                # 避免請求過快
                time.sleep(1)
            
            if not all_broker_data:
                return self._empty_broker_summary()
            
            # 合併所有券商資料
            combined_df = pd.concat(all_broker_data, ignore_index=True)
            
            # 計算統計資料
            summary = self._calculate_broker_statistics(combined_df, stock_code)
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 獲取券商進出摘要失敗: {e}")
            return self._empty_broker_summary()
    
    def _calculate_broker_statistics(self, df: pd.DataFrame, stock_code: str) -> Dict:
        """計算券商統計資料"""
        
        # 總買賣統計
        total_buy = df['buy_count'].sum()
        total_sell = df['sell_count'].sum()
        total_net = df['net_count'].sum()
        
        # 各券商明細
        broker_details = {}
        for broker_name in df['broker_name'].unique():
            broker_df = df[df['broker_name'] == broker_name]
            
            broker_details[broker_name] = {
                'buy_count': int(broker_df['buy_count'].sum()),
                'sell_count': int(broker_df['sell_count'].sum()),
                'net_count': int(broker_df['net_count'].sum()),
                'trend': self._determine_trend(broker_df['net_count'].sum()),
                'days_active': len(broker_df)
            }
        
        # 判斷整體趨勢
        flow_trend = self._determine_overall_trend(total_net, total_buy)
        
        # 檢測異常活動
        unusual_activity = self._detect_unusual_activity(df)
        
        # 法人比例估算（外資券商）
        foreign_brokers = ['美林', '瑞銀', '摩根士丹利', '高盛']
        foreign_net = sum(
            broker_details.get(b, {}).get('net_count', 0) 
            for b in foreign_brokers
        )
        
        institutional_ratio = (abs(foreign_net) / max(total_buy, 1)) * 100 if total_buy > 0 else 0
        
        return {
            'stock_code': stock_code,
            'analysis_period_days': len(df['date'].unique()),
            'total_buy_count': int(total_buy),
            'total_sell_count': int(total_sell),
            'net_flow_count': int(total_net),
            'flow_trend': flow_trend,
            'unusual_activity': unusual_activity,
            'institutional_ratio': round(institutional_ratio, 2),
            'broker_details': broker_details,
            'key_observations': self._generate_observations(broker_details, total_net),
            'confidence_score': self._calculate_confidence(df),
            'last_update': datetime.now().isoformat()
        }
    
    def _determine_trend(self, net_count: int) -> str:
        """判斷買賣趨勢"""
        if net_count > 500:
            return 'strong_buying'
        elif net_count > 100:
            return 'buying'
        elif net_count < -500:
            return 'strong_selling'
        elif net_count < -100:
            return 'selling'
        else:
            return 'neutral'
    
    def _determine_overall_trend(self, total_net: int, total_buy: int) -> str:
        """判斷整體趨勢"""
        if total_net > 1000:
            return 'strong_buying'
        elif total_net > 300:
            return 'buying'
        elif total_net < -1000:
            return 'strong_selling'
        elif total_net < -300:
            return 'selling'
        else:
            return 'neutral'
    
    def _detect_unusual_activity(self, df: pd.DataFrame) -> bool:
        """檢測異常活動"""
        # 如果單日買賣量超過平均的2倍，視為異常
        daily_volume = df.groupby('date')['buy_count'].sum()
        
        if len(daily_volume) < 2:
            return False
        
        mean_volume = daily_volume.mean()
        max_volume = daily_volume.max()
        
        return max_volume > mean_volume * 2
    
    def _generate_observations(self, broker_details: Dict, total_net: int) -> List[str]:
        """生成關鍵觀察"""
        observations = []
        
        # 檢查富邦新店動向
        if '富邦-新店' in broker_details:
            fubon_net = broker_details['富邦-新店']['net_count']
            if abs(fubon_net) > 200:
                action = "買超" if fubon_net > 0 else "賣超"
                observations.append(f"富邦新店{action} {abs(fubon_net)} 張")
        
        # 檢查外資動向
        foreign_brokers = ['美林', '瑞銀', '摩根士丹利', '高盛']
        foreign_net = sum(
            broker_details.get(b, {}).get('net_count', 0) 
            for b in foreign_brokers
        )
        
        if abs(foreign_net) > 500:
            action = "買超" if foreign_net > 0 else "賣超"
            observations.append(f"外資券商{action} {abs(foreign_net)} 張")
        
        # 整體趨勢
        if total_net > 1000:
            observations.append("主力大量買進")
        elif total_net < -1000:
            observations.append("主力大量賣出")
        
        return observations
    
    def _calculate_confidence(self, df: pd.DataFrame) -> float:
        """計算信心分數"""
        # 基於資料完整性和券商數量
        broker_count = len(df['broker_name'].unique())
        data_days = len(df['date'].unique())
        
        confidence = min(100, (broker_count * 10) + (data_days * 5))
        
        return round(confidence, 2)
    
    def _empty_broker_summary(self) -> Dict:
        """空的券商摘要"""
        return {
            'stock_code': '',
            'analysis_period_days': 0,
            'total_buy_count': 0,
            'total_sell_count': 0,
            'net_flow_count': 0,
            'flow_trend': 'neutral',
            'unusual_activity': False,
            'institutional_ratio': 0,
            'broker_details': {},
            'key_observations': [],
            'confidence_score': 0,
            'last_update': datetime.now().isoformat()
        }
    
    def get_top_stocks_by_broker(self, 
                                broker_name: str = '富邦-新店',
                                top_n: int = 20,
                                min_net_count: int = 100) -> List[Dict]:
        """
        獲取特定券商買超前N名股票
        如果券商數據不可用，使用證交所法人數據作為備用
        
        Args:
            broker_name: 券商名稱
            top_n: 前N名
            min_net_count: 最小買超張數
            
        Returns:
            股票列表
        """
        try:
            broker_info = self.key_brokers.get(broker_name)
            
            if not broker_info:
                logger.warning(f"⚠️ 未知券商: {broker_name}，使用預設新店(9661)")
                # 預設使用富邦新店
                broker_code = '9600'
                sub_broker_code = '9661'
            else:
                broker_code = broker_info['code']
                sub_broker_code = broker_info.get('sub_code', broker_code)
            
            # 抓取資料
            df = self.fetch_fubon_broker_data(
                broker_code=broker_code,
                sub_broker_code=sub_broker_code
            )
            
            if df.empty:
                logger.warning("⚠️ 富邦新店數據為空（可能是假日或無交易）")
                return []
            
            # 按股票代碼分組統計
            stock_summary = df.groupby('stock_code').agg({
                'stock_name': 'first',
                'buy_count': 'sum',
                'sell_count': 'sum',
                'net_count': 'sum'
            }).reset_index()
            
            # 篩選買超股票
            buy_stocks = stock_summary[stock_summary['net_count'] >= min_net_count]
            
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
                    'broker_name': broker_name,
                    'broker_code': broker_code
                })
            
            logger.info(f"✅ {broker_name} 買超前 {len(result)} 檔股票")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 獲取券商買超股票失敗: {e}")
            logger.info("嘗試使用證交所法人數據作為備用")
            return self._get_twse_institutional_data(top_n)
    
    def _get_twse_institutional_data(self, top_n: int = 20) -> List[Dict]:
        """
        從證交所獲取法人買賣超數據（備用方案）
        """
        try:
            # 嘗試多個日期
            for days_ago in range(0, 7):
                date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
                
                url = f'https://www.twse.com.tw/rwd/zh/fund/T86?date={date}&selectType=ALLBUT0999&response=json'
                
                logger.info(f"🔍 嘗試從證交所獲取 {date} 法人數據...")
                
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and len(data['data']) > 0:
                        logger.info(f"✅ 成功獲取證交所法人數據 ({date})")
                        
                        result = []
                        for row in data['data'][:top_n * 2]:  # 取多一些，後面篩選
                            try:
                                code = row[0].strip()
                                name = row[1].strip()
                                
                                # 跳過 ETF 和期貨
                                if code.startswith('00') or len(code) > 4:
                                    continue
                                
                                buy = int(row[2].replace(',', ''))
                                sell = int(row[3].replace(',', ''))
                                net = int(row[4].replace(',', ''))
                                
                                # 只取買超的
                                if net > 0:
                                    result.append({
                                        'stock_code': code,
                                        'stock_name': name,
                                        'buy_count': buy,
                                        'sell_count': sell,
                                        'net_count': net,
                                        'broker_name': '法人(證交所)',
                                        'broker_code': 'TWSE',
                                        'data_source': '證交所法人買賣超',
                                        'data_date': date
                                    })
                                    
                                    if len(result) >= top_n:
                                        break
                                        
                            except Exception as e:
                                continue
                        
                        if result:
                            logger.info(f"✅ 獲取法人買超前 {len(result)} 檔股票")
                            return result
                
                time.sleep(0.5)  # 避免請求過快
            
            logger.warning("❌ 無法從證交所獲取數據")
            return []
            
        except Exception as e:
            logger.error(f"❌ 獲取證交所法人數據失敗: {e}")
            return []


# 全域實例
broker_flow_analyzer = BrokerFlowAnalyzer()


# ==================== 便捷函數 ====================

def get_fubon_xindan_flow(stock_code: str, days: int = 5) -> Dict:
    """獲取富邦新店對特定股票的進出資料"""
    return broker_flow_analyzer.get_broker_flow_summary(stock_code, days)


def get_fubon_xindan_top_stocks(top_n: int = 20) -> List[Dict]:
    """獲取富邦新店買超前N名股票"""
    return broker_flow_analyzer.get_top_stocks_by_broker('富邦-新店', top_n)


def analyze_broker_consensus(stock_code: str) -> Dict:
    """分析多家券商對特定股票的共識"""
    return broker_flow_analyzer.get_broker_flow_summary(stock_code, days=5)
