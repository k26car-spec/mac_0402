# stock_names.py - 股票中文名稱對照表

STOCK_NAMES = {
    # 台灣50成分股
    '2330.TW': '台積電',
    '2317.TW': '鴻海',
    '2454.TW': '聯發科',
    '2881.TW': '富邦金',
    '2882.TW': '國泰金',
    '2412.TW': '中華電',
    '2308.TW': '台達電',
    '3008.TW': '大立光',
    '2886.TW': '兆豐金',
    '2891.TW': '中信金',
    '2303.TW': '聯電',
    '1301.TW': '台塑',
    '1303.TW': '南亞',
    '2884.TW': '玉山金',
    '2357.TW': '華碩',
    '2382.TW': '廣達',
    '2395.TW': '研華',
    '3711.TW': '日月光投控',
    '5880.TW': '合庫金',
    '2883.TW': '開發金',
    '2892.TW': '第一金',
    '2912.TW': '統一超',
    '2002.TW': '中鋼',
    '1216.TW': '統一',
    '2207.TW': '和泰車',
    '2379.TW': '瑞昱',
    '2327.TW': '國巨',
    '3045.TW': '台灣大',
    '2885.TW': '元大金',
    '6505.TW': '台塑化',
    
    # 用戶新增的監控股票
    '1802.TW': '台玻',
    '2313.TW': '華通',
    '2331.TW': '精英',
    '2344.TW': '華邦電',
    '2449.TW': '京元電',
    '8110.TW': '華東',
    '8021.TW': '尖點',
    '3706.TW': '神達',
    '5521.TW': '工信',
    
    # 不同後綴版本
    '1802': '台玻',
    '2313': '華通',
    '2331': '精英',
    '2344': '華邦電',
    '2449': '京元電',
    '8110': '華東',
    '8021': '尖點',
    '3706': '神達',
    '5521': '工信',
    
    # ETF
    '0050.TW': '元大台灣50',
    '0056.TW': '元大高股息',
    '00631L.TW': '元大台灣50正2',
    '00632R.TW': '元大台灣50反1',
    '00878.TW': '國泰永續高股息',
    '00679B.TW': '元大美債20年',
    '006208.TW': '富邦台50',
    '00692.TW': '富邦公司治理',
    '00757.TW': '統一FANG+',
    '00881.TW': '國泰台灣5G+',
    
    # 其他熱門股票
    '2603.TW': '長榮',
    '2609.TW': '陽明',
    '2615.TW': '萬海',
    '2618.TW': '長榮航',
    '3034.TW': '聯詠',
    '2408.TW': '南亞科',
    '2301.TW': '光寶科',
    '2474.TW': '可成',
    '6669.TW': '緯穎',
    '3037.TW': '欣興',
    '2352.TW': '佳世達',
    '2377.TW': '微星',
    '2409.TW': '友達',
    '3481.TW': '群創',
    '2356.TW': '英業達',
    
    # 上櫃股票
    '8046.TW': '南電',
    '8046.TWO': '南電',
    '8155.TWO': '博智',
    '8021.TW': '尖點',
    '8021.TWO': '尖點',
    '8110.TW': '華東',
    '8110.TWO': '華東',
    '3706.TW': '神達',
    '3363.TW': '上詮',
    '5475.TW': '德宏',
    '5475.TWO': '德宏',
    '5475': '德宏',
    '6257': '矽格',
    '6257.TW': '矽格',
}

def get_stock_name(stock_code):
    """
    獲取股票中文名稱 - 自動從多個來源查詢
    
    優先順序：
    1. 從本地字典查找（快速）
    2. 從 Yahoo Finance 網頁抓取
    3. 從 TWSE API 查詢
    4. 從 yfinance 獲取
    5. 返回代碼本身（後備）
    
    Args:
        stock_code: 股票代碼 (如: 2330.TW, 8155.TWO, 5475)
    
    Returns:
        str: 中文名稱，如果找不到則返回代碼本身
    """
    # 1. 先從本地字典查找（完全匹配）
    if stock_code in STOCK_NAMES:
        return STOCK_NAMES[stock_code]
    
    # 2. 嘗試不同後綴 (.TW, .TWO, 無後綴)
    base_code = stock_code.replace('.TW', '').replace('.TWO', '')
    
    for suffix in ['', '.TW', '.TWO']:
        test_code = base_code + suffix
        if test_code in STOCK_NAMES:
            return STOCK_NAMES[test_code]
    
    # 3. 自動從 API 查詢
    name = _fetch_stock_name_from_api(base_code)
    if name:
        # 快取結果
        STOCK_NAMES[base_code] = name
        STOCK_NAMES[f"{base_code}.TW"] = name
        STOCK_NAMES[f"{base_code}.TWO"] = name
        return name
    
    # 4. 後備方案：返回代碼本身
    return base_code


def _fetch_stock_name_from_api(stock_code):
    """
    從多個 API 來源獲取股票名稱
    """
    import requests
    
    # 方法 1: 從 Yahoo 台股網頁抓取
    try:
        for suffix in ['.TW', '.TWO']:
            url = f"https://tw.stock.yahoo.com/quote/{stock_code}{suffix}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                # 從 title 解析: "德宏(5475.TWO) 走勢圖 - Yahoo奇摩股市"
                import re
                match = re.search(r'<title>([^(]+)\(', resp.text)
                if match:
                    name = match.group(1).strip()
                    if name and name != stock_code:
                        return name
    except:
        pass
    
    # 方法 2: 從 TWSE API 查詢
    try:
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo={stock_code}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get('title', '')
            # 格式: "113年12月 2330 台積電 各日成交資訊"
            import re
            match = re.search(rf'{stock_code}\s+(\S+)\s+', title)
            if match:
                return match.group(1)
    except:
        pass
    
    # 方法 3: 從 yfinance 獲取
    try:
        import yfinance as yf
        for suffix in ['.TW', '.TWO']:
            ticker = yf.Ticker(f"{stock_code}{suffix}")
            info = ticker.info
            if info:
                name = info.get('longName') or info.get('shortName') or info.get('name', '')
                if name and name != stock_code:
                    return name
    except:
        pass
    
    return None

def get_full_name(stock_code):
    """
    獲取完整的股票名稱（代碼 + 中文名）
    
    Args:
        stock_code: 股票代碼 (如: 2330.TW)
    
    Returns:
        str: 完整名稱 (如: 2330.TW 台積電)
    """
    chinese_name = get_stock_name(stock_code)
    if chinese_name == stock_code.replace('.TW', ''):
        return stock_code
    return f"{stock_code} {chinese_name}"

# 添加股票名稱到對照表
def add_stock_name(stock_code, chinese_name):
    """
    添加新的股票名稱
    
    Args:
        stock_code: 股票代碼
        chinese_name: 中文名稱
    """
    STOCK_NAMES[stock_code] = chinese_name
