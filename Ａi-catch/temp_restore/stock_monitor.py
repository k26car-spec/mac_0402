# stock_monitor.py - 完整系統整合

import sqlite3
import asyncio
import logging
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
from typing import List, Dict
import json
from dotenv import load_dotenv

# 載入 .env 環境變數（郵件配置）
load_dotenv()

from config import (
    DATA_SOURCES, 
    DEFAULT_WATCHLIST, 
    SYSTEM_CONFIG,
    NOTIFICATION_CONFIG,
    AI_MODEL_CONFIG
)
from main_force_detector import MainForceDetector
from async_crawler import AsyncStockCrawler
from ml_predictor import MainForcePredictor
from notifier import MultiChannelNotifier

# 確保必要目錄存在
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('models', exist_ok=True)

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/stock_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class AdvancedStockMonitor:
    """
    進階股票監控系統
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化監控系統
        
        Args:
            config_path: 配置文件路徑（YAML格式）
        """
        # 載入配置
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                'monitoring': SYSTEM_CONFIG,
                'notifications': NOTIFICATION_CONFIG,
                'ai_model': AI_MODEL_CONFIG,
                'watchlist': {'stocks': DEFAULT_WATCHLIST}
            }
        
        # 初始化各個模組
        self.crawler = AsyncStockCrawler()
        self.detector = MainForceDetector()
        
        # 初始化ML模型
        model_path = self.config.get('ai_model', {}).get('path')
        self.predictor = MainForcePredictor(model_path)
        
        # 初始化通知系統
        self.notifier = MultiChannelNotifier(self.config.get('notifications', {}))
        
        # 初始化資料庫
        self.db_path = self.config.get('database', {}).get('path', 'stock_monitor.db')
        self.init_database()
        
        # 解析監控清單（支援新的分類結構）
        self.watchlist = self._parse_watchlist()
        
        # 市值分類門檻
        self.thresholds = self.config.get('watchlist', {}).get('thresholds', {
            'large_cap': 1000,
            'mid_cap': 200,
            'small_cap': 50
        })
        
        # 配置比例
        self.allocation = self.config.get('watchlist', {}).get('allocation', {
            'large_cap': 50,
            'mid_cap': 30,
            'small_cap': 20
        })
        
        # 狀態追蹤
        self.alert_history = {}
        
        logger.info("✅ 系統初始化完成")
        logger.info(f"   📊 大型股: {len(self._get_stocks_by_cap('large_cap'))} 檔 (配置 {self.allocation.get('large_cap', 50)}%)")
        logger.info(f"   📈 中型股: {len(self._get_stocks_by_cap('mid_cap'))} 檔 (配置 {self.allocation.get('mid_cap', 30)}%)")
        logger.info(f"   📉 小型股: {len(self._get_stocks_by_cap('small_cap'))} 檔 (配置 {self.allocation.get('small_cap', 20)}%)")
        logger.info(f"   📦 ETF: {len(self._get_stocks_by_cap('etfs'))} 檔")
    
    def _parse_watchlist(self) -> List[str]:
        """解析監控清單，合併所有分類"""
        wl = self.config.get('watchlist', {})
        all_stocks = []
        
        # 新格式：分類結構
        for cap_type in ['large_cap', 'mid_cap', 'small_cap', 'etfs']:
            stocks = wl.get(cap_type, [])
            if stocks:
                all_stocks.extend(stocks)
        
        # 向後兼容：舊格式 stocks 欄位
        if not all_stocks:
            all_stocks = wl.get('stocks', DEFAULT_WATCHLIST)
        
        return all_stocks
    
    def _get_stocks_by_cap(self, cap_type: str) -> List[str]:
        """取得特定市值分類的股票"""
        return self.config.get('watchlist', {}).get(cap_type, [])
    
    def init_database(self):
        """初始化SQLite資料庫"""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # 建立 stock_alerts 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                features TEXT,
                timestamp DATETIME NOT NULL,
                notified BOOLEAN DEFAULT 0
            )
        ''')
        
        # 建立 stock_alerts 索引
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_stock_code 
            ON stock_alerts(stock_code)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
            ON stock_alerts(timestamp)
        ''')
        
        # 建立 stock_data 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                data_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        # 建立 stock_data 索引
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_data_stock_type 
            ON stock_data(stock_code, data_type)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_data_timestamp 
            ON stock_data(timestamp)
        ''')
        
        # 建立 monitoring_log 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                description TEXT,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        self.conn.commit()
        logger.info(f"✅ 資料庫初始化完成: {self.db_path}")
    
    async def monitoring_callback(self, stock_code: str, data: Dict):
        """
        監控回調函數
        
        Args:
            stock_code: 股票代碼
            data: 股票數據
        """
        try:
            logger.info(f"🔍 分析 {stock_code}...")
            
            # 將數據轉換為DataFrame
            df = self._prepare_dataframe(data)
            
            if df is None or len(df) < 10:
                logger.warning(f"⚠️  {stock_code} 數據不足，跳過分析")
                return
            
            # 特徵提取
            features = self.detector.extract_features(df)
            
            # AI判斷
            is_main_force, confidence = self.detector.detect_main_force(features)
            
            # 也可以使用ML模型預測
            # ml_result = self.predictor.predict(features.iloc[0])
            # is_main_force = ml_result['is_main_force']
            # confidence = ml_result['confidence']
            
            threshold = self.config.get('ai_model', {}).get('confidence_threshold', 0.7)
            
            if is_main_force and confidence > threshold:
                # 避免重複通知（每小時最多一次）
                alert_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d%H')}"
                
                if alert_key not in self.alert_history:
                    logger.info(f"🚨 偵測到主力進場: {stock_code} (信心度: {confidence:.2%})")
                    
                    # 儲存到資料庫
                    self.save_alert(stock_code, confidence, features)
                    
                    # 發送通知
                    await self.send_notification(stock_code, confidence, features)
                    
                    # 記錄通知歷史
                    self.alert_history[alert_key] = datetime.now()
                else:
                    logger.info(f"ℹ️  {stock_code} 主力信號已在本小時內通知過")
            else:
                logger.info(f"✓ {stock_code} 未偵測到主力 (信心度: {confidence:.2%})")
            
            # 儲存股票數據
            self.save_stock_data(stock_code, 'realtime', data)
            
        except Exception as e:
            logger.error(f"❌ 監控回調錯誤 {stock_code}: {e}", exc_info=True)
    
    def _prepare_dataframe(self, data: Dict) -> pd.DataFrame:
        """將爬蟲數據轉換為DataFrame"""
        try:
            # 檢查是否有OHLCV數據
            if 'timestamp' in data and 'close' in data:
                df = pd.DataFrame({
                    'timestamp': data['timestamp'],
                    'open': data.get('open', []),
                    'high': data.get('high', []),
                    'low': data.get('low', []),
                    'close': data['close'],
                    'volume': data.get('volume', [])
                })
                
                # 移除None值
                df = df.dropna()
                
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"DataFrame 準備錯誤: {e}")
            return None
    
    async def send_notification(self, stock_code: str, confidence: float, features: pd.DataFrame):
        """發送多管道通知"""
        
        # 獲取股票中文名稱
        try:
            from stock_names import get_stock_name, get_full_name
            stock_name = get_stock_name(stock_code)
            full_name = get_full_name(stock_code)
        except:
            stock_name = stock_code
            full_name = stock_code
        
        # 提取關鍵特徵
        feature_dict = features.iloc[0].to_dict()
        
        message = f"""
🚨 **主力大單警報** 🚨

📈 股票: {full_name}
⭐ 信心指數: {confidence:.2%}
🕒 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 關鍵特徵:
• 量能比率: {feature_dict.get('volume_ratio', 0):.2f}
• 大單比例: {feature_dict.get('large_order_ratio', 0):.2%}
• 資金流向: {feature_dict.get('money_flow', 0):.2f}
• 法人追蹤: {feature_dict.get('institutional_flow', 0):.2f}
• 型態突破: {feature_dict.get('pattern_breakout', 0):.2%}

🔗 快速連結:
• Yahoo主力: https://tw.stock.yahoo.com/quote/{stock_code}/agent
• 富邦分析: https://www.fubon.com/stock/{stock_code}
        """
        
        await self.notifier.send_all(
            title=f"主力大單警報 - {full_name}",
            message=message.strip(),
            priority="high",
            data={
                'stock_code': stock_code,
                'confidence': confidence,
                'features': feature_dict
            }
        )
    
    def save_alert(self, stock_code: str, confidence: float, features: pd.DataFrame):
        """儲存警示紀錄"""
        try:
            self.cursor.execute('''
                INSERT INTO stock_alerts 
                (stock_code, alert_type, confidence, features, timestamp, notified)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                stock_code,
                'main_force',
                confidence,
                features.to_json(),
                datetime.now().isoformat(),
                True
            ))
            self.conn.commit()
            logger.info(f"✅ 警示已儲存: {stock_code}")
            
        except Exception as e:
            logger.error(f"❌ 儲存警示錯誤: {e}")
    
    def save_stock_data(self, stock_code: str, data_type: str, data: Dict):
        """儲存股票數據"""
        try:
            self.cursor.execute('''
                INSERT INTO stock_data 
                (stock_code, data_type, data_json, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                stock_code,
                data_type,
                json.dumps(data, ensure_ascii=False),
                datetime.now().isoformat()
            ))
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"❌ 儲存數據錯誤: {e}")
    
    def get_historical_alerts(self, days: int = 7) -> List[Dict]:
        """取得歷史警示"""
        try:
            query = '''
                SELECT * FROM stock_alerts 
                WHERE timestamp >= datetime('now', ?)
                ORDER BY timestamp DESC
            '''
            self.cursor.execute(query, (f'-{days} days',))
            
            results = []
            for row in self.cursor.fetchall():
                results.append({
                    'id': row[0],
                    'stock_code': row[1],
                    'alert_type': row[2],
                    'confidence': row[3],
                    'features': row[4],
                    'timestamp': row[5],
                    'notified': row[6]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 查詢歷史警示錯誤: {e}")
            return []
    
    def generate_report(self, days: int = 1) -> str:
        """產生每日報告"""
        alerts = self.get_historical_alerts(days)
        
        if alerts:
            report = f"📊 **主力監控{days}日報告**\n"
            report += f"報告時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"總警示數: {len(alerts)}\n\n"
            
            for alert in alerts:
                stock_code = alert['stock_code']
                confidence = alert['confidence']
                timestamp = alert['timestamp']
                report += f"• {stock_code}: 信心度 {confidence:.2%} ({timestamp})\n"
            
            return report
        
        return f"📊 過去{days}日無主力警示\n"
    
    async def start_monitoring(self):
        """開始監控"""
        logger.info("=" * 50)
        logger.info("🚀 啟動 AI 主力監控系統")
        logger.info("=" * 50)
        logger.info(f"📊 監控清單: {self.watchlist}")
        logger.info(f"⏱️  檢查間隔: {self.config.get('monitoring', {}).get('check_interval', 60)} 秒")
        logger.info(f"⏰ 交易時間監控: {self.config.get('monitoring', {}).get('trading_hours_only', True)}")
        logger.info("=" * 50)
        
        # 記錄啟動事件
        self.cursor.execute('''
            INSERT INTO monitoring_log (event_type, description, timestamp)
            VALUES (?, ?, ?)
        ''', ('system_start', '系統啟動', datetime.now().isoformat()))
        self.conn.commit()
        
        # 開始監控
        interval = self.config.get('monitoring', {}).get('check_interval', 60)
        
        # 從配置讀取是否只在交易時間運行
        trading_hours_only = self.config.get('monitoring', {}).get('trading_hours_only', True)
        
        try:
            await self.crawler.monitor_stream(
                self.watchlist,
                self.monitoring_callback,
                interval=interval,
                ignore_time_check=not trading_hours_only
            )
        except KeyboardInterrupt:
            logger.info("\n⏹️  收到中斷信號")
        except Exception as e:
            logger.error(f"❌ 監控錯誤: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """關閉系統"""
        logger.info("🛑 正在關閉系統...")
        
        # 記錄關閉事件
        self.cursor.execute('''
            INSERT INTO monitoring_log (event_type, description, timestamp)
            VALUES (?, ?, ?)
        ''', ('system_stop', '系統關閉', datetime.now().isoformat()))
        self.conn.commit()
        
        # 生成最終報告
        report = self.generate_report(1)
        logger.info(f"\n{report}")
        
        # 關閉資料庫連接
        if self.conn:
            self.conn.close()
        
        # 關閉爬蟲
        await self.crawler.close()
        
        logger.info("✅ 系統已安全關閉")
    
    def load_watchlist(self) -> List[str]:
        """從配置或數據庫載入監控清單"""
        return self.config.get('watchlist', {}).get('stocks', DEFAULT_WATCHLIST)


async def main():
    """主程式"""
    # 建立必要的目錄
    os.makedirs('logs', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # 建立監控系統
    monitor = AdvancedStockMonitor(config_path='config.yaml')
    
    # 開始監控
    await monitor.start_monitoring()


if __name__ == '__main__':
    # 運行主程式
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程式已終止")
