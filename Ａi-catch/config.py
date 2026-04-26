# config.py - 數據源設定

DATA_SOURCES = {
    'yahoo': {
        'url': 'https://tw.stock.yahoo.com/quote/{}/agent',
        'api': 'https://query1.finance.yahoo.com/v8/finance/chart/{}',
        'realtime': False
    },
    'fubon': {
        'realtime_api': '富邦開放API',
        'main_force_url': 'https://fubon-wealth.com/broker-service/market-info'
    },
    'tdcc': {
        'shareholder': 'https://www.tdcc.com.tw/portal/zh/smWeb/qryStock'
    },
    'goodinfo': {
        'institutional': 'https://goodinfo.tw/tw/StockList.asp?MARKET_CAT=全部&INDUSTRY_CAT=全部'
    }
}

# 系統配置
SYSTEM_CONFIG = {
    'check_interval': 60,  # 秒
    'trading_hours_only': True,
    'max_concurrent': 10,
    'database_path': './stock_monitor.db',
    'log_path': './logs/stock_monitor.log'
}

# 預設監控清單
DEFAULT_WATCHLIST = [
    '2330.TW',  # 台積電
    '2317.TW',  # 鴻海
    '2454.TW',  # 聯發科
    '2881.TW',  # 富邦金
    '2882.TW',  # 國泰金
    '0050.TW',  # 元大台灣50
    '00631L.TW' # 元大台灣50正2
]

# 通知設定
NOTIFICATION_CONFIG = {
    'line': {
        'enabled': True,
        'token': None  # 從環境變數讀取
    },
    'telegram': {
        'enabled': True,
        'bot_token': None,  # 從環境變數讀取
        'chat_id': None     # 從環境變數讀取
    },
    'email': {
        'enabled': True,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': None,  # 從環境變數讀取
        'password': None   # 從環境變數讀取
    }
}

# AI模型配置
AI_MODEL_CONFIG = {
    'model_path': './models/main_force_model.pkl',
    'retrain_interval': 30,  # 天
    'min_training_samples': 1000,
    'confidence_threshold': 0.7
}
