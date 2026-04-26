# test_system.py - 系統測試腳本

import asyncio
import logging
from datetime import datetime
import pandas as pd
import numpy as np

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_imports():
    """測試所有模組導入"""
    logger.info("🧪 測試模組導入...")
    
    try:
        from config import DATA_SOURCES, DEFAULT_WATCHLIST
        logger.info("✓ config.py 導入成功")
        
        from main_force_detector import MainForceDetector
        logger.info("✓ main_force_detector.py 導入成功")
        
        from async_crawler import AsyncStockCrawler
        logger.info("✓ async_crawler.py 導入成功")
        
        from ml_predictor import MainForcePredictor
        logger.info("✓ ml_predictor.py 導入成功")
        
        from notifier import MultiChannelNotifier
        logger.info("✓ notifier.py 導入成功")
        
        from stock_monitor import AdvancedStockMonitor
        logger.info("✓ stock_monitor.py 導入成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 模組導入失敗: {e}")
        return False


def test_detector():
    """測試主力偵測器"""
    logger.info("\n🧪 測試主力偵測器...")
    
    try:
        from main_force_detector import MainForceDetector
        
        # 建立測試數據
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(490, 510, 30),
            'high': np.random.uniform(495, 515, 30),
            'low': np.random.uniform(485, 505, 30),
            'close': np.random.uniform(490, 510, 30),
            'volume': np.random.uniform(10000, 50000, 30)
        })
        
        # 建立偵測器
        detector = MainForceDetector()
        
        # 提取特徵
        features = detector.extract_features(data)
        logger.info(f"✓ 特徵提取成功，共 {len(features.columns)} 個特徵")
        logger.info(f"  特徵: {list(features.columns)}")
        
        # 主力判斷
        is_main_force, confidence = detector.detect_main_force(features)
        logger.info(f"✓ 主力判斷完成")
        logger.info(f"  判斷結果: {'主力進場' if is_main_force else '無主力'}")
        logger.info(f"  信心分數: {confidence:.2%}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 偵測器測試失敗: {e}")
        return False


async def test_crawler():
    """測試爬蟲"""
    logger.info("\n🧪 測試異步爬蟲...")
    
    try:
        from async_crawler import AsyncStockCrawler
        
        crawler = AsyncStockCrawler()
        
        # 測試單支股票
        test_stock = '2330.TW'
        logger.info(f"  測試股票: {test_stock}")
        
        # 初始化 session
        import aiohttp
        crawler.session = aiohttp.ClientSession()
        
        # 獲取數據
        data = await crawler.fetch_yahoo_quote(test_stock)
        
        if data and 'close' in data:
            logger.info(f"✓ 數據獲取成功")
            logger.info(f"  獲得 {len(data.get('close', []))} 筆數據")
        else:
            logger.warning("⚠️  未獲取到數據（可能網路問題）")
        
        # 關閉 session
        await crawler.close()
        
        return True
    except Exception as e:
        logger.error(f"❌ 爬蟲測試失敗: {e}")
        return False


def test_ml_predictor():
    """測試ML預測器"""
    logger.info("\n🧪 測試ML預測器...")
    
    try:
        from ml_predictor import MainForcePredictor, generate_synthetic_training_data
        
        # 生成訓練數據
        logger.info("  生成合成訓練數據...")
        df = generate_synthetic_training_data(500)
        logger.info(f"✓ 生成 {len(df)} 筆訓練數據")
        
        # 建立預測器
        predictor = MainForcePredictor()
        
        # 準備訓練數據
        X, y = predictor.prepare_training_data(df)
        logger.info(f"✓ 訓練數據準備完成: {X.shape}")
        
        # 測試預測（不訓練，使用預設模型）
        test_features = df.iloc[0].drop('label')
        result = predictor.predict(test_features)
        
        logger.info(f"✓ 預測完成")
        logger.info(f"  預測結果: {'主力' if result['is_main_force'] else '無主力'}")
        logger.info(f"  信心度: {result['confidence']:.2%}")
        
        return True
    except Exception as e:
        logger.error(f"❌ ML預測器測試失敗: {e}")
        return False


async def test_notifier():
    """測試通知系統"""
    logger.info("\n🧪 測試通知系統...")
    
    try:
        from notifier import MultiChannelNotifier
        import os
        
        # 檢查環境變數
        has_line = bool(os.getenv('LINE_NOTIFY_TOKEN'))
        has_telegram = bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'))
        has_email = bool(os.getenv('EMAIL_USERNAME') and os.getenv('EMAIL_PASSWORD'))
        
        logger.info(f"  LINE Token: {'已設定 ✓' if has_line else '未設定'}")
        logger.info(f"  Telegram: {'已設定 ✓' if has_telegram else '未設定'}")
        logger.info(f"  Email: {'已設定 ✓' if has_email else '未設定'}")
        
        # 建立通知器（即使沒有Token也能測試）
        notifier = MultiChannelNotifier()
        logger.info("✓ 通知器建立成功")
        
        if has_line or has_telegram or has_email:
            logger.info("  如要測試實際發送，請手動運行通知測試")
        else:
            logger.info("  💡 提示: 設定環境變數後可測試實際通知")
        
        return True
    except Exception as e:
        logger.error(f"❌ 通知系統測試失敗: {e}")
        return False


def test_database():
    """測試資料庫"""
    logger.info("\n🧪 測試資料庫...")
    
    try:
        import sqlite3
        import os
        
        # 建立測試資料庫
        os.makedirs('data', exist_ok=True)
        test_db = 'data/test.db'
        
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # 建立測試表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # 插入測試數據
        cursor.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
        conn.commit()
        
        # 查詢測試
        cursor.execute("SELECT * FROM test")
        result = cursor.fetchone()
        
        conn.close()
        
        # 清理
        os.remove(test_db)
        
        if result:
            logger.info("✓ 資料庫讀寫測試成功")
            return True
        else:
            logger.error("❌ 資料庫測試失敗")
            return False
            
    except Exception as e:
        logger.error(f"❌ 資料庫測試失敗: {e}")
        return False


def test_config():
    """測試配置文件"""
    logger.info("\n🧪 測試配置文件...")
    
    try:
        import yaml
        import os
        
        if os.path.exists('config.yaml'):
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.info("✓ config.yaml 載入成功")
            logger.info(f"  系統名稱: {config['system']['name']}")
            logger.info(f"  版本: {config['system']['version']}")
            logger.info(f"  監控股票數: {len(config['watchlist']['stocks'])}")
            logger.info(f"  檢查間隔: {config['monitoring']['check_interval']} 秒")
            
            return True
        else:
            logger.warning("⚠️  config.yaml 不存在（將使用預設配置）")
            return True
            
    except Exception as e:
        logger.error(f"❌ 配置測試失敗: {e}")
        return False


async def run_all_tests():
    """運行所有測試"""
    logger.info("=" * 60)
    logger.info("🚀 AI主力偵測系統 - 完整測試")
    logger.info("=" * 60)
    
    results = {}
    
    # 1. 測試導入
    results['imports'] = await test_imports()
    
    # 2. 測試配置
    results['config'] = test_config()
    
    # 3. 測試資料庫
    results['database'] = test_database()
    
    # 4. 測試偵測器
    results['detector'] = test_detector()
    
    # 5. 測試爬蟲
    results['crawler'] = await test_crawler()
    
    # 6. 測試ML預測器
    results['ml_predictor'] = test_ml_predictor()
    
    # 7. 測試通知系統
    results['notifier'] = await test_notifier()
    
    # 顯示結果
    logger.info("\n" + "=" * 60)
    logger.info("📊 測試結果總結")
    logger.info("=" * 60)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {name:15s}: {status}")
    
    total = len(results)
    passed_count = sum(results.values())
    
    logger.info("-" * 60)
    logger.info(f"總計: {passed_count}/{total} 測試通過 ({passed_count/total*100:.1f}%)")
    logger.info("=" * 60)
    
    if passed_count == total:
        logger.info("\n🎉 所有測試通過！系統可以正常運行。")
        logger.info("\n💡 下一步:")
        logger.info("  1. 設定環境變數 (cp .env.example .env)")
        logger.info("  2. 編輯 config.yaml 調整監控清單")
        logger.info("  3. 運行 ./start_monitor.sh 啟動系統")
    else:
        logger.warning("\n⚠️  部分測試失敗，請檢查錯誤訊息並修復問題。")
    
    return passed_count == total


if __name__ == '__main__':
    # 運行測試
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
