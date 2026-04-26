import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TechnicalAnalysisService:
    @staticmethod
    def calculate_indicators(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        計算技術指標 (MA, Volume MA, RSI, MACD等)
        確保所有回傳數據皆可 JSON 序列化 (排除 numpy 類型)
        """
        if not candles or len(candles) < 5:
            return {"error": "Insufficient data"}

        try:
            df = pd.DataFrame(candles)
            
            # 確保必要的欄位存在並轉換為數值
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 移除無效數據
            df = df.dropna(subset=['close'])
            
            if len(df) < 5:
                return {"error": "Insufficient valid data after cleanup"}

            # 1. 計算均線 (Moving Averages)
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()

            # 2. 計算成交量均線 (Volume MAs)
            df['MV5'] = df['volume'].rolling(window=5).mean()
            df['MV20'] = df['volume'].rolling(window=20).mean()

            # 3. 計算 RSI (14)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            df['RSI'] = 100 - (100 / (1 + rs))
            df['RSI'] = df['RSI'].fillna(50) # 預設中值

            # 4. 計算 MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Hist'] = df['MACD'] - df['Signal']

            # 5. K線形態與趨勢分析
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            trend = "盤整中 (Neutral)"
            ma5, ma10, ma20 = latest['MA5'], latest['MA10'], latest['MA20']
            
            if not np.isnan(ma5) and not np.isnan(ma10) and not np.isnan(ma20):
                if ma5 > ma10 > ma20: trend = "多頭排列 (Bullish)"
                elif ma5 < ma10 < ma20: trend = "空頭排列 (Bearish)"
            
            # 交叉訊號
            signal = "無明顯訊號"
            if len(df) > 2:
                if prev['MA5'] <= prev['MA10'] and latest['MA5'] > latest['MA10']:
                    signal = "金叉 (MA5 🚀 MA10)"
                elif prev['MA5'] >= prev['MA10'] and latest['MA5'] < latest['MA10']:
                    signal = "死叉 (MA5 📉 MA10)"

            # 安全轉換函數
            def safe_float(val):
                if pd.isna(val) or np.isinf(val): return None
                return float(val)

            # 構建回傳結果
            result = {
                "current": {
                    "price": safe_float(latest['close']),
                    "ma5": safe_float(latest['MA5']),
                    "ma10": safe_float(latest['MA10']),
                    "ma20": safe_float(latest['MA20']),
                    "ma60": safe_float(latest['MA60']),
                    "rsi": safe_float(latest['RSI']),
                    "macd": safe_float(latest['MACD']),
                    "macd_hist": safe_float(latest['Hist']),
                    "trend": trend,
                    "signal": signal,
                    "volume_ratio": safe_float(latest['volume'] / latest['MV20']) if latest['MV20'] > 0 else 1.0
                },
                "history": []
            }

            # 處理歷史數據並確保 JSON 安全
            hist_df = df.tail(60).copy()
            for _, row in hist_df.iterrows():
                hist_item = {}
                for k, v in row.items():
                    hist_item[k] = safe_float(v) if isinstance(v, (int, float, np.number)) else str(v)
                result["history"].append(hist_item)

            return result
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}", exc_info=True)
            return {"error": f"Internal calculation error: {str(e)}"}

tech_analysis_service = TechnicalAnalysisService()
