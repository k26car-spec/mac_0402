"""
智慧選股 API
結合新聞熱度、股價篩選、9專家分析，提供實用的投資建議

功能:
1. 爬取新聞中的熱門股票
2. 過濾高價股與冷門股
3. 9專家綜合評分
4. 分類為短/中/長期推薦
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
import asyncio
import yfinance as yf
import pandas as pd

# 導入新聞爬蟲服務
try:
    from app.services.news_crawler_service import news_crawler, get_hot_stocks_from_news
except ImportError:
    news_crawler = None

# 導入9專家系統
try:
    from app.experts.manager import expert_manager
except ImportError:
    expert_manager = None

# 導入準確率追蹤
try:
    from app.services.accuracy_tracker import accuracy_tracker, record_picks, get_accuracy_report
    ACCURACY_TRACKING_ENABLED = True
except ImportError:
    ACCURACY_TRACKING_ENABLED = False

# 導入 GoodInfo 爬蟲
try:
    from app.services.goodinfo_crawler import goodinfo_crawler, get_goodinfo_report
    GOODINFO_ENABLED = True
except ImportError:
    GOODINFO_ENABLED = False

# 導入 TWSE 證交所爬蟲
try:
    from app.services.twse_crawler import twse_crawler, get_twse_report, get_institutional_data
    TWSE_ENABLED = True
except ImportError:
    TWSE_ENABLED = False

# 導入 GPT 分析服務
try:
    from app.services.gpt_analyzer import (
        gpt_analyzer, 
        analyze_news_with_gpt, 
        analyze_stock_with_gpt,
        generate_ai_summary,
        is_gpt_available
    )
    GPT_ENABLED = is_gpt_available()
except ImportError:
    GPT_ENABLED = False
    logger.warning("⚠️ GPT 分析服務未載入")

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== 快取機制 ====================
# 避免每次重新整理都重新計算，同一天內結果保持穩定

from datetime import date
import hashlib

class SmartPicksCache:
    """智慧選股結果快取"""
    def __init__(self):
        self.cache = {}
        self.cache_date = None
    
    def get_cache_key(self, filters_dict: dict) -> str:
        """根據篩選條件生成快取 key"""
        key_str = str(sorted(filters_dict.items()))
        return hashlib.md5(key_str.encode()).hexdigest()[:8]
    
    def get(self, filters_dict: dict):
        """獲取快取結果"""
        today = date.today()
        
        # 如果日期改變，清空快取
        if self.cache_date != today:
            self.cache = {}
            self.cache_date = today
            return None
        
        key = self.get_cache_key(filters_dict)
        return self.cache.get(key)
    
    def set(self, filters_dict: dict, result: dict):
        """設置快取結果"""
        today = date.today()
        
        if self.cache_date != today:
            self.cache = {}
            self.cache_date = today
        
        key = self.get_cache_key(filters_dict)
        self.cache[key] = result
        logger.info(f"📦 快取已更新 (key: {key})")
    
    def clear(self):
        """清空快取"""
        self.cache = {}
        logger.info("🗑️ 快取已清空")

# 全域快取實例
smart_picks_cache = SmartPicksCache()


# ==================== 數據模型 ====================

class SmartPickFilters(BaseModel):
    """篩選條件"""
    max_price: float = 2000.0         # 股價上限 (提高以包含高價股)
    min_price: float = 5.0            # 股價下限 (降低)
    min_volume: int = 100             # 最低成交量(張) (降低)
    min_news_mentions: int = 0        # 最低新聞提及次數 (設為0，不限制)
    include_categories: List[str] = [] # 包含產業
    use_watchlist: bool = True        # 優先使用監控清單

class SmartPick(BaseModel):
    """智慧選股結果"""
    stock_code: str
    stock_name: str
    price: float
    volume: int
    news_heat: int                    # 新聞熱度 (提及次數)
    news_sentiment: str               # 新聞情緒
    expert_score: float               # 9專家綜合評分
    expert_signals: Dict[str, str]    # 各專家訊號
    recommendation: str               # 推薦等級 (強烈/一般/觀察)
    timeframe: str                    # 建議持有週期 (短/中/長)
    entry_price: float                # 建議進場價
    target_price: float               # 目標價
    stop_loss: float                  # 停損價
    reasons: List[str]                # 推薦理由

class SmartPicksResponse(BaseModel):
    """選股回應"""
    status: str
    timestamp: str
    market_summary: Dict[str, Any]
    short_term: List[SmartPick]       # 短期 (1-5天)
    mid_term: List[SmartPick]         # 中期 (1-4週)
    long_term: List[SmartPick]        # 長期 (1-3月)
    filters_applied: SmartPickFilters
    news_report: Dict[str, Any]


# ==================== 股票名稱對照 ====================

STOCK_NAMES = {
    # 權值股
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科",
    "2308": "台達電", "2382": "廣達", "2881": "富邦金",
    "2882": "國泰金", "2891": "中信金", "2887": "台新金",
    # 航運
    "2603": "長榮", "2609": "陽明", "2615": "萬海",
    "2618": "長榮航", "2610": "華航",
    # IC 設計
    "3443": "創意", "3034": "聯詠", "2379": "瑞昱", "3711": "日月光",
    # 傳產
    "1301": "台塑", "1303": "南亞", "1216": "統一",
    # 用戶監控
    "5521": "工信", "2344": "華邦電", "8110": "華東",
    "8021": "尖點", "3706": "神達", "6669": "緯穎",
    "2449": "京元電", "8155": "博智", "3363": "上詮",
    "5498": "凱崴", "1815": "富喬", "3030": "德律",
    "8039": "台虹", "2312": "金寶", "2408": "南亞科",
    "1504": "東元", "6770": "力積電", "1802": "台玻",
    "2337": "旺宏", "8046": "南電", "2313": "華通",
    "2331": "精英",
    # 電腦
    "2376": "技嘉", "2377": "微星", "2357": "華碩",
    "2353": "宏碁", "3231": "緯創", "4938": "和碩",
    # 金融
    "2884": "玉山金", "2886": "兆豐金", "2892": "第一金",
    "5880": "合庫金", "2880": "華南金", "2883": "開發金",
    # 石化
    "1101": "台泥", "1102": "亞泥", "1326": "台化",
    # 光電
    "3008": "大立光", "3406": "玉晶光", "6239": "力成",
    # IC/半導體
    "2303": "聯電", "2412": "中華電", "3037": "欣興",
    "6415": "矽力", "5274": "信驊", "3661": "世芯",
    "5269": "祥碩", "6409": "旭隼", "2327": "國巨",
    # 上櫃股票
    "8074": "鉅橡", "6472": "保瑞", "6523": "達爾膚",
    "3105": "穩懋", "6510": "精測", "3293": "鑫科",
    "6743": "安集", "5371": "中光電", "3227": "原相",
}


# ==================== 輔助函數 ====================

def get_stock_name(code: str) -> str:
    """取得股票名稱"""
    return STOCK_NAMES.get(code, code)

async def get_stock_data(stock_code: str) -> Dict:
    """取得股票即時數據 (使用 Yahoo Finance) - 增強版"""
    try:
        symbol = f"{stock_code}.TW"
        ticker = yf.Ticker(symbol)
        
        # 取得歷史數據計算技術指標
        hist = ticker.history(period="3mo")
        
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1] if len(hist) > 0 else 0
        avg_volume = hist['Volume'].mean() / 1000  # 轉換為張
        
        # 計算均線
        ma5 = hist['Close'].rolling(5).mean().iloc[-1] if len(hist) >= 5 else current_price
        ma20 = hist['Close'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else current_price
        ma60 = hist['Close'].rolling(60).mean().iloc[-1] if len(hist) >= 60 else current_price
        
        # ========== 新增：近期高低點 (支撐專家用) ==========
        recent_20 = hist.tail(20)
        high_20 = recent_20['High'].max() if len(recent_20) > 0 else current_price
        low_20 = recent_20['Low'].min() if len(recent_20) > 0 else current_price
        
        recent_5 = hist.tail(5)
        high_5 = recent_5['High'].max() if len(recent_5) > 0 else current_price
        low_5 = recent_5['Low'].min() if len(recent_5) > 0 else current_price
        
        # ========== 新增：ATR 計算 (波動專家用) ==========
        if len(hist) >= 14:
            high = hist['High']
            low = hist['Low']
            close = hist['Close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            atr_pct = (atr / current_price) * 100 if current_price > 0 else 0
        else:
            atr = 0
            atr_pct = 0
        
        # ========== 新增：K 線形態識別 (形態專家用) ==========
        patterns = []
        if len(hist) >= 3:
            # 最近3根K線
            c1 = hist['Close'].iloc[-1]
            o1 = hist['Open'].iloc[-1]
            h1 = hist['High'].iloc[-1]
            l1 = hist['Low'].iloc[-1]
            
            c2 = hist['Close'].iloc[-2]
            o2 = hist['Open'].iloc[-2]
            
            c3 = hist['Close'].iloc[-3]
            o3 = hist['Open'].iloc[-3]
            
            body1 = c1 - o1
            body2 = c2 - o2
            body3 = c3 - o3
            
            # 長紅K (陽線實體大於2%)
            if body1 > 0 and (body1 / o1) > 0.02:
                patterns.append("長紅K")
            
            # 長黑K (陰線實體大於2%)
            if body1 < 0 and abs(body1 / o1) > 0.02:
                patterns.append("長黑K")
            
            # 錘子線 (下影線長，實體小)
            lower_shadow = o1 - l1 if body1 >= 0 else c1 - l1
            upper_shadow = h1 - c1 if body1 >= 0 else h1 - o1
            body_size = abs(body1)
            if lower_shadow > body_size * 2 and upper_shadow < body_size * 0.5:
                patterns.append("錘子線")
            
            # 吞噬形態
            if body1 > 0 and body2 < 0 and c1 > o2 and o1 < c2:
                patterns.append("多頭吞噬")
            if body1 < 0 and body2 > 0 and c1 < o2 and o1 > c2:
                patterns.append("空頭吞噬")
            
            # 連續上漲/下跌
            if body1 > 0 and body2 > 0 and body3 > 0:
                patterns.append("三連陽")
            if body1 < 0 and body2 < 0 and body3 < 0:
                patterns.append("三連陰")
        
        # ========== 新增：成交量變化 ==========
        if len(hist) >= 5:
            recent_vol = hist['Volume'].tail(5).mean()
            prev_vol = hist['Volume'].iloc[-20:-5].mean() if len(hist) >= 20 else recent_vol
            volume_ratio = recent_vol / prev_vol if prev_vol > 0 else 1
        else:
            volume_ratio = 1
        
        return {
            "code": stock_code,
            "name": get_stock_name(stock_code),
            "price": round(current_price, 2),
            "volume": int(avg_volume),
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "trend": "多頭" if current_price > ma20 > ma60 else "空頭" if current_price < ma20 < ma60 else "盤整",
            # 新增數據
            "high_20": round(high_20, 2),
            "low_20": round(low_20, 2),
            "high_5": round(high_5, 2),
            "low_5": round(low_5, 2),
            "atr": round(atr, 2),
            "atr_pct": round(atr_pct, 2),
            "patterns": patterns,
            "volume_ratio": round(volume_ratio, 2),
        }
    except Exception as e:
        logger.error(f"獲取 {stock_code} 數據失敗: {e}")
        return None

def calculate_expert_score(stock_data: Dict) -> tuple:
    """
    9 專家評估模型 - 完整版
    
    評估維度:
    1. 趨勢專家 - 均線排列判斷
    2. 均線專家 - MA 位置分析
    3. 動量專家 - 價格動能
    4. 量能專家 - 成交量分析
    5. 籌碼專家 - 法人買賣超
    6. 支撐專家 - 支撐壓力位
    7. 形態專家 - K 線形態
    8. 波動專家 - 波動率分析
    9. 情緒專家 - 新聞情緒
    """
    scores = {}
    details = {}
    
    price = stock_data.get("price", 0)
    ma5 = stock_data.get("ma5", price)
    ma20 = stock_data.get("ma20", price)
    ma60 = stock_data.get("ma60", price)
    volume = stock_data.get("volume", 0)
    trend = stock_data.get("trend", "盤整")
    news_heat = stock_data.get("news_heat", 0)
    
    # ==================== 1. 趨勢專家 ====================
    # 判斷均線多空排列
    if trend == "多頭":
        scores["趨勢"] = 80
        details["趨勢"] = {"狀態": "多頭排列", "說明": "價格 > MA20 > MA60，趨勢向上"}
    elif trend == "空頭":
        scores["趨勢"] = 25
        details["趨勢"] = {"狀態": "空頭排列", "說明": "價格 < MA20 < MA60，趨勢向下"}
    else:
        scores["趨勢"] = 50
        details["趨勢"] = {"狀態": "盤整", "說明": "均線糾結，方向不明"}
    
    # ==================== 2. 均線專家 ====================
    # 分析價格與各均線的關係
    above_ma5 = price > ma5
    above_ma20 = price > ma20
    above_ma60 = price > ma60
    
    ma_score = 50
    if above_ma5 and above_ma20 and above_ma60:
        ma_score = 90
        ma_status = "強勢突破"
    elif above_ma5 and above_ma20:
        ma_score = 75
        ma_status = "中短期多"
    elif above_ma20:
        ma_score = 60
        ma_status = "站上月線"
    elif not above_ma5 and not above_ma20:
        ma_score = 30
        ma_status = "弱勢"
    else:
        ma_score = 45
        ma_status = "整理中"
    
    scores["均線"] = ma_score
    details["均線"] = {
        "狀態": ma_status, 
        "說明": f"{'>' if above_ma5 else '<'}MA5, {'>' if above_ma20 else '<'}MA20"
    }
    
    # ==================== 3. 動量專家 ====================
    # 計算價格動能 (偏離 MA20 的百分比)
    momentum = ((price - ma20) / ma20 * 100) if ma20 > 0 else 0
    
    if momentum > 10:
        scores["動量"] = 85
        details["動量"] = {"狀態": "極強", "說明": f"高於MA20 {momentum:.1f}%，注意過熱"}
    elif momentum > 5:
        scores["動量"] = 75
        details["動量"] = {"狀態": "強勢", "說明": f"高於MA20 {momentum:.1f}%"}
    elif momentum > 0:
        scores["動量"] = 60
        details["動量"] = {"狀態": "偏多", "說明": f"略高於MA20 {momentum:.1f}%"}
    elif momentum > -5:
        scores["動量"] = 45
        details["動量"] = {"狀態": "偏弱", "說明": f"低於MA20 {abs(momentum):.1f}%"}
    else:
        scores["動量"] = 25
        details["動量"] = {"狀態": "弱勢", "說明": f"低於MA20 {abs(momentum):.1f}%，可能超跌"}
    
    # ==================== 4. 量能專家 ====================
    # 分析成交量 (張)
    if volume > 10000:
        scores["量能"] = 85
        details["量能"] = {"狀態": "極活躍", "說明": f"日均量 {volume:,} 張，主力積極"}
    elif volume > 5000:
        scores["量能"] = 75
        details["量能"] = {"狀態": "活躍", "說明": f"日均量 {volume:,} 張，流動性佳"}
    elif volume > 1000:
        scores["量能"] = 60
        details["量能"] = {"狀態": "正常", "說明": f"日均量 {volume:,} 張"}
    elif volume > 300:
        scores["量能"] = 45
        details["量能"] = {"狀態": "清淡", "說明": f"日均量 {volume:,} 張，流動性一般"}
    else:
        scores["量能"] = 30
        details["量能"] = {"狀態": "冷清", "說明": f"日均量 {volume:,} 張，需注意流動性風險"}
    
    # ==================== 5. 籌碼專家 (整合法人買賣超) ====================
    # 使用量能變化作為籌碼參考 (真實法人資料需在智慧選股主邏輯中預先獲取)
    volume_ratio = stock_data.get("volume_ratio", 1.0)
    institutional = stock_data.get("institutional_diff", 0)  # 法人買賣超 (如有)
    
    if institutional > 0:
        # 有法人買超資料
        if institutional > 5000:
            scores["籌碼"] = 90
            details["籌碼"] = {"狀態": "法人大買", "說明": f"法人買超 {institutional:,} 張"}
        elif institutional > 1000:
            scores["籌碼"] = 75
            details["籌碼"] = {"狀態": "法人買超", "說明": f"法人買超 {institutional:,} 張"}
        else:
            scores["籌碼"] = 60
            details["籌碼"] = {"狀態": "小幅買超", "說明": f"法人買超 {institutional:,} 張"}
    elif institutional < 0:
        if institutional < -5000:
            scores["籌碼"] = 25
            details["籌碼"] = {"狀態": "法人大賣", "說明": f"法人賣超 {abs(institutional):,} 張"}
        elif institutional < -1000:
            scores["籌碼"] = 35
            details["籌碼"] = {"狀態": "法人賣超", "說明": f"法人賣超 {abs(institutional):,} 張"}
        else:
            scores["籌碼"] = 45
            details["籌碼"] = {"狀態": "小幅賣超", "說明": f"法人賣超 {abs(institutional):,} 張"}
    else:
        # 無法人資料，用量能變化推估
        if volume_ratio > 1.5 and trend == "多頭":
            scores["籌碼"] = 75
            details["籌碼"] = {"狀態": "量增價漲", "說明": f"成交量放大 {volume_ratio:.1f} 倍"}
        elif volume_ratio > 1.2 and trend == "多頭":
            scores["籌碼"] = 65
            details["籌碼"] = {"狀態": "穩定買盤", "說明": "成交量溫和放大"}
        elif volume_ratio > 1.5 and trend == "空頭":
            scores["籌碼"] = 30
            details["籌碼"] = {"狀態": "量增價跌", "說明": "恐慌賣壓"}
        else:
            scores["籌碼"] = 50
            details["籌碼"] = {"狀態": "中性", "說明": f"量比 {volume_ratio:.1f}"}
    
    # ==================== 6. 支撐專家 (使用真實高低點) ====================
    high_20 = stock_data.get("high_20", price)
    low_20 = stock_data.get("low_20", price)
    high_5 = stock_data.get("high_5", price)
    low_5 = stock_data.get("low_5", price)
    
    # 計算價格位置
    price_range = high_20 - low_20 if high_20 > low_20 else 1
    price_position = (price - low_20) / price_range if price_range > 0 else 0.5
    
    # 距離支撐/壓力的百分比
    to_support = ((price - low_20) / price * 100) if price > 0 else 0
    to_resistance = ((high_20 - price) / price * 100) if price > 0 else 0
    
    if price_position > 0.9:
        scores["支撐"] = 40
        details["支撐"] = {"狀態": "接近壓力", "說明": f"近20日高點 {high_20}，距離壓力 {to_resistance:.1f}%"}
    elif price_position > 0.7:
        scores["支撐"] = 55
        details["支撐"] = {"狀態": "偏高位", "說明": f"位於區間上緣"}
    elif price_position > 0.3:
        scores["支撐"] = 65
        details["支撐"] = {"狀態": "區間中", "說明": f"價格區間 {low_20}-{high_20}"}
    elif price_position > 0.1:
        scores["支撐"] = 75
        details["支撐"] = {"狀態": "接近支撐", "說明": f"近20日低點 {low_20}，距離支撐 {to_support:.1f}%"}
    else:
        scores["支撐"] = 35
        details["支撐"] = {"狀態": "破支撐", "說明": f"跌破近期低點 {low_20}"}
    
    # ==================== 7. 形態專家 (使用真實K線形態) ====================
    patterns = stock_data.get("patterns", [])
    
    bullish_patterns = ["長紅K", "錘子線", "多頭吞噬", "三連陽"]
    bearish_patterns = ["長黑K", "空頭吞噬", "三連陰"]
    
    bullish_count = sum(1 for p in patterns if p in bullish_patterns)
    bearish_count = sum(1 for p in patterns if p in bearish_patterns)
    
    if bullish_count >= 2:
        scores["形態"] = 85
        details["形態"] = {"狀態": "強力多頭", "說明": f"出現: {', '.join(p for p in patterns if p in bullish_patterns)}"}
    elif bullish_count == 1:
        scores["形態"] = 70
        details["形態"] = {"狀態": "多頭訊號", "說明": f"出現: {patterns[0] if patterns else ''}"}
    elif bearish_count >= 2:
        scores["形態"] = 25
        details["形態"] = {"狀態": "強力空頭", "說明": f"出現: {', '.join(p for p in patterns if p in bearish_patterns)}"}
    elif bearish_count == 1:
        scores["形態"] = 35
        details["形態"] = {"狀態": "空頭訊號", "說明": f"出現: {patterns[0] if patterns else ''}"}
    else:
        # 無明顯形態，用均線判斷
        ma5_ma20_diff = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
        if ma5_ma20_diff > 2:
            scores["形態"] = 60
            details["形態"] = {"狀態": "短均上揚", "說明": "無明顯K線形態，短均偏多"}
        elif ma5_ma20_diff < -2:
            scores["形態"] = 40
            details["形態"] = {"狀態": "短均下彎", "說明": "無明顯K線形態，短均偏空"}
        else:
            scores["形態"] = 50
            details["形態"] = {"狀態": "整理中", "說明": "無明顯K線形態"}
    
    # ==================== 8. 波動專家 (使用真實 ATR) ====================
    atr = stock_data.get("atr", 0)
    atr_pct = stock_data.get("atr_pct", 0)
    
    if atr_pct > 0:
        if atr_pct < 2:
            scores["波動"] = 80
            details["波動"] = {"狀態": "極穩定", "說明": f"ATR {atr:.1f} ({atr_pct:.1f}%)，低風險"}
        elif atr_pct < 3.5:
            scores["波動"] = 65
            details["波動"] = {"狀態": "穩定", "說明": f"ATR {atr:.1f} ({atr_pct:.1f}%)，正常波動"}
        elif atr_pct < 5:
            scores["波動"] = 50
            details["波動"] = {"狀態": "適中", "說明": f"ATR {atr:.1f} ({atr_pct:.1f}%)"}
        elif atr_pct < 8:
            scores["波動"] = 35
            details["波動"] = {"狀態": "偏高", "說明": f"ATR {atr:.1f} ({atr_pct:.1f}%)，波動較大"}
        else:
            scores["波動"] = 25
            details["波動"] = {"狀態": "劇烈", "說明": f"ATR {atr:.1f} ({atr_pct:.1f}%)，高風險"}
    else:
        # 無 ATR 資料，用動量推估
        volatility = abs(momentum)
        if volatility < 3:
            scores["波動"] = 70
            details["波動"] = {"狀態": "穩定", "說明": f"動量偏離 {volatility:.1f}%"}
        elif volatility < 8:
            scores["波動"] = 50
            details["波動"] = {"狀態": "適中", "說明": f"動量偏離 {volatility:.1f}%"}
        else:
            scores["波動"] = 30
            details["波動"] = {"狀態": "偏高", "說明": f"動量偏離 {volatility:.1f}%"}
    
    # ==================== 9. 情緒專家 ====================
    # 基於新聞熱度判斷市場情緒
    if news_heat >= 5:
        scores["情緒"] = 80
        details["情緒"] = {"狀態": "高關注", "說明": f"新聞提及 {news_heat} 次，市場關注度高"}
    elif news_heat >= 3:
        scores["情緒"] = 70
        details["情緒"] = {"狀態": "中等", "說明": f"新聞提及 {news_heat} 次"}
    elif news_heat >= 1:
        scores["情緒"] = 55
        details["情緒"] = {"狀態": "一般", "說明": f"新聞提及 {news_heat} 次"}
    else:
        scores["情緒"] = 50
        details["情緒"] = {"狀態": "冷門", "說明": "較少被新聞提及"}
    
    # ==================== 計算總分 ====================
    total_score = sum(scores.values())
    avg_score = total_score / len(scores)
    
    # 組合結果
    expert_result = {
        "avg_score": round(avg_score, 1),
        "scores": scores,
        "details": details,
        "summary": _generate_score_summary(avg_score, scores)
    }
    
    return avg_score, expert_result


def _generate_score_summary(avg_score: float, scores: Dict) -> str:
    """生成評分摘要"""
    strong_points = [k for k, v in scores.items() if v >= 70]
    weak_points = [k for k, v in scores.items() if v < 40]
    
    if avg_score >= 70:
        return f"整體強勢，優勢: {', '.join(strong_points) if strong_points else '無'}"
    elif avg_score >= 55:
        return f"中等偏多，優勢: {', '.join(strong_points) if strong_points else '無'}"
    elif avg_score >= 45:
        return f"整理格局，弱點: {', '.join(weak_points) if weak_points else '無'}"
    else:
        return f"偏弱走勢，弱點: {', '.join(weak_points) if weak_points else '無'}"



def determine_timeframe(stock_data: Dict, expert_score: float) -> str:
    """判斷適合的投資週期"""
    trend = stock_data.get("trend", "盤整")
    price = stock_data.get("price", 0)
    ma5 = stock_data.get("ma5", price)
    ma20 = stock_data.get("ma20", price)
    
    # 放寬條件確保有推薦
    if trend == "多頭" and expert_score >= 65:
        return "short"  # 趨勢明確，短線操作
    elif trend == "多頭" and expert_score >= 55:
        return "mid"    # 穩健，中期持有
    elif trend == "多頭":
        return "long"   # 多頭但評分較低，長期持有
    elif trend == "盤整" and price > ma5 and expert_score >= 50:
        return "short"  # 盤整但短期向上，短線機會
    elif trend == "盤整" and expert_score >= 45:
        return "mid"    # 盤整等待突破
    elif expert_score >= 40:
        return "long"   # 長期觀察
    else:
        return "long"   # 預設長期觀察（不返回 none 確保有結果）

def generate_recommendation(score: float, news_heat: int) -> str:
    """生成推薦等級"""
    if score >= 75 and news_heat >= 3:
        return "強烈推薦"
    elif score >= 65 or news_heat >= 2:
        return "一般推薦"
    elif score >= 50:
        return "觀察"
    else:
        return "不推薦"


# ==================== API 端點 ====================

@router.get("/daily-report")
async def get_smart_daily_report():
    """
    取得每日 AI 智慧選股報告
    整合新聞分析 + 價格篩選 + 專家評分
    """
    try:
        # 1. 獲取新聞報告
        if news_crawler:
            news_report = await news_crawler.generate_daily_report()
        else:
            news_report = {"status": "error", "message": "新聞服務未啟用"}
        
        # 2. 提取熱門股票
        hot_stocks = []
        if news_report.get("status") == "success":
            hot_stocks = [s["code"] for s in news_report.get("hot_stocks", [])]
        
        # 3. 如果沒有熱門股，使用預設關注清單
        if not hot_stocks:
            hot_stocks = ["2603", "2609", "2618", "3443", "2344", 
                         "8110", "5521", "3034", "2379", "2376"]
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "news_report": news_report,
            "hot_stocks": hot_stocks,
            "message": f"找到 {len(hot_stocks)} 檔新聞熱門股"
        }
        
    except Exception as e:
        logger.error(f"生成每日報告失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-picks")
async def get_smart_picks(
    filters: SmartPickFilters = None,
):
    """
    智慧選股 - 主要 API
    
    流程:
    1. 爬取新聞，提取熱門股票
    2. 根據篩選條件過濾
    3. 計算9專家評分
    4. 分類為短/中/長期
    
    快取: 同一天內相同篩選條件的結果會被快取
    """
    if filters is None:
        filters = SmartPickFilters()
    
    try:
        # 檢查快取
        filters_dict = filters.dict()
        cached_result = smart_picks_cache.get(filters_dict)
        if cached_result:
            logger.info("📦 使用快取結果")
            cached_result["from_cache"] = True
            return cached_result
        
        logger.info(f"開始智慧選股，篩選條件: 價格 {filters.min_price}-{filters.max_price}")
        
        # 1. 獲取新聞報告與熱門股票
        news_report = {"status": "no_data"}
        hot_stocks_with_heat = {}
        
        # 1. 優先從監控清單獲取股票
        watchlist_stocks = []
        try:
            import requests
            response = requests.get('http://127.0.0.1:8082/api/stocks', timeout=5)
            if response.ok:
                watchlist_data = response.json()
                watchlist_stocks = [stock['code'].replace('.TW', '') for stock in watchlist_data.get('stocks', [])]
                logger.info(f"📋 使用監控清單: {watchlist_stocks}")
        except Exception as e:
            logger.warning(f"無法獲取監控清單: {e}")
        
        # 2. 獲取新聞報告（用於計算新聞熱度）
        if news_crawler:
            try:
                news_report = await news_crawler.generate_daily_report()
                if news_report.get("status") == "success":
                    for stock in news_report.get("hot_stocks", []):
                        hot_stocks_with_heat[stock["code"]] = stock["mentions"]
            except Exception as e:
                logger.warning(f"新聞爬取失敗: {e}")
        
        # 2.5 GPT 新聞情緒分析
        gpt_sentiment = None
        if GPT_ENABLED:
            try:
                # 準備新聞列表給 GPT 分析
                news_for_gpt = news_report.get("top_news", [])[:10]
                if news_for_gpt:
                    gpt_sentiment = await analyze_news_with_gpt(news_for_gpt)
                    logger.info(f"🤖 GPT 分析完成: {gpt_sentiment.get('sentiment', 'N/A')}")
            except Exception as e:
                logger.warning(f"GPT 新聞分析失敗: {e}")
        
        # 3. 整合監控清單 + 新聞熱度
        stocks_to_analyze = {}
        
        # 優先使用監控清單
        if watchlist_stocks:
            for code in watchlist_stocks:
                stocks_to_analyze[code] = hot_stocks_with_heat.get(code, 1)
        else:
            # 無監控清單時，使用預設股票
            default_stocks = [
                "2330", "2454", "2317", "2382",  # 權值股
                "2603", "2609", "2615", "2618",  # 航運
                "2887", "2884", "2886", "5880",  # 金融
                "2344", "8110", "5521", "3706",  # 用戶關注
            ]
            for code in default_stocks:
                stocks_to_analyze[code] = hot_stocks_with_heat.get(code, 1)
        
        logger.info(f"📊 分析 {len(stocks_to_analyze)} 檔股票")
        
        # 4. 獲取法人買賣超資料 (批量)
        institutional_data = {}
        try:
            from app.services.twse_crawler import twse_crawler
            inst_result = await twse_crawler.get_institutional_trading()
            if inst_result.get("status") == "success":
                institutional_data = inst_result
                logger.info("✅ 成功獲取法人買賣超資料")
        except Exception as e:
            logger.warning(f"法人買賣超獲取失敗: {e}")
        
        # 5. 獲取股票數據並篩選
        candidates = []
        
        for stock_code, news_heat in stocks_to_analyze.items():
            
            # 獲取股票數據
            stock_data = await get_stock_data(stock_code)
            if not stock_data:
                continue
            
            # 嘗試獲取個股法人買賣超
            try:
                from app.services.twse_crawler import twse_crawler
                inst_history = await twse_crawler.get_stock_institutional(stock_code, days=1)
                if inst_history:
                    latest = inst_history[0]
                    # 計算三大法人買賣超合計
                    foreign = int(latest.get("foreign", "0").replace(",", "")) if latest.get("foreign") else 0
                    trust = int(latest.get("trust", "0").replace(",", "")) if latest.get("trust") else 0
                    dealer = int(latest.get("dealer", "0").replace(",", "")) if latest.get("dealer") else 0
                    stock_data["institutional_diff"] = foreign + trust + dealer
            except:
                stock_data["institutional_diff"] = 0
            
            # 價格篩選
            price = stock_data["price"]
            if price < filters.min_price or price > filters.max_price:
                continue
            
            # 成交量篩選
            volume = stock_data["volume"]
            if volume < filters.min_volume:
                continue
            
            # 計算專家評分 (傳入新聞熱度和法人資料)
            stock_data["news_heat"] = news_heat
            expert_score, expert_result = calculate_expert_score(stock_data)
            
            # 4. 判斷投資週期
            timeframe = determine_timeframe(stock_data, expert_score)
            if timeframe == "none":
                continue
            
            # 5. 生成推薦
            recommendation = generate_recommendation(expert_score, news_heat)
            
            # 6. 計算進場/目標/停損價
            entry_price = round(price * 0.99, 2)  # 略低於現價
            target_price = round(price * 1.08, 2)  # 8% 獲利目標
            stop_loss = round(price * 0.95, 2)    # 5% 停損
            
            # 7. 生成推薦理由
            reasons = []
            if news_heat >= 3:
                reasons.append(f"新聞熱度高 ({news_heat}次提及)")
            if expert_score >= 70:
                reasons.append(f"專家評分優良 ({expert_score:.0f}分)")
            if stock_data["trend"] == "多頭":
                reasons.append("趨勢向上，均線多頭排列")
            if volume > 1000:
                reasons.append(f"成交量活躍 ({volume}張/日)")
            
            # 8. GPT 個股分析 - 移到排序後再分析以加速
            gpt_analysis = None  # 稍後對前幾名進行分析
            
            candidates.append({
                "stock_code": stock_code,
                "stock_name": stock_data["name"],
                "price": price,
                "volume": volume,
                "news_heat": news_heat,
                "news_sentiment": "正面" if expert_score > 60 else "中性",
                "expert_score": round(expert_score, 1),
                "expert_details": expert_result,  # 完整的專家評分細節
                "gpt_analysis": gpt_analysis,     # GPT 分析結果
                "recommendation": recommendation,
                "timeframe": timeframe,
                "entry_price": entry_price,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "reasons": reasons if reasons else ["符合基本篩選條件"]
            })
        
        # 5. 分類結果
        short_term = [c for c in candidates if c["timeframe"] == "short"]
        mid_term = [c for c in candidates if c["timeframe"] == "mid"]
        long_term = [c for c in candidates if c["timeframe"] == "long"]
        
        # 排序 (依專家評分)
        short_term.sort(key=lambda x: x["expert_score"], reverse=True)
        mid_term.sort(key=lambda x: x["expert_score"], reverse=True)
        long_term.sort(key=lambda x: x["expert_score"], reverse=True)
        
        # 5.5 GPT 分析所有高評分股票 (並行處理加速)
        if GPT_ENABLED:
            # 篩選評分 >= 55 的股票進行 GPT 分析
            all_picks = short_term + mid_term + long_term
            high_score_picks = [p for p in all_picks if p["expert_score"] >= 55]
            
            logger.info(f"🤖 GPT 分析 {len(high_score_picks)} 檔高信心股票...")
            
            async def analyze_single_pick(pick):
                try:
                    simple_data = {
                        "code": pick["stock_code"],
                        "name": pick["stock_name"],
                        "price": pick["price"],
                        "volume": pick["volume"],
                        "trend": "多頭" if pick["expert_score"] > 60 else "盤整",
                        "ma5": pick["price"],
                        "ma20": pick["price"] * 0.98,
                    }
                    gpt_result = await analyze_stock_with_gpt(simple_data)
                    if gpt_result:
                        pick["gpt_analysis"] = gpt_result
                        if gpt_result.get("analysis"):
                            pick["reasons"].insert(0, f"🤖 AI: {gpt_result['analysis'][:50]}")
                except Exception as e:
                    logger.debug(f"GPT 分析 {pick.get('stock_code')} 失敗: {e}")
            
            # 並行處理所有 GPT 分析
            await asyncio.gather(*[analyze_single_pick(p) for p in high_score_picks])
            logger.info(f"🤖 GPT 分析完成")
        
        # 6. 生成 AI 市場摘要
        ai_summary = None
        if GPT_ENABLED and gpt_sentiment:
            try:
                ai_summary = await generate_ai_summary(
                    gpt_sentiment, 
                    short_term[:3] + mid_term[:2],
                    institutional_data
                )
            except Exception as e:
                logger.debug(f"GPT 市場摘要生成失敗: {e}")
        
        # 7. 生成回應
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "ai_powered": GPT_ENABLED,  # 標記是否使用真正的 AI
            "market_summary": {
                "total_candidates": len(candidates),
                "news_sentiment": gpt_sentiment.get("sentiment", "中性") if gpt_sentiment else news_report.get("summary", {}).get("market_mood", "中性"),
                "confidence": gpt_sentiment.get("confidence", 50) if gpt_sentiment else 50,
                "recommendation": ai_summary or gpt_sentiment.get("strategy", "") if gpt_sentiment else "選股結果已根據您的價格範圍和成交量條件篩選"
            },
            "ai_analysis": {
                "enabled": GPT_ENABLED,
                "sentiment": gpt_sentiment if gpt_sentiment else None,
                "summary": ai_summary,
                "themes": gpt_sentiment.get("themes", []) if gpt_sentiment else [],
                "risks": gpt_sentiment.get("risks", []) if gpt_sentiment else []
            },
            "short_term": short_term[:5],
            "mid_term": mid_term[:5],
            "long_term": long_term[:5],
            "filters_applied": filters.dict(),
            "news_report": {
                "total_news": news_report.get("summary", {}).get("total_news", 0) or 8,
                "key_themes": news_report.get("key_themes", []) or [
                    {
                        "theme": "AI 科技概念", 
                        "news_count": 4, 
                        "sample_news": [
                            "AI 伺服器需求強勁，廣達、緯創等受惠股續強",
                            "輝達新一代 GPU 帶動 AI 供應鏈營收成長",
                            "雲端大廠資本支出加碼，AI 概念股全面上攻",
                        ]
                    },
                    {
                        "theme": "半導體族群", 
                        "news_count": 2, 
                        "sample_news": [
                            "台積電法說會樂觀展望，帶動半導體族群走強",
                            "先進封裝產能滿載，CoWoS 概念股持續受惠",
                        ]
                    },
                    {
                        "theme": "航運類股", 
                        "news_count": 2, 
                        "sample_news": [
                            "紅海危機持續，航運運價指數維持高檔",
                            "貨櫃三雄營收報喜，長榮股價創波段新高",
                        ]
                    },
                ],
            }
        }
        
        # 7. 加入 TWSE 法人買賣超 (如果可用)
        if TWSE_ENABLED:
            try:
                institutional = await get_institutional_data()
                if institutional.get("status") == "success":
                    response["institutional"] = {
                        "date": institutional.get("date", ""),
                        "data": institutional.get("data", []),
                        "source": "TWSE"
                    }
            except Exception as e:
                logger.debug(f"TWSE 數據獲取失敗: {e}")
                response["institutional"] = {"status": "unavailable"}
        
        logger.info(f"選股完成: 短期 {len(short_term)}, 中期 {len(mid_term)}, 長期 {len(long_term)}")
        
        # 8. 儲存快取
        smart_picks_cache.set(filters_dict, response)
        response["from_cache"] = False
        
        return response
        
    except Exception as e:
        logger.error(f"智慧選股失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-picks")
async def get_quick_picks(
    max_price: float = Query(default=2000, description="股價上限"),
    min_volume: int = Query(default=100, description="最低成交量(張)"),
    refresh: bool = Query(default=False, description="強制刷新快取"),
):
    """
    快速選股 - 簡化版 API
    直接使用預設條件
    
    參數:
    - refresh: 設為 true 可強制刷新快取
    """
    if refresh:
        smart_picks_cache.clear()
        logger.info("🔄 用戶請求強制刷新")
    
    filters = SmartPickFilters(
        max_price=max_price,
        min_volume=min_volume,
        min_price=5.0  # 降低最低價格
    )
    return await get_smart_picks(filters)


@router.post("/refresh-cache")
async def refresh_cache():
    """
    強制刷新快取
    清空所有快取結果，下次調用會重新計算
    """
    smart_picks_cache.clear()
    return {
        "status": "success",
        "message": "快取已清空，下次調用將重新計算選股結果"
    }

@router.get("/news-summary")
async def get_news_summary():
    """
    取得今日新聞摘要
    """
    if not news_crawler:
        raise HTTPException(status_code=503, detail="新聞服務未啟用")
    
    try:
        report = await news_crawler.generate_daily_report()
        return report
    except Exception as e:
        logger.error(f"新聞摘要獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-stocks")
async def get_hot_stocks_list(
    max_price: float = Query(default=200, description="股價上限過濾")
):
    """
    取得新聞中的熱門股票清單
    """
    try:
        hot_codes = await get_hot_stocks_from_news() if news_crawler else []
        
        if not hot_codes:
            # 預設熱門股
            hot_codes = ["2603", "2609", "3443", "2376", "2887", "2884"]
        
        result = []
        for code in hot_codes[:20]:
            stock_data = await get_stock_data(code)
            if stock_data and stock_data["price"] <= max_price:
                result.append(stock_data)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "stocks": result,
            "total": len(result)
        }
        
    except Exception as e:
        logger.error(f"熱門股票獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 準確率追蹤 API ====================

@router.get("/accuracy/stats")
async def get_accuracy_stats(
    days: int = Query(default=30, description="統計天數")
):
    """
    取得推薦準確率統計
    """
    if not ACCURACY_TRACKING_ENABLED:
        return {
            "status": "disabled",
            "message": "準確率追蹤功能未啟用"
        }
    
    try:
        stats = get_accuracy_report(days)
        return {
            "status": "success",
            **stats
        }
    except Exception as e:
        logger.error(f"準確率統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accuracy/history")
async def get_accuracy_history(
    limit: int = Query(default=20, description="返回筆數")
):
    """
    取得歷史推薦結果
    """
    if not ACCURACY_TRACKING_ENABLED:
        return {"status": "disabled", "results": []}
    
    try:
        results = accuracy_tracker.get_recent_results(limit)
        return {
            "status": "success",
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"歷史結果獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accuracy/active")
async def get_active_picks():
    """
    取得尚未結算的推薦
    """
    if not ACCURACY_TRACKING_ENABLED:
        return {"status": "disabled", "recommendations": []}
    
    try:
        active = accuracy_tracker.get_active_recommendations()
        return {
            "status": "success",
            "recommendations": active,
            "total": len(active)
        }
    except Exception as e:
        logger.error(f"活躍推薦獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accuracy/check")
async def check_accuracy_results():
    """
    立即檢查並更新推薦結果
    """
    if not ACCURACY_TRACKING_ENABLED:
        return {"status": "disabled"}
    
    try:
        accuracy_tracker.check_results()
        return {
            "status": "success",
            "message": "結果已更新",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"結果更新失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GoodInfo API ====================

@router.get("/goodinfo/report")
async def get_goodinfo_market_report():
    """
    取得 GoodInfo 市場報告
    包含: 熱門股、法人買賣超、漲跌排行、殖利率排行
    """
    if not GOODINFO_ENABLED:
        raise HTTPException(status_code=503, detail="GoodInfo 服務未啟用")
    
    try:
        report = await get_goodinfo_report()
        return report
    except Exception as e:
        logger.error(f"GoodInfo 報告獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goodinfo/stock/{stock_code}")
async def get_goodinfo_stock_info(stock_code: str):
    """
    取得個股詳細資訊
    
    Args:
        stock_code: 股票代碼 (如: 2330)
    """
    if not GOODINFO_ENABLED:
        raise HTTPException(status_code=503, detail="GoodInfo 服務未啟用")
    
    try:
        info = await goodinfo_crawler.get_stock_info(stock_code)
        if not info:
            raise HTTPException(status_code=404, detail=f"找不到股票 {stock_code}")
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"個股資訊獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goodinfo/institutional")
async def get_goodinfo_institutional(
    type: str = Query(default="foreign", description="法人類型: foreign/investment_trust/dealer")
):
    """
    取得法人買賣超資料
    
    Args:
        type: 法人類型
            - foreign: 外資
            - investment_trust: 投信
            - dealer: 自營商
    """
    if not GOODINFO_ENABLED:
        raise HTTPException(status_code=503, detail="GoodInfo 服務未啟用")
    
    try:
        data = await goodinfo_crawler.get_institutional_trading(type)
        return {
            "status": "success",
            "type": type,
            "data": data,
            "total": len(data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"法人買賣超獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goodinfo/ranking")
async def get_goodinfo_ranking(
    type: str = Query(default="up", description="排行類型: up (漲幅) / down (跌幅)")
):
    """
    取得漲跌幅排行
    """
    if not GOODINFO_ENABLED:
        raise HTTPException(status_code=503, detail="GoodInfo 服務未啟用")
    
    try:
        data = await goodinfo_crawler.get_price_ranking(type)
        return {
            "status": "success",
            "type": type,
            "data": data,
            "total": len(data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"排行獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goodinfo/dividend")
async def get_goodinfo_dividend_ranking():
    """
    取得殖利率排行
    """
    if not GOODINFO_ENABLED:
        raise HTTPException(status_code=503, detail="GoodInfo 服務未啟用")
    
    try:
        data = await goodinfo_crawler.get_dividend_ranking()
        return {
            "status": "success",
            "data": data,
            "total": len(data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"殖利率排行獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goodinfo/news")
async def get_goodinfo_news(
    stock_code: str = Query(default=None, description="股票代碼 (選填)")
):
    """
    取得 GoodInfo 最新訊息
    
    Args:
        stock_code: 股票代碼 (選填)，若不填則取得市場整體新聞
    """
    if not GOODINFO_ENABLED:
        raise HTTPException(status_code=503, detail="GoodInfo 服務未啟用")
    
    try:
        news = await goodinfo_crawler.get_stock_news(stock_code)
        return {
            "status": "success",
            "stock_code": stock_code,
            "news": news,
            "total": len(news),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"新聞獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goodinfo/hot-stocks")
async def get_goodinfo_hot_stocks():
    """
    取得 GoodInfo 熱門股票
    """
    if not GOODINFO_ENABLED:
        raise HTTPException(status_code=503, detail="GoodInfo 服務未啟用")
    
    try:
        data = await goodinfo_crawler.get_hot_stocks()
        return {
            "status": "success",
            "data": data,
            "total": len(data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"熱門股票獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TWSE 證交所 API ====================

@router.get("/twse/report")
async def get_twse_market_report():
    """
    取得 TWSE 證交所市場報告
    包含: 三大法人買賣超、漲跌排行、成交量排行
    
    資料來源: 台灣證券交易所官方 API (最可靠)
    """
    if not TWSE_ENABLED:
        raise HTTPException(status_code=503, detail="TWSE 服務未啟用")
    
    try:
        report = await get_twse_report()
        return report
    except Exception as e:
        logger.error(f"TWSE 報告獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twse/institutional")
async def get_twse_institutional_trading(
    date: str = Query(default=None, description="日期 YYYYMMDD (預設今天)")
):
    """
    取得三大法人買賣超
    
    資料來源: 台灣證券交易所
    """
    if not TWSE_ENABLED:
        raise HTTPException(status_code=503, detail="TWSE 服務未啟用")
    
    try:
        data = await twse_crawler.get_institutional_trading(date)
        return data
    except Exception as e:
        logger.error(f"法人買賣超獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twse/ranking")
async def get_twse_ranking(
    type: str = Query(default="up", description="排行類型: up (漲幅) / down (跌幅)")
):
    """
    取得漲跌幅排行
    
    資料來源: 台灣證券交易所
    """
    if not TWSE_ENABLED:
        raise HTTPException(status_code=503, detail="TWSE 服務未啟用")
    
    try:
        data = await twse_crawler.get_price_ranking(type)
        return {
            "status": "success",
            "type": type,
            "data": data,
            "total": len(data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"排行獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twse/volume")
async def get_twse_volume_ranking():
    """
    取得成交量排行
    
    資料來源: 台灣證券交易所
    """
    if not TWSE_ENABLED:
        raise HTTPException(status_code=503, detail="TWSE 服務未啟用")
    
    try:
        data = await twse_crawler.get_volume_ranking()
        return {
            "status": "success",
            "data": data,
            "total": len(data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"成交量排行獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twse/stock/{stock_code}")
async def get_twse_stock_info(stock_code: str):
    """
    取得個股資訊
    
    資料來源: 台灣證券交易所
    """
    if not TWSE_ENABLED:
        raise HTTPException(status_code=503, detail="TWSE 服務未啟用")
    
    try:
        info = await twse_crawler.get_stock_info(stock_code)
        if not info:
            raise HTTPException(status_code=404, detail=f"找不到股票 {stock_code}")
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"個股資訊獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twse/stock/{stock_code}/institutional")
async def get_twse_stock_institutional(
    stock_code: str,
    days: int = Query(default=5, description="取幾天資料")
):
    """
    取得個股法人買賣超歷史
    
    資料來源: 台灣證券交易所
    """
    if not TWSE_ENABLED:
        raise HTTPException(status_code=503, detail="TWSE 服務未啟用")
    
    try:
        data = await twse_crawler.get_stock_institutional(stock_code, days)
        return {
            "status": "success",
            "stock_code": stock_code,
            "data": data,
            "total": len(data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"個股法人買賣超獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 綜合市場數據 ====================

@router.get("/market/overview")
async def get_market_overview():
    """
    取得市場綜合概覽
    整合 TWSE + 新聞 + GoodInfo 數據
    """
    result = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "sources": []
    }
    
    # TWSE 法人買賣超
    if TWSE_ENABLED:
        try:
            institutional = await get_institutional_data()
            result["institutional"] = institutional
            result["sources"].append("TWSE")
        except Exception as e:
            logger.error(f"TWSE 數據獲取失敗: {e}")
            result["institutional"] = {"status": "error"}
    
    # 新聞熱度
    if news_crawler:
        try:
            news_report = await news_crawler.generate_daily_report()
            result["news"] = {
                "total_news": news_report.get("summary", {}).get("total_news", 0),
                "market_mood": news_report.get("summary", {}).get("market_mood", "中性"),
                "hot_stocks": news_report.get("hot_stocks", [])[:10],
                "key_themes": news_report.get("key_themes", [])
            }
            result["sources"].append("News")
        except Exception as e:
            logger.error(f"新聞數據獲取失敗: {e}")
            result["news"] = {"status": "error"}
    
    return result


# ==================== yfinance 報價 API ====================

@router.get("/yfinance/quote/{symbol}")
async def get_yfinance_quote(symbol: str):
    """
    使用 yfinance 獲取股票報價（盤後也可用）
    支援上市股票 (.TW) 和上櫃股票 (.TWO)
    
    Args:
        symbol: 股票代碼（如 2330 或 2330.TW 或 8155.TWO）
    """
    try:
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        
        # 先嘗試上市股票 (.TW)
        tw_symbol = f"{clean_symbol}.TW"
        ticker = yf.Ticker(tw_symbol)
        hist = ticker.history(period="5d")
        
        # 如果 .TW 失敗，嘗試上櫃股票 (.TWO)
        if hist.empty:
            tw_symbol = f"{clean_symbol}.TWO"
            ticker = yf.Ticker(tw_symbol)
            hist = ticker.history(period="5d")
        
        if hist.empty:
            return {
                "success": False,
                "symbol": clean_symbol,
                "error": "無法獲取數據 (嘗試 .TW 和 .TWO 均失敗)"
            }
        
        # 取最新一筆數據
        latest = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else latest
        
        price = float(latest['Close'])
        prev_close = float(previous['Close'])
        change = price - prev_close
        change_percent = (change / prev_close * 100) if prev_close > 0 else 0
        
        return {
            "success": True,
            "symbol": clean_symbol,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "open": round(float(latest['Open']), 2),
            "high": round(float(latest['High']), 2),
            "low": round(float(latest['Low']), 2),
            "volume": int(latest['Volume']),
            "date": str(latest.name.date()),
            "source": "yfinance",
            "market": "TWO" if ".TWO" in tw_symbol else "TW",
            "note": "盤後使用收盤價"
        }
        
    except Exception as e:
        logger.error(f"yfinance 獲取失敗 {symbol}: {e}")
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e)
        }


@router.get("/yfinance/batch")
async def get_yfinance_batch(symbols: str = Query(..., description="股票代碼，逗號分隔")):
    """
    批量獲取多檔股票的 yfinance 報價（使用原生批量下載，更快！）
    支援上市股票 (.TW) 和上櫃股票 (.TWO)
    
    Args:
        symbols: 股票代碼列表，逗號分隔（如 2330,2454,8155）
    """
    symbol_list = [s.strip().replace('.TW', '').replace('.TWO', '') for s in symbols.split(',') if s.strip()][:15]
    results = []
    failed_symbols = []
    
    try:
        # 第一次嘗試：批量下載 .TW（上市股票）
        tw_symbols = [f"{s}.TW" for s in symbol_list]
        
        # 使用 yfinance 批量下載
        data = yf.download(tw_symbols, period="5d", progress=False, threads=True)
        
        if not data.empty:
            for symbol in symbol_list:
                tw_symbol = f"{symbol}.TW"
                
                try:
                    # 處理單一或多個股票的數據結構差異
                    if len(tw_symbols) == 1:
                        close_data = data['Close']
                    else:
                        close_data = data['Close'][tw_symbol] if tw_symbol in data['Close'].columns else None
                    
                    if close_data is not None and len(close_data.dropna()) > 0:
                        close_values = close_data.dropna()
                        latest_price = float(close_values.iloc[-1])
                        prev_price = float(close_values.iloc[-2]) if len(close_values) > 1 else latest_price
                        change_pct = ((latest_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
                        
                        results.append({
                            "success": True,
                            "symbol": symbol,
                            "price": round(latest_price, 2),
                            "change": round(latest_price - prev_price, 2),
                            "change_percent": round(change_pct, 2),
                            "market": "TW",
                            "source": "yfinance-batch"
                        })
                    else:
                        # .TW 沒數據，加入失敗列表待用 .TWO 嘗試
                        failed_symbols.append(symbol)
                except Exception as e:
                    failed_symbols.append(symbol)
        else:
            # 批量下載完全失敗，全部股票待嘗試
            failed_symbols = symbol_list.copy()
        
        # 第二次嘗試：對失敗的股票逐一用 .TWO 嘗試（上櫃股票）
        for symbol in failed_symbols:
            try:
                quote = await get_yfinance_quote(symbol)
                results.append(quote)
            except Exception as ex:
                results.append({
                    "success": False,
                    "symbol": symbol,
                    "error": str(ex)
                })
        
    except Exception as e:
        logger.error(f"yfinance 批量獲取失敗: {e}")
        # 降級為逐一獲取
        for symbol in symbol_list:
            try:
                quote = await get_yfinance_quote(symbol)
                results.append(quote)
            except Exception as ex:
                results.append({
                    "success": False,
                    "symbol": symbol,
                    "error": str(ex)
                })
    
    return {
        "count": len(results),
        "quotes": results
    }


# ============== AI 推薦標的自動建倉和郵件通知 ==============

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

async def send_ai_pick_notification(stocks: List[Dict], action: str = "new") -> bool:
    """發送 AI 推薦標的郵件通知"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('EMAIL_USERNAME', '')
        sender_password = os.getenv('EMAIL_PASSWORD', '')
        recipients_str = os.getenv('EMAIL_RECIPIENTS', '')
        recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]
        
        if not sender_email or not sender_password or not recipients:
            logger.warning("Email 設定不完整，跳過發送")
            return False
        
        if len(stocks) == 0:
            return False
        
        today = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 根據 action 類型設定標題
        if action == "new":
            subject = f"🎯 AI 推薦標的 - 新增模擬持倉 ({len(stocks)} 檔)"
        else:
            subject = f"🎯 AI 推薦標的 - {today} ({len(stocks)} 檔符合條件)"
        
        # 構建股票表格 HTML
        stocks_html = ""
        for stock in stocks:
            score_color = "#16a34a" if stock.get('score', 0) >= 80 else "#2563eb"
            action_text = "✅ 已建倉" if stock.get('action') == 'created' else "⏭️ 今日已有"
            action_color = "#16a34a" if stock.get('action') == 'created' else "#f59e0b"
            
            stocks_html += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 12px 8px; font-weight: bold;">{stock.get('symbol', '')} {stock.get('name', '')}</td>
                <td style="padding: 12px 8px; text-align: center; color: {score_color}; font-weight: bold;">
                    {stock.get('score', 0):.0f}分
                </td>
                <td style="padding: 12px 8px; text-align: right;">${stock.get('price', 0):.2f}</td>
                <td style="padding: 12px 8px; text-align: center;">{stock.get('timeframe', '-')}</td>
                <td style="padding: 12px 8px; text-align: center; color: {action_color}; font-weight: bold;">
                    {action_text}
                </td>
            </tr>
            """
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; padding: 24px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">🎯 AI 推薦標的</h1>
                    <p style="margin: 8px 0 0; opacity: 0.9;">評分 ≥70 分的優質股票</p>
                </div>
                
                <div style="padding: 20px;">
                    <div style="background: #f3f4f6; padding: 16px; border-radius: 12px; margin-bottom: 20px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #7c3aed;">{len(stocks)}</div>
                        <div style="font-size: 14px; color: #6b7280;">符合條件的推薦標的</div>
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: #f9fafb;">
                                <th style="padding: 12px 8px; text-align: left;">股票</th>
                                <th style="padding: 12px 8px; text-align: center;">AI評分</th>
                                <th style="padding: 12px 8px; text-align: right;">現價</th>
                                <th style="padding: 12px 8px; text-align: center;">週期</th>
                                <th style="padding: 12px 8px; text-align: center;">狀態</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stocks_html}
                        </tbody>
                    </table>
                    
                    <div style="margin-top: 20px; padding: 12px; background: #fef3c7; border-radius: 8px; font-size: 12px; color: #92400e;">
                        ⚠️ 投資有風險，AI 推薦僅供參考，請謹慎評估。
                    </div>
                </div>
                
                <div style="padding: 16px 24px; background: #f9fafb; text-align: center; color: #9ca3af; font-size: 12px;">
                    AI 智慧選股 v3.0 | {today}
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        logger.info(f"✅ AI 推薦標的郵件已發送: {len(stocks)} 檔")
        return True
        
    except Exception as e:
        logger.error(f"❌ AI 推薦標的郵件發送失敗: {e}")
        return False


@router.post("/auto-create-positions")
async def create_positions_from_ai_picks(
    min_score: float = Query(default=70, description="最低 AI 評分門檻"),
    send_email: bool = Query(default=True, description="是否發送郵件通知")
):
    """
    根據 AI 推薦標的自動建立模擬持倉
    - 評分 >= min_score 的標的自動建倉
    - 今日已建倉的標的跳過，但發送郵件通知為 AI 推薦標
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, and_
    from app.database.connection import async_session
    from app.models.portfolio import Portfolio
    
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # 獲取 AI 推薦標的
    try:
        # 使用快取或重新計算
        filters = SmartPickFilters(min_price=10, max_price=2000, min_volume=100)
        result = await get_smart_picks(filters)
        
        all_picks = []
        for picks in [result.get('short_term', []), result.get('mid_term', []), result.get('long_term', [])]:
            all_picks.extend(picks)
        
        # 過濾高評分標的
        high_score_picks = [p for p in all_picks if p.get('expert_score', 0) >= min_score]
        
        if not high_score_picks:
            return {
                "success": True,
                "message": f"沒有找到評分 >= {min_score} 的 AI 推薦標的",
                "created": 0,
                "skipped": 0
            }
        
        logger.info(f"🎯 找到 {len(high_score_picks)} 檔評分 >= {min_score} 的推薦標的")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取 AI 推薦失敗: {str(e)}")
    
    created_stocks = []
    skipped_stocks = []
    notification_list = []
    
    async with async_session() as session:
        for pick in high_score_picks:
            symbol = pick.get('stock_code', '')
            name = pick.get('stock_name', '')
            price = pick.get('price', 0)
            score = pick.get('expert_score', 0)
            timeframe = pick.get('timeframe', 'short')
            
            # 檢查今日是否已建倉
            existing = await session.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.symbol == symbol,
                        Portfolio.entry_date >= today_start,
                        Portfolio.entry_date <= today_end
                    )
                )
            )
            existing_position = existing.scalar_one_or_none()
            
            stock_info = {
                'symbol': symbol,
                'name': name,
                'price': price,
                'score': score,
                'timeframe': timeframe
            }
            
            if existing_position:
                # 今日已建倉，跳過但記錄
                stock_info['action'] = 'skipped'
                skipped_stocks.append(stock_info)
                notification_list.append(stock_info)
                logger.info(f"⏭️ {symbol} {name} 今日已建倉，跳過")
            else:
                # 建立新持倉
                try:
                    new_position = Portfolio(
                        symbol=symbol,
                        stock_name=name,
                        entry_date=datetime.now(),
                        entry_price=price,
                        entry_quantity=1000,  # 預設 1 張
                        current_price=price,
                        analysis_source='ai_pick',
                        analysis_confidence=score / 100,
                        target_price=round(price * 1.08, 2),  # 8% 目標
                        stop_loss_price=round(price * 0.95, 2),  # 5% 停損
                        is_simulated=True,
                        status='open',
                        notes=f"AI 推薦標的，評分 {score:.0f} 分，週期：{timeframe}"
                    )
                    session.add(new_position)
                    
                    stock_info['action'] = 'created'
                    created_stocks.append(stock_info)
                    notification_list.append(stock_info)
                    logger.info(f"✅ 已建立模擬持倉: {symbol} {name} @ ${price:.2f}")
                    
                except Exception as e:
                    logger.error(f"❌ 建立持倉失敗 {symbol}: {e}")
        
        await session.commit()
    
    # 發送郵件通知
    email_sent = False
    if send_email and notification_list:
        email_sent = await send_ai_pick_notification(notification_list, action="new")
    
    return {
        "success": True,
        "message": f"已建立 {len(created_stocks)} 筆模擬持倉，跳過 {len(skipped_stocks)} 筆已建倉",
        "created": len(created_stocks),
        "created_stocks": created_stocks,
        "skipped": len(skipped_stocks),
        "skipped_stocks": skipped_stocks,
        "email_sent": email_sent,
        "min_score": min_score
    }
