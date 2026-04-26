"""
大單監控配置 - 動態閾值計算 v2.0
根據股價自動計算大單門檻，以金額影響力為基準

核心邏輯:
- 大單定義 = 單筆交易金額達到「影響股價」的程度
- 以「單筆金額 500-1000 萬」作為大單基準
- 系統根據當前股價，反推需要多少張才達到此金額

計算公式:
  大單張數 = 目標金額 / (股價 × 1000股)
  
舉例:
  - 台積電 $1000 元: 500萬 / (1000 × 1000) = 5 張
  - 鴻海 $200 元: 500萬 / (200 × 1000) = 25 張
  - 金融股 $30 元: 500萬 / (30 × 1000) = 167 張
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import math


@dataclass
class BigOrderThresholdConfig:
    """大單閾值配置"""
    single_order: int          # 單筆大單閾值 (張)
    minute_accumulate: int     # 1分鐘累積閾值 (張)
    quality_threshold: float   # 通知品質門檻
    target_amount: float       # 目標金額 (萬元)
    actual_amount: float       # 實際金額 (萬元)


# ==================== 核心配置 ====================

# 大單基準金額 (萬元)
# 這個數字代表「有能力影響股價的單筆交易金額」
BIG_ORDER_TARGET_AMOUNT = 500  # 500 萬

# 最小/最大張數限制
MIN_THRESHOLD = 5     # 最少 5 張才算大單
MAX_THRESHOLD = 200   # 最多不超過 200 張

# 累積倍數 (1分鐘累積通常是單筆的 2 倍)
ACCUMULATE_MULTIPLIER = 2


def calculate_dynamic_threshold(price: float) -> BigOrderThresholdConfig:
    """
    根據股價動態計算大單閾值
    
    核心邏輯:
    1. 設定目標金額 (500萬)
    2. 根據股價反推需要多少張
    3. 限制在合理範圍內
    
    Args:
        price: 當前股價 (元)
    
    Returns:
        BigOrderThresholdConfig: 閾值配置
    """
    if price <= 0:
        # 無法取得股價時的預設值
        return BigOrderThresholdConfig(
            single_order=50,
            minute_accumulate=100,
            quality_threshold=0.7,
            target_amount=BIG_ORDER_TARGET_AMOUNT,
            actual_amount=0
        )
    
    # 計算達到目標金額所需的張數
    # 公式: 張數 = 目標金額(萬) × 10000 / (股價 × 1000)
    # 簡化: 張數 = 目標金額(萬) × 10 / 股價
    raw_threshold = (BIG_ORDER_TARGET_AMOUNT * 10) / price
    
    # 限制在合理範圍內
    single_order = max(MIN_THRESHOLD, min(MAX_THRESHOLD, int(math.ceil(raw_threshold))))
    
    # 1分鐘累積門檻
    minute_accumulate = single_order * ACCUMULATE_MULTIPLIER
    
    # 實際對應金額 (萬元)
    actual_amount = (price * single_order * 1000) / 10000
    
    # 品質門檻根據股價調整
    # 高價股因為流動性較低，門檻可以稍低
    if price >= 500:
        quality_threshold = 0.80
    elif price >= 200:
        quality_threshold = 0.75
    elif price >= 50:
        quality_threshold = 0.70
    else:
        quality_threshold = 0.65
    
    return BigOrderThresholdConfig(
        single_order=single_order,
        minute_accumulate=minute_accumulate,
        quality_threshold=quality_threshold,
        target_amount=BIG_ORDER_TARGET_AMOUNT,
        actual_amount=round(actual_amount, 1)
    )


def calculate_threshold_with_custom_amount(price: float, target_amount: float = 500) -> BigOrderThresholdConfig:
    """
    使用自訂金額計算大單門檻
    
    Args:
        price: 股價
        target_amount: 目標金額 (萬元)
    
    Returns:
        BigOrderThresholdConfig
    """
    if price <= 0:
        return BigOrderThresholdConfig(
            single_order=50,
            minute_accumulate=100,
            quality_threshold=0.7,
            target_amount=target_amount,
            actual_amount=0
        )
    
    raw_threshold = (target_amount * 10) / price
    single_order = max(MIN_THRESHOLD, min(MAX_THRESHOLD, int(math.ceil(raw_threshold))))
    minute_accumulate = single_order * ACCUMULATE_MULTIPLIER
    actual_amount = (price * single_order * 1000) / 10000
    
    if price >= 500:
        quality_threshold = 0.80
    elif price >= 200:
        quality_threshold = 0.75
    elif price >= 50:
        quality_threshold = 0.70
    else:
        quality_threshold = 0.65
    
    return BigOrderThresholdConfig(
        single_order=single_order,
        minute_accumulate=minute_accumulate,
        quality_threshold=quality_threshold,
        target_amount=target_amount,
        actual_amount=round(actual_amount, 1)
    )


def get_threshold_description(price: float) -> str:
    """取得閾值說明文字"""
    config = calculate_dynamic_threshold(price)
    
    if price < 30:
        category = "銅板股"
    elif price < 50:
        category = "低價股"
    elif price < 100:
        category = "中低價股"
    elif price < 200:
        category = "中價股"
    elif price < 500:
        category = "中高價股"
    elif price < 1000:
        category = "高價股"
    else:
        category = "超高價股"
    
    return (
        f"{category} (${price:.0f}): "
        f"單筆 {config.single_order} 張 = ${config.actual_amount:.0f}萬, "
        f"1分鐘累積 {config.minute_accumulate} 張"
    )


def get_threshold_breakdown(price: float) -> Dict:
    """取得完整的門檻分析"""
    config = calculate_dynamic_threshold(price)
    
    return {
        "price": price,
        "single_order_threshold": config.single_order,
        "minute_accumulate_threshold": config.minute_accumulate,
        "target_amount": f"${config.target_amount}萬",
        "actual_amount": f"${config.actual_amount}萬",
        "quality_threshold": f"{config.quality_threshold:.0%}",
        "formula": f"{config.single_order}張 × ${price} × 1000股 = ${config.actual_amount:.0f}萬"
    }


# ==================== 通知配置 ====================

class NotificationConfig:
    """通知配置"""
    
    # 冷卻時間 (同一股票多久才能再次通知)
    COOLDOWN_SECONDS = 300  # 5 分鐘
    
    # 累積通知
    ACCUMULATE_WINDOW_SECONDS = 60  # 1 分鐘內
    ACCUMULATE_COUNT_TRIGGER = 3   # 同向訊號達到3次
    
    # 高品質訊號直接通知的門檻
    HIGH_QUALITY_THRESHOLD = 0.85
    
    # 一般品質訊號的門檻
    NORMAL_QUALITY_THRESHOLD = 0.70
    
    # Email 通知
    EMAIL_ENABLED = True
    EMAIL_BATCH_INTERVAL = 0  # 0 = 即時發送, >0 = 批次發送間隔(秒)
    
    # 瀏覽器推播
    BROWSER_PUSH_ENABLED = True


# ==================== 股票名稱對照 ====================

STOCK_NAMES: Dict[str, str] = {
    # 金融股 (多為銅板股)
    "2880": "華南金", "2881": "富邦金", "2882": "國泰金",
    "2883": "開發金", "2884": "玉山金", "2885": "元大金",
    "2886": "兆豐金", "2887": "台新金", "2888": "新光金",
    "2889": "國票金", "2890": "永豐金", "2891": "中信金",
    "2892": "第一金", "5880": "合庫金",
    
    # 航運股 (中低價)
    "2603": "長榮", "2609": "陽明", "2615": "萬海",
    "2618": "長榮航", "2610": "華航", "2637": "台驊",
    
    # 電子股 (價格不一)
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科",
    "2308": "台達電", "2382": "廣達", "2376": "技嘉",
    "2377": "微星", "2357": "華碩", "2353": "宏碁",
    "3231": "緯創", "4938": "和碩", "2324": "仁寶",
    "2356": "英業達", "2312": "金寶",
    
    # IC 設計 (中高價)
    "3443": "創意", "3034": "聯詠", "2379": "瑞昱",
    "3661": "世芯", "5269": "祥碩", "5274": "信驊",
    "6415": "矽力", "2344": "華邦電",
    
    # 用戶關注 (包含上櫃股票)
    "5521": "工信", "8110": "華東", "8021": "尖點", 
    "3706": "神達", "5498": "凱崴", "3030": "德律",
    "3037": "欣興", "1815": "富喬", "8039": "台虹",
    "3363": "上詮", "8155": "博智", "6257": "矽格",  # 上櫃股票
    
    # 傳產
    "1101": "台泥", "1102": "亞泥", "1301": "台塑",
    "1303": "南亞", "1326": "台化", "1216": "統一",
    "2912": "統一超", "1721": "三晃",
}


def get_stock_name(code: str) -> str:
    """
    取得股票名稱
    
    查詢優先順序:
    1. 本地 STOCK_NAMES 字典 (快速)
    2. Fubon/Yahoo API (動態獲取)
    3. 返回代碼本身 (後備)
    """
    clean_code = code.replace('.TW', '').replace('.TWO', '')
    
    # 1. 先從本地字典查找
    if clean_code in STOCK_NAMES:
        return STOCK_NAMES[clean_code]
    
    # 2. 嘗試從外部 API 獲取
    try:
        # 嘗試使用 fubon_stock_info
        import sys
        import os
        
        # 添加根目錄到路徑
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        
        from fubon_stock_info import get_stock_name_from_fubon
        name = get_stock_name_from_fubon(clean_code)
        
        if name and name != clean_code:
            # 自動加入快取
            STOCK_NAMES[clean_code] = name
            return name
            
    except ImportError:
        pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"API 獲取股票名稱失敗 {clean_code}: {e}")
    
    # 3. 嘗試 yfinance 備用方案
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{clean_code}.TW")
        info = ticker.info
        if info:
            name = info.get('shortName') or info.get('longName')
            if name and name != clean_code:
                # 清理名稱
                name = name.split(' Ordinary')[0].split(' ADR')[0].strip()
                STOCK_NAMES[clean_code] = name
                return name
    except Exception:
        pass
    
    # 4. 後備: 返回代碼本身
    return clean_code


# ==================== 通知格式 ====================

def format_notification_message(
    stock_code: str,
    stock_name: str,
    signal_type: str,
    price: float,
    threshold_config: BigOrderThresholdConfig,
    trigger_reason: str,
    quality_score: float
) -> Dict:
    """格式化通知訊息"""
    
    emoji = "🔴" if signal_type == "BUY" else "🟢"
    action = "買進" if signal_type == "BUY" else "賣出"
    
    return {
        "title": f"{emoji} 大單{action}訊號 - {stock_code} {stock_name}",
        "body": f"""
股票: {stock_code} {stock_name}
訊號: {action}
價格: ${price:.2f}
品質: {quality_score:.0%}
觸發: {trigger_reason}
時間: {datetime.now().strftime('%H:%M:%S')}

大單標準: 單筆 ≥{threshold_config.single_order}張 (≥${threshold_config.actual_amount:.0f}萬)
""".strip(),
        "stock_code": stock_code,
        "stock_name": stock_name,
        "signal_type": signal_type,
        "price": price,
        "quality_score": quality_score,
        "trigger_reason": trigger_reason,
        "threshold_lots": threshold_config.single_order,
        "threshold_amount": threshold_config.actual_amount,
        "timestamp": datetime.now().isoformat()
    }


# ==================== 測試 ====================

if __name__ == "__main__":
    # 測試不同股價的閾值
    test_prices = [15, 25, 45, 75, 120, 200, 350, 600, 1000, 1500, 2500]
    
    print("=" * 70)
    print("大單動態閾值計算系統 v2.0")
    print("=" * 70)
    print(f"\n目標基準: 單筆交易金額達 ${BIG_ORDER_TARGET_AMOUNT} 萬\n")
    print("-" * 70)
    print(f"{'股價':>8} | {'張數門檻':>8} | {'實際金額':>10} | {'累積門檻':>8} | {'品質門檻':>8}")
    print("-" * 70)
    
    for price in test_prices:
        config = calculate_dynamic_threshold(price)
        print(f"${price:>7.0f} | {config.single_order:>7} 張 | ${config.actual_amount:>8.0f}萬 | {config.minute_accumulate:>7} 張 | {config.quality_threshold:>7.0%}")
    
    print("-" * 70)
    
    print("\n" + "=" * 70)
    print("計算公式說明:")
    print("=" * 70)
    print(f"""
核心邏輯:
  大單 = 單筆交易金額達到「能影響股價」的程度
  
公式:
  張數門檻 = 目標金額(萬) × 10 / 股價
  
範例:
  - 台積電 $1000: {BIG_ORDER_TARGET_AMOUNT}萬 × 10 / 1000 = 5 張
  - 鴻海 $200: {BIG_ORDER_TARGET_AMOUNT}萬 × 10 / 200 = 25 張
  - 金融股 $30: {BIG_ORDER_TARGET_AMOUNT}萬 × 10 / 30 = 167 張 → 最大 200 張
  
限制:
  - 最小: {MIN_THRESHOLD} 張 (避免過度敏感)
  - 最大: {MAX_THRESHOLD} 張 (避免門檻過高)
""")
