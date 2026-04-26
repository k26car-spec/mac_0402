"""
LSTM模型管理器 (LSTM Manager)
负责管理所有LSTM模型的加载、数据预处理和预测
集成到 Smart Entry 系统中作为 AI 辅助决策模块
"""

import os
import json
import numpy as np
import pandas as pd
import pickle
from datetime import datetime, timedelta
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')

class LSTMManager:
    def __init__(self, model_dir='models/lstm_smart_entry', whitelist_file='lstm_whitelist.json'):
        self.model_dir = model_dir
        self.whitelist_file = whitelist_file
        self.models = {}
        self.scalers = {}
        self.whitelist = {}
        self.sequence_length = 20
        
        # 初始化：加载白名单
        self._load_whitelist()
        
    def _load_whitelist(self):
        """加载白名单配置"""
        if os.path.exists(self.whitelist_file):
            with open(self.whitelist_file, 'r') as f:
                raw = json.load(f)
            # 過濾 _meta 等特殊鍵，只保留股票代碼
            self.whitelist = {k: v for k, v in raw.items() if not k.startswith('_')}
            meta_total = raw.get('_meta', {}).get('total_stocks', len(self.whitelist))
            print(f"✅ LSTM Manager: 已加载白名单，共 {len(self.whitelist)} 支股票 (meta記錄={meta_total})")
        else:
            print(f"⚠️ LSTM Manager: 白名单文件不存在 ({self.whitelist_file})，LSTM 功能将不可用")

    def _get_model_path(self, stock_code):
        return os.path.join(self.model_dir, f"{stock_code}_model.h5")
        
    def _get_scaler_path(self, stock_code):
        return os.path.join(self.model_dir, f"{stock_code}_scaler.pkl")

    def _load_model_for_stock(self, stock_code):
        """懒加载：只在需要时加载特定股票的模型"""
        if stock_code in self.models:
            return self.models[stock_code]
            
        model_path = self._get_model_path(stock_code)
        if not os.path.exists(model_path):
            print(f"❌ LSTM Manager: 模型文件不存在 {model_path}")
            return None
            
        try:
            # 兼容性加载
            try:
                model = load_model(model_path, compile=False)
            except:
                import tensorflow.keras.metrics as metrics
                custom_objects = {
                    'mse': metrics.MeanSquaredError(),
                    'mae': metrics.MeanAbsoluteError()
                }
                model = load_model(model_path, custom_objects=custom_objects, compile=False)
                
            self.models[stock_code] = model
            # print(f"✅ LSTM Manager: 已加载模型 {stock_code}")
            return model
        except Exception as e:
            print(f"❌ LSTM Manager: 模型加载失败 {stock_code}: {e}")
            return None

    def preprocess_data(self, df, stock_code: str = None):
        """
        將原始 K 線數據轉換為模型輸入格式
        v5: 優先使用 35 個強化特徵 (lstm_feature_builder)
        v4/舊版: 退回 9 個技術指標
        """
        try:
            # ── 嘗試 v5 模式：載入已儲存的 scaler + 特徵清單 ──
            if stock_code:
                scaler_path = os.path.join(self.model_dir,
                                           f'{stock_code}_scaler_v5.pkl')
                if os.path.exists(scaler_path):
                    import pickle
                    with open(scaler_path, 'rb') as f:
                        saved = pickle.load(f)
                    scaler       = saved['scaler']
                    feature_cols = saved.get('top_feat_names', saved['feature_cols'])

                    from lstm_feature_builder import build_features_full
                    import yfinance as yf
                    bench = yf.Ticker('^TWII').history(period='1y')
                    df_feat, _ = build_features_full(df, bench)

                    if len(df_feat) < self.sequence_length:
                        return None

                    # 確保所有需要的特徵都在 df_feat 中
                    missing = [c for c in feature_cols if c not in df_feat.columns]
                    if missing:
                        # 如果 v5 builder 缺特徵，可能是 v6 模型，嘗試用 v3 builder
                        try:
                            from lstm_feature_builder_v3 import build_features_v3
                            df_feat, _ = build_features_v3(df, bench)
                        except:
                            pass
                    
                    recent = df_feat.reindex(columns=feature_cols).iloc[-self.sequence_length:]
                    # 填補 NaN 並確保維度正確 (samples, seq_len, n_features)
                    X_input = recent.fillna(0).values
                    
                    # 再次檢查維度是否匹配 scaler
                    if X_input.shape[1] != len(feature_cols):
                        print(f"⚠️ 特徵維度不符: 預期 {len(feature_cols)} 但得到 {X_input.shape[1]}")
                        return None
                        
                    scaled = scaler.transform(X_input)
                    return np.array([scaled])  # shape (1, seq_len, n_feat)

            # ── 回退到 v4/舊版：9 個技術指標 ──
            df = df.copy()
            df['MA5']        = df['Close'].rolling(window=5).mean()
            df['MA10']       = df['Close'].rolling(window=10).mean()
            df['MA20']       = df['Close'].rolling(window=20).mean()
            df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
            delta = df['Close'].diff()
            gain  = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss  = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs    = gain / (loss + 1e-9)
            df['RSI']        = 100 - (100 / (1 + rs))
            df['Volatility'] = df['Close'].rolling(window=20).std()
            exp1  = df['Close'].ewm(span=12, adjust=False).mean()
            exp2  = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD']       = exp1 - exp2
            df = df.dropna()

            if len(df) < self.sequence_length:
                return None

            recent_df = df.iloc[-self.sequence_length:]
            feature_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20',
                            'Volume_MA5', 'RSI', 'Volatility', 'MACD']
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
            scaled = scaler.fit_transform(recent_df[feature_cols])
            return np.array([scaled])

        except Exception as e:
            print(f'❌ 數據預處理錯誤: {e}')
            return None

    def predict(self, stock_code, df):
        """
        核心預測接口（支援 v5 35特徵 + 舊版 9特徵）
        """
        stock_code = str(stock_code)

        # 1. 白名單檢查
        if stock_code not in self.whitelist:
            return {'available': False, 'reason': 'Not in whitelist'}

        threshold_info = self.whitelist[stock_code]
        threshold = threshold_info.get('threshold', 0.5)

        # 2. 載入模型
        model = self._load_model_for_stock(stock_code)
        if model is None:
            return {'available': False, 'reason': 'Model load failed'}

        # 3. 準備數據（優先 v5 模式）
        input_data = self.preprocess_data(df, stock_code=stock_code)
        if input_data is None:
            return {'available': False, 'reason': 'Insufficient data'}

        # 4. 預測
        try:
            prediction = model.predict(input_data, verbose=0)[0][0]
            signal     = 1 if prediction > threshold else 0
            confidence = float(abs(prediction - threshold) * 10)

            return {
                'available':  True,
                'signal':     signal,
                'raw_pred':   float(prediction),
                'threshold':  float(threshold),
                'confidence': confidence,
                'version':    threshold_info.get('version', 'v4')
            }
        except Exception as e:
            return {'available': False, 'reason': f'Prediction error: {e}'}

# 單例模式輔助變量
_lstm_manager_instance = None

def get_lstm_manager():
    global _lstm_manager_instance
    if _lstm_manager_instance is None:
        _lstm_manager_instance = LSTMManager()
    return _lstm_manager_instance


# ─── 大盤風向偵測（緩存 5 分鐘）────────────────────────────────
_market_context_cache = {'data': None, 'ts': None}

# 盤中急跌門檻（可調整）
_BEAR_INTRADAY_THRESHOLD  = -2.0   # 盤中跌幅 > 2% → 強制 BEAR
_BULL_INTRADAY_THRESHOLD  =  2.0   # 盤中漲幅 > 2% → 強制 BULL
_BEAR_GAP_THRESHOLD       = -1.5   # 跳空低開 > 1.5% + 盤中繼跌 → BEAR

def get_market_context() -> dict:
    """
    獲取大盤當日即時風向（v2）
    每 5 分鐘更新一次，避免頻繁請求

    ★ v2 升級：
    - 優先用「今日開盤→目前即時價」計算盤中漲跌（5m K棒）
    - 盤中跌幅 > 2%  → 強制 BEAR（不等收盤，阻擋新進場）
    - 盤中漲幅 > 2%  → 強制 BULL
    - 跳空低開 + 盤中繼跌 → 複合空頭信號
    - 額外欄位：intraday_drop / gap_pct / forced

    Returns:
        {
          'status':         'BULL' | 'NEUTRAL' | 'BEAR',
          'chg_pct':        float,  # 昨收→最新 漲跌幅
          'intraday_drop':  float,  # 今開→最新 盤中漲跌（負=跌）
          'gap_pct':        float,  # 今開 vs 昨收 跳空
          'open_price':     float,
          'current_price':  float,
          'prev_close':     float,
          'desc':           str,
          'forced':         bool,   # True = 因盤中跌幅強制切換
        }
    """
    global _market_context_cache
    now = datetime.now()

    # 緩存有效期 5 分鐘
    if (_market_context_cache['ts'] and
            now - _market_context_cache['ts'] < timedelta(minutes=5)):
        return _market_context_cache['data']

    try:
        import yfinance as yf
        twii = yf.Ticker('^TWII')

        # ① 日 K（取昨收 / 今開）
        hist = twii.history(period='5d')
        if hist.empty or len(hist) < 2:
            raise ValueError('TWII history empty')

        prev_close  = float(hist['Close'].iloc[-2])   # 昨日收盤
        today_open  = float(hist['Open'].iloc[-1])    # 今日開盤
        today_close = float(hist['Close'].iloc[-1])   # 今日收盤（非交易中用此代替）

        # ② 嘗試取 5 分鐘 K 棒拿即時價
        try:
            intra = twii.history(period='1d', interval='5m')
            if not intra.empty:
                current_price = float(intra['Close'].iloc[-1])
            else:
                current_price = today_close
        except Exception:
            current_price = today_close

        # ③ 三維計算
        chg_pct      = (current_price - prev_close) / prev_close * 100   # 昨收→最新
        intraday_pct = (current_price - today_open)  / today_open  * 100 if today_open > 0 else 0.0  # 盤中
        gap_pct      = (today_open - prev_close)     / prev_close  * 100 if prev_close > 0 else 0.0  # 跳空

        forced = False

        # ══ 優先看盤中即時跌幅（最重要） ══
        if intraday_pct <= _BEAR_INTRADAY_THRESHOLD:
            status = 'BEAR'
            forced = True
            desc = (f'🚨 盤中急跌 {intraday_pct:.2f}%'
                    f'（開={today_open:.0f}→現={current_price:.0f}）'
                    f'，強制 BEAR，LSTM 扣分大幅加重')

        elif intraday_pct >= _BULL_INTRADAY_THRESHOLD:
            status = 'BULL'
            forced = True
            desc = (f'🚀 盤中強勢 +{intraday_pct:.2f}%'
                    f'（開={today_open:.0f}→現={current_price:.0f}）'
                    f'，強制 BULL')

        elif gap_pct <= _BEAR_GAP_THRESHOLD and intraday_pct <= -0.5:
            # 跳空低開 + 盤中繼續跌 → 複合空頭
            status = 'BEAR'
            forced = True
            desc = (f'⚠️ 跳空低開 {gap_pct:.2f}% + 盤中再跌 {intraday_pct:.2f}%'
                    f'，複合空頭信號，強制 BEAR')

        elif chg_pct >= 1.5:
            status = 'BULL'
            desc = f'大盤強勢（昨收→今）+{chg_pct:.2f}%，放寬 LSTM 觀望扣分'

        elif chg_pct <= -1.5:
            status = 'BEAR'
            desc = f'大盤弱勢（昨收→今）{chg_pct:.2f}%，加強 LSTM 觀望扣分'

        else:
            status = 'NEUTRAL'
            desc = (f'大盤中性 {chg_pct:+.2f}%'
                    f'（盤中 {intraday_pct:+.2f}%）'
                    f'，正常計分')

        result = {
            'status':        status,
            'chg_pct':       round(chg_pct, 2),
            'intraday_drop': round(intraday_pct, 2),
            'gap_pct':       round(gap_pct, 2),
            'open_price':    round(today_open, 0),
            'current_price': round(current_price, 0),
            'prev_close':    round(prev_close, 0),
            'desc':          desc,
            'forced':        forced,
        }

    except Exception as e:
        result = {
            'status': 'NEUTRAL', 'chg_pct': 0.0,
            'intraday_drop': 0.0, 'gap_pct': 0.0,
            'open_price': 0.0, 'current_price': 0.0, 'prev_close': 0.0,
            'desc': f'取得大盤失敗: {e}', 'forced': False,
        }

    _market_context_cache['data'] = result
    _market_context_cache['ts']   = now
    return result
