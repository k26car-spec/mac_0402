"""
大單偵測監控系統 - 配置模組
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path
import yaml
from enum import Enum
from datetime import datetime


class StockType(Enum):
    """股票類型"""
    ELECTRONIC = "electronic"
    SEMICONDUCTOR = "semiconductor"
    FINANCIAL = "financial"
    SHIPPING = "shipping"
    BIOTECH = "biotech"
    STEEL = "steel"
    PLASTIC = "plastic"
    OTHER = "other"


class TradingMode(Enum):
    """交易模式（監控用）"""
    DAY_TRADING = "day_trading"
    SWING_TRADING = "swing_trading"
    POSITION_TRADING = "position_trading"


@dataclass
class StockConfig:
    """股票配置"""
    code: str
    name: str
    type: StockType
    market_cap: float = 0.0  # 市值（億）
    avg_daily_volume: float = 0.0  # 日均量（張）
    volatility: float = 0.02  # 波動率
    
    @property
    def big_order_threshold(self) -> int:
        """動態大單門檻計算"""
        base_thresholds = {
            StockType.ELECTRONIC: 50,
            StockType.SEMICONDUCTOR: 80,
            StockType.FINANCIAL: 100,
            StockType.SHIPPING: 120,
            StockType.BIOTECH: 30,
            StockType.STEEL: 60,
            StockType.PLASTIC: 40,
            StockType.OTHER: 50
        }
        
        base = base_thresholds.get(self.type, 50)
        
        # 根據市值調整
        if self.market_cap > 5000:  # 超大型股
            base *= 2.0
        elif self.market_cap > 1000:  # 大型股
            base *= 1.5
        elif self.market_cap < 100:  # 小型股
            base *= 0.5
        
        # 根據成交量調整
        if self.avg_daily_volume > 10000:
            base *= 1.8
        elif self.avg_daily_volume < 1000:
            base *= 0.7
        
        # 根據波動率調整
        if self.volatility > 0.03:
            base *= 1.2
        
        return int(max(base, 10))


@dataclass
class DetectorConfig:
    """偵測器配置"""
    # 基本參數
    base_time_window: int = 5  # 時間窗口（分鐘）
    base_min_big_orders: int = 3  # 最少大單數
    base_min_volume_ratio: float = 0.40  # 大單佔比門檻
    
    # 方向檢查
    min_direction_ratio: float = 0.70  # 方向一致性要求
    
    # 品質控制
    min_signal_quality: float = 0.60  # 最低品質分數
    min_composite_score: float = 0.65  # 最低綜合分數
    
    # 假單偵測
    enable_fake_order_detection: bool = True
    max_same_price_orders: int = 5  # 同價位最大大單數
    
    # AI模型
    use_ai_model: bool = False  # 預設關閉


@dataclass
class EmailConfig:
    """Email 通知配置"""
    enabled: bool = True
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    recipient_emails: List[str] = field(default_factory=list)
    
    # 通知條件
    min_quality_for_email: float = 0.70  # 品質達到 70% 才發送


@dataclass
class AdvancedSystemConfig:
    """進階系統配置"""
    # 基本設定
    system_name: str = "大單偵測監控系統"
    version: str = "3.0"
    
    # 監控設定
    watchlist: Dict[str, StockConfig] = field(default_factory=dict)
    detector_config: DetectorConfig = field(default_factory=DetectorConfig)
    email_config: EmailConfig = field(default_factory=EmailConfig)
    
    # 通知設定
    enable_notifications: bool = True
    notification_methods: Dict[str, bool] = field(default_factory=lambda: {
        'console': True,
        'file': True,
        'email': True,
        'line': False,
        'telegram': False
    })
    
    # 檔案路徑
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    report_dir: Path = field(default_factory=lambda: Path("reports"))
    
    def __post_init__(self):
        """初始化後處理"""
        self.log_dir.mkdir(exist_ok=True)
        self.report_dir.mkdir(exist_ok=True)
    
    def add_stock(self, code: str, name: str, type: StockType,
                  market_cap: float = 0, avg_daily_volume: float = 0,
                  volatility: float = 0.02):
        """新增監控股票"""
        self.watchlist[code] = StockConfig(
            code=code,
            name=name,
            type=type,
            market_cap=market_cap,
            avg_daily_volume=avg_daily_volume,
            volatility=volatility
        )
        return self.watchlist[code]
    
    def remove_stock(self, code: str):
        """移除股票"""
        if code in self.watchlist:
            del self.watchlist[code]
    
    def save(self, filepath: Path):
        """儲存設定"""
        data = {
            'system_name': self.system_name,
            'version': self.version,
            'watchlist': {
                code: {
                    'name': stock.name,
                    'type': stock.type.value,
                    'market_cap': stock.market_cap,
                    'avg_daily_volume': stock.avg_daily_volume,
                    'volatility': stock.volatility
                }
                for code, stock in self.watchlist.items()
            },
            'detector_config': {
                'base_time_window': self.detector_config.base_time_window,
                'base_min_big_orders': self.detector_config.base_min_big_orders,
                'base_min_volume_ratio': self.detector_config.base_min_volume_ratio,
                'min_direction_ratio': self.detector_config.min_direction_ratio,
                'min_signal_quality': self.detector_config.min_signal_quality
            },
            'email_config': {
                'enabled': self.email_config.enabled,
                'smtp_server': self.email_config.smtp_server,
                'smtp_port': self.email_config.smtp_port,
                'sender_email': self.email_config.sender_email,
                'recipient_emails': self.email_config.recipient_emails,
                'min_quality_for_email': self.email_config.min_quality_for_email
            },
            'notification_methods': self.notification_methods
        }
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    @classmethod
    def load(cls, filepath: Path):
        """載入設定"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        config = cls()
        config.system_name = data.get('system_name', '大單偵測監控系統')
        config.version = data.get('version', '3.0')
        
        # 載入股票
        for code, stock_data in data.get('watchlist', {}).items():
            config.add_stock(
                code=code,
                name=stock_data['name'],
                type=StockType(stock_data['type']),
                market_cap=stock_data.get('market_cap', 0),
                avg_daily_volume=stock_data.get('avg_daily_volume', 0),
                volatility=stock_data.get('volatility', 0.02)
            )
        
        # 載入偵測器設定
        if 'detector_config' in data:
            dc = data['detector_config']
            config.detector_config.base_time_window = dc.get('base_time_window', 5)
            config.detector_config.base_min_big_orders = dc.get('base_min_big_orders', 3)
            config.detector_config.base_min_volume_ratio = dc.get('base_min_volume_ratio', 0.40)
            config.detector_config.min_direction_ratio = dc.get('min_direction_ratio', 0.70)
            config.detector_config.min_signal_quality = dc.get('min_signal_quality', 0.60)
        
        # 載入 Email 設定
        if 'email_config' in data:
            ec = data['email_config']
            config.email_config.enabled = ec.get('enabled', True)
            config.email_config.smtp_server = ec.get('smtp_server', 'smtp.gmail.com')
            config.email_config.smtp_port = ec.get('smtp_port', 587)
            config.email_config.sender_email = ec.get('sender_email', '')
            config.email_config.recipient_emails = ec.get('recipient_emails', [])
            config.email_config.min_quality_for_email = ec.get('min_quality_for_email', 0.70)
        
        # 載入通知設定
        if 'notification_methods' in data:
            config.notification_methods = data['notification_methods']
        
        return config
    
    def display_config(self):
        """顯示配置摘要"""
        print("\n" + "=" * 70)
        print(f"📋 系統配置: {self.system_name} v{self.version}")
        print("=" * 70)
        print(f"監控股票數: {len(self.watchlist)}")
        print(f"時間窗口: {self.detector_config.base_time_window} 分鐘")
        print(f"最少大單數: {self.detector_config.base_min_big_orders} 筆")
        print(f"大單佔比門檻: {self.detector_config.base_min_volume_ratio:.0%}")
        print(f"方向一致性要求: {self.detector_config.min_direction_ratio:.0%}")
        print(f"最低品質分數: {self.detector_config.min_signal_quality:.0%}")
        print(f"假單偵測: {'啟用' if self.detector_config.enable_fake_order_detection else '停用'}")
        print(f"Email 通知: {'啟用' if self.email_config.enabled else '停用'}")
        print("=" * 70)
