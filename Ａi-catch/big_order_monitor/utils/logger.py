"""
日誌模組
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_level=logging.INFO, log_dir: str = "logs"):
    """設定日誌系統"""
    # 建立logs目錄
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 日誌檔案名稱
    log_file = log_path / f"big_order_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 設定格式
    log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 設定root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 設定第三方套件日誌等級
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


def get_logger(name: str):
    """取得logger"""
    return logging.getLogger(name)
