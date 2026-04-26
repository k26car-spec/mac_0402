"""
系統測試程式
"""
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# 添加路徑
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

from config.trading_config import AdvancedSystemConfig, StockType
from core.detector.advanced_detector import AdvancedBigOrderDetector
from utils.logger import setup_logging


async def test_detector():
    """測試偵測器"""
    setup_logging()
    
    print("=" * 70)
    print("🧪 測試大單偵測系統 v3.0")
    print("=" * 70)
    
    # 建立配置
    config = AdvancedSystemConfig()
    config.add_stock(
        code='TEST001',
        name='測試股票',
        type=StockType.ELECTRONIC,
        market_cap=1000,
        avg_daily_volume=5000,
        volatility=0.02
    )
    
    # 建立偵測器
    detector = AdvancedBigOrderDetector(config)
    
    print("✅ 偵測器初始化完成")
    print(f"   大單門檻: {config.watchlist['TEST001'].big_order_threshold} 張")
    print("\n模擬 tick 資料...")
    
    # 模擬tick資料
    base_price = 100.0
    signals = []
    
    for i in range(200):
        # 前100筆：正常交易
        if i < 100:
            volume = np.random.randint(10, 40)
            bs_flag = 'B' if np.random.random() > 0.5 else 'S'
            price_change = 0
        # 後100筆：強勢買盤
        else:
            volume = np.random.randint(80, 150)  # 大單
            bs_flag = 'B'  # 買盤
            price_change = 0.001  # 價格上漲
        
        tick = {
            'timestamp': datetime.now(),
            'price': base_price + price_change * (i - 100) if i >= 100 else base_price,
            'volume': volume,
            'bs_flag': bs_flag,
            'ask_price': base_price + 0.5,
            'bid_price': base_price - 0.5,
            'ask_volume': 50,
            'bid_volume': 50
        }
        
        # 處理tick
        signal = await detector.process_tick_stream('TEST001', tick)
        
        if signal:
            signals.append(signal)
            print(f"\n✅ 第 {i+1} 筆 tick 偵測到訊號:")
            print(f"   方向: {signal.signal_type}")
            print(f"   價格: ${signal.price:,.2f}")
            print(f"   信心度: {signal.confidence:.1%}")
            print(f"   品質分數: {signal.quality_score:.1%} ({signal.quality_level})")
            print(f"   綜合分數: {signal.composite_score:.1%}")
            print(f"   原因: {signal.reason}")
        
        if i % 50 == 0:
            print(f"處理中... {i}/200")
    
    # 顯示結果
    print("\n" + "=" * 70)
    print("測試結果")
    print("=" * 70)
    print(f"總 tick 數: 200")
    print(f"偵測到訊號數: {len(signals)}")
    
    if signals:
        print(f"\n訊號品質分佈:")
        excellent = sum(1 for s in signals if s.quality_score >= 0.8)
        good = sum(1 for s in signals if 0.7 <= s.quality_score < 0.8)
        fair = sum(1 for s in signals if 0.6 <= s.quality_score < 0.7)
        poor = sum(1 for s in signals if s.quality_score < 0.6)
        
        print(f"  🌟 優秀(≥80%): {excellent}")
        print(f"  ✨ 良好(70-80%): {good}")
        print(f"  💫 普通(60-70%): {fair}")
        print(f"  ⚠️  不佳(<60%): {poor}")
    
    # 效能指標
    stats = detector.get_performance_metrics()
    print(f"\n偵測器統計:")
    print(f"  大單數: {stats['big_orders']}")
    print(f"  假單數: {stats['fake_orders']}")
    print(f"  有效訊號: {stats['valid_signals']}")
    print(f"  假單率: {stats['fake_order_rate']:.1%}")
    
    print("\n✅ 測試完成")
    print("=" * 70)


async def test_email():
    """測試 Email 服務"""
    from utils.email_service import EmailNotificationService
    from config.trading_config import EmailConfig
    import os
    
    print("=" * 70)
    print("🧪 測試 Email 服務")
    print("=" * 70)
    
    # 從環境變數載入配置
    config = EmailConfig(
        enabled=True,
        sender_email=os.getenv('SENDER_EMAIL', ''),
        sender_password=os.getenv('SENDER_PASSWORD', ''),
        recipient_emails=os.getenv('RECIPIENT_EMAILS', '').split(',') if os.getenv('RECIPIENT_EMAILS') else []
    )
    
    email_service = EmailNotificationService(config)
    
    if not email_service.enabled:
        print("❌ Email 服務未配置")
        print("請設定以下環境變數:")
        print("  SENDER_EMAIL=your_email@gmail.com")
        print("  SENDER_PASSWORD=your_app_password")
        print("  RECIPIENT_EMAILS=recipient@example.com")
        return
    
    print("📧 發送測試郵件...")
    success = await email_service.send_test_email()
    
    if success:
        print("✅ 測試郵件發送成功！")
    else:
        print("❌ 測試郵件發送失敗")
    
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='大單偵測系統測試')
    parser.add_argument('--email', action='store_true', help='測試 Email 服務')
    parser.add_argument('--detector', action='store_true', help='測試偵測器')
    args = parser.parse_args()
    
    if args.email:
        asyncio.run(test_email())
    elif args.detector:
        asyncio.run(test_detector())
    else:
        # 預設測試偵測器
        asyncio.run(test_detector())
