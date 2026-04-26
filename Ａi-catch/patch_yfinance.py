"""
YFinance 修補模組
自動處理台灣上市/上櫃股票的後綴問題

在程式啟動時導入此模組，即可全局修復 yfinance 的問題
"""

import yfinance as yf
from functools import wraps
import logging
import warnings
import sys
import io

logger = logging.getLogger(__name__)

# 全局靜默 yfinance 的警告和錯誤輸出
def silence_yfinance():
    warnings.filterwarnings('ignore', message='.*possibly delisted.*')
    warnings.filterwarnings('ignore', message='.*No data found.*')
    warnings.filterwarnings('ignore', message='.*Quote not found.*')
    
    # 強制降低 yfinance 內部的日誌級別
    logging.getLogger('yfinance').setLevel(logging.CRITICAL)
    
    # 某些版本會輸出到 stderr，我們可以嘗試重定向
    # 但為了穩定性，我們先用 filter 處理

silence_yfinance()

# ==================== 上櫃股票清單 ====================
# 這些股票需要使用 .TWO 後綴
OTC_STOCKS = {
    '3363', '3163', '5438', '6163',
    
    # 用戶「我的最愛」可能包含的上櫃股票
    '8155', '5475', '7610', '1815', '5498', '8074',
    
    # 常見上櫃科技股
    '3057', '3062', '3064', '3092', '3115', '3144',
    '3294', '3303', '3305', '3324', '3332', '3349',
    '3357', '3360', '3376', '3380', '3390', '3402',
    '3416', '3438', '3455', '3472', '3516', '3520',
    '3523', '3528', '3533', '3545', '3551', '3552',
    '3558', '3564', '3567', '3577',
    '3593', '3594', '3596', '3605', '3611', '3615',
    '3617', '3622', '3624', '3629', '3630', '3642',
    '3653', '3661', '3669', '3672', '3680', '3682',
    '3684', '3687', '3689', '3691', '3693', '3694',
    '3707', '3714', '3715', '3718',
    
    # 上櫃電子股
    '4966', '4971', '4979', '4989', '4995',
    
    # 上櫃生技股
    '4126', '4128', '4130', '4137', '4138', '4147',
    '4155', '4162', '4164', '4167', '4174', '4175',
    '4180', '4183', '4188', '4192', '4198', '4205',
    
    # 上櫃光電股
    '3088', '3114', '3535', '3537', '3543', '3559',
    '3563', '3576', '3588', '3592', '3609', '3623',
    '3625', '3632', '3651', '3674', '3708', '3720',
    
    # 上櫃半導體
    '5269', '5274', '5281', '5288', '5289', '5291',
    '5309', '5314', '5324', '5328', '5340', '5345',
    '5347', '5351', '5355', '5356', '5371', '5386',
    '5388', '5392', '5398', '5410', '5425', '5426',
    '5432', '5443', '5457', '5469', '5478', '5483',
    
    # 其他上櫃股
    '6104', '6108', '6112', '6117', '6127', '6131',
    '6133', '6140', '6143', '6146', '6154', '6158',
    '6163', '6168', '6169', '6170', '6174', '6177',
    '6201', '6207', '6214', '6221', '6223', '6227',
    '6231', '6234', '6244', '6246', '6259', '6263',
    '6266', '6269', '6275', '6278', '6284', '6287',
    '6289', '6291', '6298',
}

# 興櫃股票 (Yahoo 可能無資料)
EMERGING_STOCKS = {
    '7810',
}

# 已知的上市股票 (用於快速判斷)
TWSE_STOCKS = {
    # 台灣50成分股
    '2330', '2317', '2454', '2881', '2882', '2412', '2308', '3008',
    '2886', '2891', '2303', '1301', '1303', '2884', '2357', '2382',
    '2395', '3711', '5880', '2883', '2892', '2912', '2002', '1216',
    '2207', '2379', '2327', '3045', '2885', '6505',
    
    # 其他上市股票
    '2603', '2609', '2615', '2618', '3034', '2408', '2301', '2474',
    '8021',  # 雖然是上櫃，但 Yahoo 需用 .TW 才有資料
    '6669', '3037', '2352', '2377', '2409', '3481', '2356', '3443',
    '1802', '2313', '2331', '2337', '2344', '2449', '3264', '5521',
    '1605', '8046', '3706', '3030', '8110', '6239', '6257', '6282',
    '3703', '3711', '4906', '4915', '4927', '4934', '4942', '4968', '4977',
    '2323', '2324', '2338', '2340', '2347', '2351', '2353', '2354',
    '2355', '2360', '2362', '2363', '2365', '2368', '2369', '2371',
    '2373', '2374', '2375', '2376', '2380', '2383', '2384', '2385',
    '2387', '2388', '2390', '2392', '2393', '2399', '2401', '2402',
    '2404', '2405', '2406', '2410', '2411', '2413', '2414', '2415',
    '2417', '2419', '2420', '2421', '2423', '2424', '2425', '2426',
}


def get_stock_market_type(stock_code: str) -> str:
    """
    判斷股票市場類別
    
    Returns:
        'OTC' - 上櫃 (需要 .TWO)
        'TWSE' - 上市 (需要 .TW)
        'EMERGING' - 興櫃 (可能無資料)
    """
    clean_code = stock_code.replace('.TW', '').replace('.TWO', '')
    
    if clean_code in EMERGING_STOCKS:
        return 'EMERGING'
    elif clean_code in OTC_STOCKS:
        return 'OTC'
    elif clean_code in TWSE_STOCKS:
        return 'TWSE'
    else:
        # 預設為上市，因為上市股票數量較多
        return 'TWSE'


def fix_taiwan_symbol(ticker: str) -> str:
    """
    修正台灣股票代碼格式
    
    Args:
        ticker: 原始股票代碼 (可能是 2330, 2330.TW, 2330.TWO)
    
    Returns:
        修正後的股票代碼 (包含正確的後綴)
    """
    if not isinstance(ticker, str):
        return ticker
        
    # 提取純數字部分
    clean_code = ticker.replace('.TW', '').replace('.TWO', '').strip()
    
    # 如果不是 4-5 位數字，直接返回 (可能是指數如 ^TWII)
    if not (clean_code.isdigit() and len(clean_code) >= 4):
        return ticker
    
    # 判斷市場類型
    market_type = get_stock_market_type(clean_code)
    
    if market_type == 'OTC':
        fixed = f"{clean_code}.TWO"
    else:
        fixed = f"{clean_code}.TW"
        
    if fixed != ticker:
        logger.debug(f"修正股票代碼: {ticker} -> {fixed}")
        
    return fixed


# ==================== Patch yfinance ====================

# 保存原始的 Ticker __init__
_original_Ticker_init = yf.Ticker.__init__

@wraps(_original_Ticker_init)
def _patched_Ticker_init(self, ticker, *args, **kwargs):
    """
    修補的 Ticker 初始化方法
    自動處理台灣股票的後綴
    """
    # 如果包含台灣後綴或為 4-5 位數字，則進行修正
    if isinstance(ticker, str):
        if '.TW' in ticker or '.TWO' in ticker or (ticker.isdigit() and len(ticker) >= 4):
            ticker = fix_taiwan_symbol(ticker)
    
    return _original_Ticker_init(self, ticker, *args, **kwargs)


# 應用 patch
yf.Ticker.__init__ = _patched_Ticker_init

logger.info("✅ yfinance 已修補：自動處理台灣上市/上櫃股票後綴")


# ==================== 輔助函數 ====================

def add_otc_stock(stock_code: str):
    """動態添加上櫃股票到清單"""
    OTC_STOCKS.add(stock_code.replace('.TW', '').replace('.TWO', ''))
    logger.info(f"已添加上櫃股票: {stock_code}")


def add_twse_stock(stock_code: str):
    """動態添加上市股票到清單"""
    TWSE_STOCKS.add(stock_code.replace('.TW', '').replace('.TWO', ''))
    logger.info(f"已添加上市股票: {stock_code}")


# ==================== 測試 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("yfinance 修補測試")
    print("=" * 60)
    
    test_stocks = [
        ('3363', '上櫃'),
        ('3163', '上櫃'),
        ('5438', '上櫃'),
        ('6163', '上櫃'),
        ('3264', '上市'),
        ('2330', '上市'),
        ('2454', '上市'),
    ]
    
    for code, market in test_stocks:
        fixed = fix_taiwan_symbol(code)
        market_type = get_stock_market_type(code)
        print(f"{code} ({market}): {fixed} [判斷: {market_type}]")
    
    print("\n✅ 測試完成!")
