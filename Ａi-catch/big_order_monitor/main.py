"""
大單偵測監控系統 v3.0 - 主程式
整合富邦API即時數據與Email通知
"""
import asyncio
import os
import signal as sig
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Optional
import json

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config.trading_config import AdvancedSystemConfig, StockType, EmailConfig
from core.detector.advanced_detector import AdvancedBigOrderDetector, EnhancedSignal
from data.api.fubon_api import EnhancedFubonAPI
from utils.logger import setup_logging, get_logger
from utils.email_service import EmailNotificationService

logger = get_logger(__name__)


class BigOrderMonitoringSystem:
    """大單偵測監控系統 v3.0"""
    
    def __init__(self, config_path: Path = None):
        """初始化"""
        print("""
╔══════════════════════════════════════════════════════════════════╗
║      🔍 大單偵測監控系統 v3.0                                      ║
║      📊 即時監控 • 訊號分析 • 品質評估 • Email通知                  ║
║      ⚠️  本系統僅監控訊號，不執行任何交易                           ║
╚══════════════════════════════════════════════════════════════════╝
        """)
        
        setup_logging(log_dir=str(Path(__file__).parent / "logs"))
        
        # 載入配置
        self.config = self._load_config(config_path)
        self.config.display_config()
        
        # 初始化元件
        self.detector = AdvancedBigOrderDetector(self.config)
        self.broker_api: Optional[EnhancedFubonAPI] = None
        self.email_service: Optional[EmailNotificationService] = None
        self.is_running = False
        
        # 統計資料
        self.stats = {
            'start_time': datetime.now(),
            'total_ticks_processed': 0,
            'total_signals_detected': 0,
            'emails_sent': 0,
        }
        
        # 初始化 Email 服務
        self._init_email_service()
        
        logger.info("✅ 監控系統初始化完成")
    
    def _init_email_service(self):
        """初始化 Email 服務"""
        try:
            self.email_service = EmailNotificationService(self.config.email_config)
            if self.email_service.enabled:
                logger.info("✅ Email 通知服務已啟用")
            else:
                logger.warning("⚠️ Email 通知服務未配置")
        except Exception as e:
            logger.error(f"初始化 Email 服務失敗: {e}")
            self.email_service = None
    
    def _load_config(self, config_path: Path) -> AdvancedSystemConfig:
        """載入設定"""
        if config_path and config_path.exists():
            try:
                config = AdvancedSystemConfig.load(config_path)
                logger.info(f"從 {config_path} 載入設定")
                return config
            except Exception as e:
                logger.error(f"載入設定失敗: {e}")
        
        # 預設設定
        logger.info("使用預設設定")
        config = AdvancedSystemConfig()
        
        # 設定 Email（從環境變數）
        config.email_config = EmailConfig(
            enabled=True,
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            sender_email=os.getenv('SENDER_EMAIL', ''),
            sender_password=os.getenv('SENDER_PASSWORD', ''),
            recipient_emails=os.getenv('RECIPIENT_EMAILS', '').split(',') if os.getenv('RECIPIENT_EMAILS') else [],
            min_quality_for_email=0.70
        )
        
        # 預設監控股票
        default_stocks = [
            ('2330', '台積電', StockType.SEMICONDUCTOR, 15000000, 25000, 0.02),
            ('2454', '聯發科', StockType.SEMICONDUCTOR, 500000, 8000, 0.025),
            ('2317', '鴻海', StockType.ELECTRONIC, 1500000, 15000, 0.018),
            ('2881', '富邦金', StockType.FINANCIAL, 500000, 12000, 0.015),
            ('2882', '國泰金', StockType.FINANCIAL, 450000, 10000, 0.016),
            ('2308', '台達電', StockType.ELECTRONIC, 200000, 8000, 0.02),
            ('2382', '廣達', StockType.ELECTRONIC, 150000, 6000, 0.022),
            ('3443', '創意', StockType.SEMICONDUCTOR, 20000, 3000, 0.03),
        ]
        
        for code, name, stype, mcap, vol, vola in default_stocks:
            config.add_stock(code, name, stype, mcap, vol, vola)
        
        return config
    
    async def connect_data_source(self) -> bool:
        """連接資料源"""
        try:
            logger.info("🔗 正在連接資料源...")
            
            self.broker_api = EnhancedFubonAPI()
            connected = await self.broker_api.connect()
            
            if connected:
                logger.info("✅ 資料源連接成功")
                return True
            else:
                logger.error("❌ 資料源連接失敗")
                return False
                
        except Exception as e:
            logger.error(f"連接失敗: {e}")
            return False
    
    async def start_monitoring(self):
        """開始監控"""
        if not self.broker_api:
            logger.error("❌ 請先連接資料源")
            return
        
        if self.is_running:
            logger.warning("⚠️ 系統已在執行中")
            return
        
        self.is_running = True
        
        print("\n" + "=" * 70)
        print("🚀 開始即時監控大單訊號...")
        print(f"📋 監控股票數: {len(self.config.watchlist)}")
        print("📊 監控模式: 純訊號偵測（不執行交易）")
        print(f"📧 Email通知: {'啟用' if self.email_service and self.email_service.enabled else '停用'}")
        print("=" * 70)
        
        # 顯示監控清單
        print("\n監控股票清單:")
        for code, stock in self.config.watchlist.items():
            print(f"  • {code} {stock.name:8s} | "
                  f"門檻:{stock.big_order_threshold:3d}張 | "
                  f"產業:{stock.type.value}")
        print()
        
        try:
            # 訂閱所有股票
            for stock_code in self.config.watchlist:
                await self.broker_api.subscribe_realtime(stock_code)
            
            # 主監控循環
            await self._monitoring_loop()
            
        except asyncio.CancelledError:
            logger.info("監控被取消")
        except Exception as e:
            logger.error(f"監控錯誤: {e}")
        finally:
            await self.stop()
    
    async def _monitoring_loop(self):
        """主監控循環"""
        logger.info("進入監控循環...")
        last_stat_update = datetime.now()
        
        while self.is_running:
            try:
                # 檢查交易時間（可選）
                # if not self._is_trading_time():
                #     await asyncio.sleep(60)
                #     continue
                
                # 處理所有股票
                for stock_code in self.config.watchlist:
                    tick = await self.broker_api.get_latest_tick(stock_code)
                    if tick:
                        self.stats['total_ticks_processed'] += 1
                        
                        # 偵測訊號
                        signal = await self.detector.process_tick_stream(stock_code, tick)
                        
                        if signal:
                            await self._handle_signal(signal)
                
                # 定期更新統計（每5分鐘）
                if (datetime.now() - last_stat_update).seconds >= 300:
                    await self._print_statistics()
                    last_stat_update = datetime.now()
                
                # 控制頻率
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                await asyncio.sleep(1)
    
    async def _handle_signal(self, signal: EnhancedSignal):
        """處理訊號"""
        try:
            # 更新統計
            self.stats['total_signals_detected'] += 1
            
            # 顯示訊號
            self._display_signal(signal)
            
            # 記錄到檔案
            self._log_signal(signal)
            
            # 發送 Email 通知
            if self.email_service and self.email_service.enabled:
                if signal.quality_score >= self.config.email_config.min_quality_for_email:
                    success = await self.email_service.send_signal_notification(signal)
                    if success:
                        self.stats['emails_sent'] += 1
            
        except Exception as e:
            logger.error(f"處理訊號錯誤: {e}")
    
    def _display_signal(self, signal: EnhancedSignal):
        """顯示訊號"""
        # 根據品質選擇顯示樣式
        if signal.quality_score >= 0.8:
            emoji = "🌟"
            quality_text = "優秀"
        elif signal.quality_score >= 0.7:
            emoji = "✨"
            quality_text = "良好"
        elif signal.quality_score >= 0.6:
            emoji = "💫"
            quality_text = "普通"
        else:
            emoji = "⚠️"
            quality_text = "不佳"
        
        action = "買進" if signal.signal_type == "BUY" else "賣出"
        color = "\033[92m" if signal.signal_type == "BUY" else "\033[91m"
        reset = "\033[0m"
        
        print("\n" + "=" * 70)
        print(f"{emoji} {color}【{action}訊號】{reset} {signal.stock_code} {signal.stock_name}")
        print("=" * 70)
        print(f"   價格: ${signal.price:,.2f}")
        print(f"   ─────────────────────────────────────")
        print(f"   綜合評分: {signal.composite_score:.1%}")
        print(f"   信心度: {signal.confidence:.1%}")
        print(f"   品質分數: {signal.quality_score:.1%} ({quality_text})")
        print(f"   動能分數: {signal.momentum_score:.1%}")
        print(f"   成交量分數: {signal.volume_score:.1%}")
        print(f"   型態分數: {signal.pattern_score:.1%}")
        print(f"   ─────────────────────────────────────")
        print(f"   觸發原因: {signal.reason}")
        
        if signal.warnings:
            print(f"   ⚠️ 警告: {', '.join(signal.warnings)}")
        
        print(f"   ─────────────────────────────────────")
        print(f"   參考停損: ${signal.stop_loss:,.2f}")
        print(f"   參考停利: ${signal.take_profit:,.2f}")
        print(f"   時間: {signal.timestamp.strftime('%H:%M:%S')}")
        print("=" * 70)
    
    def _log_signal(self, signal: EnhancedSignal):
        """記錄訊號到檔案"""
        try:
            import pandas as pd
            
            today = datetime.now().strftime('%Y%m%d')
            log_dir = Path(__file__).parent / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"signals_{today}.csv"
            
            df = pd.DataFrame([signal.to_dict()])
            
            if log_file.exists():
                df.to_csv(log_file, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                df.to_csv(log_file, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            logger.error(f"記錄訊號失敗: {e}")
    
    async def _print_statistics(self):
        """顯示統計"""
        runtime = datetime.now() - self.stats['start_time']
        runtime_minutes = runtime.total_seconds() / 60
        
        detector_stats = self.detector.get_performance_metrics()
        
        print("\n" + "📊" * 35)
        print("系統統計")
        print("=" * 70)
        print(f"運行時間: {runtime_minutes:.1f} 分鐘")
        print(f"處理tick數: {self.stats['total_ticks_processed']:,}")
        print(f"偵測訊號數: {self.stats['total_signals_detected']}")
        print(f"發送Email數: {self.stats['emails_sent']}")
        print(f"\n偵測器效能:")
        print(f"  大單數: {detector_stats['big_orders']}")
        print(f"  假單數: {detector_stats['fake_orders']}")
        print(f"  有效訊號: {detector_stats['valid_signals']}")
        print(f"  平均品質: {detector_stats['avg_quality_score']:.1%}")
        print("📊" * 35)
    
    def _is_trading_time(self) -> bool:
        """檢查交易時間"""
        now = datetime.now().time()
        trading_start = time(9, 0)
        trading_end = time(13, 30)
        
        # 週一到週五
        weekday = datetime.now().weekday()
        if weekday >= 5:  # 週末
            return False
        
        return trading_start <= now <= trading_end
    
    async def stop(self):
        """停止系統"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        print("\n" + "=" * 70)
        print("🛑 正在停止系統...")
        print("=" * 70)
        
        # 取消訂閱
        if self.broker_api:
            await self.broker_api.unsubscribe_all()
        
        # 匯出訊號
        report_dir = Path(__file__).parent / "reports"
        report_dir.mkdir(exist_ok=True)
        filepath = str(report_dir / f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        self.detector.export_signals(filepath)
        
        # 發送日報
        if self.email_service and self.email_service.enabled:
            await self.email_service.send_daily_report(
                self.detector.get_performance_metrics(),
                self.detector.signal_history
            )
        
        # 產生日報
        await self._generate_daily_report()
        
        # 最後統計
        await self._print_statistics()
        
        logger.info("✅ 系統已停止")
    
    async def _generate_daily_report(self):
        """產生日報"""
        try:
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'runtime_minutes': (datetime.now() - self.stats['start_time']).total_seconds() / 60,
                'statistics': self.stats,
                'detector_performance': self.detector.get_performance_metrics()
            }
            
            report_dir = Path(__file__).parent / "reports"
            report_dir.mkdir(exist_ok=True)
            
            report_file = report_dir / f"daily_{datetime.now().strftime('%Y%m%d')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"✅ 日報已儲存至: {report_file}")
            
        except Exception as e:
            logger.error(f"產生日報錯誤: {e}")
    
    async def test_email(self):
        """測試 Email 服務"""
        if self.email_service:
            return await self.email_service.send_test_email()
        return False


async def main():
    """主程式"""
    # 建立系統
    config_path = Path(__file__).parent / "config" / "monitoring_config.yaml"
    system = BigOrderMonitoringSystem(config_path if config_path.exists() else None)
    
    # 設定訊號處理
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("收到關閉訊號...")
        asyncio.create_task(system.stop())
    
    for s in [sig.SIGINT, sig.SIGTERM]:
        loop.add_signal_handler(s, signal_handler)
    
    try:
        # 連接資料源
        connected = await system.connect_data_source()
        if not connected:
            logger.error("無法連接資料源")
            return
        
        # 開始監控
        await system.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("使用者中斷")
        await system.stop()
    except Exception as e:
        logger.error(f"系統錯誤: {e}", exc_info=True)
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
