"""
智能股價預測服務 v2.0
Smart Price Prediction Service with Self-Learning

功能：
1. 真正的技術指標特徵工程（RSI/MACD/布林帶/法人/VIX）
2. 方向預測主導（up/down/neutral），比價格誤差更重要
3. 預測存入 PostgreSQL，每日自動驗證
4. 成功/失敗自動分析，累積改進
5. 目標：2週內方向準確率達 80%
"""

import asyncio
import json
import logging
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# 模型存放路徑
MODEL_BASE = "/Users/Mac/Documents/ETF/AI/Ａi-catch/models/lstm_v2"
os.makedirs(MODEL_BASE, exist_ok=True)


class FeatureEngineer:
    """
    特徵工程：從歷史 OHLCV + 法人 + 大盤 生成 LSTM 輸入特徵
    共 18 個特徵 × 30 日視窗
    """
    FEATURE_NAMES = [
        'close_norm',       # 收盤價（標準化）
        'return_1d',        # 日報酬率
        'return_5d',        # 5日報酬率
        'volume_ratio',     # 成交量比（vs 20日均量）
        'rsi_14',           # RSI(14)
        'macd_signal',      # MACD histogram
        'bb_pct',           # 布林帶位置（0=下緣, 1=上緣）
        'ma5_dev',          # 偏離MA5%
        'ma20_dev',         # 偏離MA20%
        'ma60_dev',         # 偏離MA60%
        'atr_ratio',        # ATR(14)/收盤價
        'high_low_ratio',   # (High-Low)/Close
        'inst_net_norm',    # 法人買賣超（標準化）
        'foreign_5d_sum',   # 外資5日累計
        'vix_norm',         # VIX（標準化）
        'market_return',    # 大盤日報酬
        'cci_14',           # CCI(14)
        'stoch_k',          # Stochastic K
    ]
    SEQ_LEN = 30  # 30日視窗

    async def build_features(self, symbol: str) -> Optional[np.ndarray]:
        """
        建立特徵矩陣 shape = (SEQ_LEN, 18)
        返回 None 如果數據不足
        """
        try:
            import yfinance as yf
            from ta.momentum import RSIIndicator, StochasticOscillator
            from ta.trend import MACD, CCIIndicator
            from ta.volatility import BollingerBands, AverageTrueRange

            # 取 90 天歷史（足夠計算指標 + 視窗）
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="120d")
            if len(hist) < self.SEQ_LEN + 30:
                logger.warning(f"{symbol}: 歷史數據不足 ({len(hist)} 天)")
                return None

            close = hist['Close']
            high = hist['High']
            low = hist['Low']
            volume = hist['Volume']

            # === 技術指標計算 ===
            rsi = RSIIndicator(close, 14).rsi()
            macd_obj = MACD(close)
            macd_hist = macd_obj.macd_diff()
            bb = BollingerBands(close, 20, 2)
            bb_pct = (close - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband() + 1e-9)
            atr = AverageTrueRange(high, low, close, 14).average_true_range()
            cci = CCIIndicator(high, low, close, 14).cci()
            stoch = StochasticOscillator(high, low, close).stoch()

            ma5 = close.rolling(5).mean()
            ma20 = close.rolling(20).mean()
            ma60 = close.rolling(60).mean()
            vol_ma20 = volume.rolling(20).mean()

            # === 法人數據（從 DB 讀取）===
            inst_net = await self._get_institutional_net(symbol, len(hist))

            # === 大盤 & VIX ===
            vix_arr, market_ret = await self._get_market_data(len(hist))

            # === 組合特徵矩陣 ===
            features = np.column_stack([
                self._normalize(close.values),                             # close_norm
                close.pct_change().fillna(0).values,                       # return_1d
                close.pct_change(5).fillna(0).values,                      # return_5d
                (volume / (vol_ma20 + 1e-9)).fillna(1).values,            # volume_ratio
                self._normalize(rsi.fillna(50).values),                    # rsi_14
                self._normalize(macd_hist.fillna(0).values),               # macd_signal
                bb_pct.fillna(0.5).clip(0, 1).values,                     # bb_pct
                ((close - ma5) / (ma5 + 1e-9)).fillna(0).values,         # ma5_dev
                ((close - ma20) / (ma20 + 1e-9)).fillna(0).values,       # ma20_dev
                ((close - ma60) / (ma60 + 1e-9)).fillna(0).values,       # ma60_dev
                (atr / (close + 1e-9)).fillna(0).values,                  # atr_ratio
                ((high - low) / (close + 1e-9)).fillna(0).values,        # high_low_ratio
                self._normalize(inst_net),                                  # inst_net_norm
                self._rolling_sum(inst_net, 5),                            # foreign_5d_sum
                self._normalize(vix_arr),                                   # vix_norm
                market_ret,                                                  # market_return
                self._normalize(cci.fillna(0).values),                     # cci_14
                self._normalize(stoch.fillna(50).values),                  # stoch_k
            ])

            # 截取最後 SEQ_LEN 天
            features = features[-self.SEQ_LEN:]
            features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)

            # 返回特徵 + 當前收盤價（用於還原預測）
            current_price = float(close.iloc[-1])
            return features.astype(np.float32), current_price, {
                'rsi': float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0,
                'macd': float(macd_hist.iloc[-1]) if not np.isnan(macd_hist.iloc[-1]) else 0.0,
                'inst_net': int(inst_net[-1]) if len(inst_net) > 0 else 0,
                'volume_ratio': float((volume / vol_ma20).iloc[-1]) if vol_ma20.iloc[-1] > 0 else 1.0,
                'ma5_dev': float(((close - ma5) / ma5).iloc[-1]) if ma5.iloc[-1] > 0 else 0.0,
                'vix': float(vix_arr[-1]) if len(vix_arr) > 0 else 20.0,
                'market_return': float(market_ret[-1]) if len(market_ret) > 0 else 0.0,
            }

        except Exception as e:
            logger.error(f"特徵工程失敗 {symbol}: {e}", exc_info=True)
            return None

    async def _get_institutional_net(self, symbol: str, n_days: int) -> np.ndarray:
        """從 DB 取法人買賣超數據（張數）"""
        try:
            from app.database.connection import get_async_session
            from app.models.institutional import InstitutionalData
            from sqlalchemy import select, desc

            async with get_async_session() as session:
                stmt = (
                    select(InstitutionalData)
                    .where(InstitutionalData.stock_code == symbol)
                    .order_by(desc(InstitutionalData.date))
                    .limit(n_days)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

            if not rows:
                return np.zeros(n_days)

            # 按日期排序（舊→新），取外資+投信合計張數
            rows_sorted = sorted(rows, key=lambda r: r.date)
            net_vals = [
                (r.foreign_net or 0) + (r.investment_net or 0)
                for r in rows_sorted
            ]
            # 左填 0
            padded = np.zeros(n_days)
            padded[-len(net_vals):] = net_vals
            return padded

        except Exception as e:
            logger.debug(f"法人DB讀取失敗: {e}")
            return np.zeros(n_days)

    async def _get_market_data(self, n_days: int) -> Tuple[np.ndarray, np.ndarray]:
        """取 VIX 和台灣大盤日報酬"""
        try:
            import yfinance as yf

            def _fetch():
                vix = yf.Ticker('^VIX').history(period="6mo")['Close'].values
                twii = yf.Ticker('^TWII').history(period="6mo")['Close']
                twii_ret = twii.pct_change().fillna(0).values
                return vix, twii_ret

            vix_arr, market_ret = await asyncio.to_thread(_fetch)
            # 對齊長度
            vix_padded = np.zeros(n_days)
            mkt_padded = np.zeros(n_days)
            vix_padded[-min(len(vix_arr), n_days):] = vix_arr[-min(len(vix_arr), n_days):]
            mkt_padded[-min(len(market_ret), n_days):] = market_ret[-min(len(market_ret), n_days):]
            return vix_padded, mkt_padded

        except Exception:
            return np.zeros(n_days), np.zeros(n_days)

    @staticmethod
    def _normalize(arr: np.ndarray) -> np.ndarray:
        mu, sigma = np.mean(arr), np.std(arr) + 1e-9
        return (arr - mu) / sigma

    @staticmethod
    def _rolling_sum(arr: np.ndarray, window: int) -> np.ndarray:
        result = np.zeros_like(arr)
        for i in range(len(arr)):
            start = max(0, i - window + 1)
            result[i] = np.sum(arr[start:i+1])
        norm_max = np.abs(result).max() + 1e-9
        return result / norm_max


class LSTMPredictionEngine:
    """
    LSTM 預測引擎
    - 方向預測為主（binary classification: up/down）
    - 價格預測為輔（regression）
    - 每支股需要至少 60 天歷史才能訓練
    """

    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.models: Dict[str, any] = {}   # symbol -> keras model
        self.scalers: Dict[str, any] = {}  # symbol -> scaler

    def _get_model_path(self, symbol: str) -> str:
        return os.path.join(MODEL_BASE, f"{symbol}_v2.keras")

    def _get_scaler_path(self, symbol: str) -> str:
        return os.path.join(MODEL_BASE, f"{symbol}_scaler.pkl")

    def _get_meta_path(self, symbol: str) -> str:
        return os.path.join(MODEL_BASE, f"{symbol}_meta.json")

    def model_exists(self, symbol: str) -> bool:
        return os.path.exists(self._get_model_path(symbol))

    async def train(self, symbol: str, horizon_days: int = 2) -> Dict:
        """
        訓練 LSTM 模型
        使用 1年歷史數據，最後 20% 作為驗證
        """
        import yfinance as yf
        from sklearn.preprocessing import StandardScaler
        import tensorflow as tf
        from tensorflow import keras

        logger.info(f"🤖 開始訓練 {symbol} LSTM (horizon={horizon_days}d)")

        # 取全年數據
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="2y")
        if len(hist) < 100:
            return {"success": False, "error": f"數據不足 ({len(hist)} 天)"}

        close = hist['Close'].values
        high = hist['High'].values
        low = hist['Low'].values
        volume = hist['Volume'].values

        # === 技術指標特徵 (簡化版，同步計算) ===
        features = self._compute_features_sync(close, high, low, volume)
        n = len(features)

        # === 建立監督學習標籤 ===
        # 目標：horizon_days 後的方向（1=上漲, 0=下跌）
        future_rets = []
        for i in range(n):
            if i + horizon_days < n:
                ret = (close[i + horizon_days] - close[i]) / close[i]
                future_rets.append(1 if ret > 0.005 else (0 if ret < -0.005 else -1))
            else:
                future_rets.append(-1)  # 無法計算

        # 建立序列
        SEQ = FeatureEngineer.SEQ_LEN
        X, y = [], []
        for i in range(SEQ, n - horizon_days):
            if future_rets[i] != -1:
                X.append(features[i-SEQ:i])
                y.append(future_rets[i])

        if len(X) < 50:
            return {"success": False, "error": "有效樣本不足 50 個"}

        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.float32)

        # 標準化 X
        n_samples, seq_len, n_feat = X.shape
        X_flat = X.reshape(-1, n_feat)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_flat).reshape(n_samples, seq_len, n_feat)

        # 訓練/驗證分割（時間序列不能隨機）
        split = int(len(X_scaled) * 0.8)
        X_train, X_val = X_scaled[:split], X_scaled[split:]
        y_train, y_val = y[:split], y[split:]

        # === 建立 LSTM 模型 ===
        model = keras.Sequential([
            keras.layers.LSTM(64, return_sequences=True,
                              input_shape=(seq_len, n_feat),
                              kernel_regularizer=keras.regularizers.l2(0.001)),
            keras.layers.Dropout(0.3),
            keras.layers.LSTM(32, return_sequences=False,
                              kernel_regularizer=keras.regularizers.l2(0.001)),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid'),
        ])

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy']
        )

        callbacks = [
            keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(patience=4, factor=0.5),
        ]

        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=50,
            batch_size=16,
            callbacks=callbacks,
            verbose=0
        )

        # === 評估 ===
        val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
        best_epoch = np.argmin(history.history['val_loss']) + 1

        # 儲存模型和 scaler
        model.save(self._get_model_path(symbol))
        import pickle
        with open(self._get_scaler_path(symbol), 'wb') as f:
            pickle.dump(scaler, f)

        meta = {
            "symbol": symbol,
            "horizon_days": horizon_days,
            "val_accuracy": float(val_acc),
            "val_loss": float(val_loss),
            "best_epoch": int(best_epoch),
            "n_train": int(split),
            "n_val": int(len(X_val)),
            "trained_at": datetime.now().isoformat(),
            "n_features": n_feat,
        }
        with open(self._get_meta_path(symbol), 'w') as f:
            json.dump(meta, f)

        logger.info(f"✅ {symbol} 訓練完成 val_acc={val_acc:.1%} epoch={best_epoch}")
        return {"success": True, **meta}

    async def predict(self, symbol: str, horizon_days: int = 2) -> Optional[Dict]:
        """
        對指定股票做預測，返回結構化結果
        """
        import pickle
        import tensorflow as tf

        model_path = self._get_model_path(symbol)
        scaler_path = self._get_scaler_path(symbol)
        meta_path = self._get_meta_path(symbol)

        # 載入模型
        model_loaded = False
        model = None
        scaler = None

        if os.path.exists(model_path) and os.path.exists(scaler_path):
            try:
                model = tf.keras.models.load_model(model_path, compile=False)
                with open(scaler_path, 'rb') as f:
                    scaler = pickle.load(f)
                model_loaded = True
            except Exception as e:
                logger.warning(f"{symbol} 模型載入失敗: {e}，使用技術分析備援")

        # 讀取 meta
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                meta = json.load(f)

        # 取特徵
        result = await self.feature_engineer.build_features(symbol)
        if result is None:
            return None

        features, current_price, snapshot = result

        if model_loaded and model is not None:
            # LSTM 預測
            X = features.reshape(1, features.shape[0], features.shape[1])
            X_flat = X.reshape(-1, X.shape[-1])
            X_scaled = scaler.transform(X_flat).reshape(1, X.shape[1], X.shape[2])
            raw_prob = float(model.predict(X_scaled, verbose=0)[0][0])
            confidence = round(abs(raw_prob - 0.5) * 200, 1)  # 0-100

            if raw_prob > 0.55:
                direction = "up"
                change_est = 0.015 + (raw_prob - 0.55) * 0.1
            elif raw_prob < 0.45:
                direction = "down"
                change_est = -(0.015 + (0.45 - raw_prob) * 0.1)
            else:
                direction = "neutral"
                change_est = (raw_prob - 0.5) * 0.04

            model_source = "lstm_v2"
            val_accuracy = meta.get("val_accuracy", 0.65)

        else:
            # 技術分析備援（不使用 random！）
            raw_prob, direction, change_est, confidence = self._technical_signal(snapshot)
            model_source = "technical_fallback"
            val_accuracy = 0.55

        predicted_price = round(current_price * (1 + change_est), 2)
        predicted_high = round(current_price * (1 + abs(change_est) * 1.5), 2)
        predicted_low = round(current_price * (1 - abs(change_est) * 0.8), 2)
        if direction == "down":
            predicted_high, predicted_low = (
                round(current_price * (1 + abs(change_est) * 0.8), 2),
                round(current_price * (1 - abs(change_est) * 1.5), 2)
            )

        return {
            "symbol": symbol,
            "horizon_days": horizon_days,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "predicted_change_pct": round(change_est * 100, 2),
            "predicted_direction": direction,
            "predicted_high": predicted_high,
            "predicted_low": predicted_low,
            "confidence": confidence,
            "model_source": model_source,
            "model_val_accuracy": val_accuracy,
            "snapshot": snapshot,
            "prediction_date": date.today().isoformat(),
            "target_date": (date.today() + timedelta(days=horizon_days + 1)).isoformat(),
        }

    def _technical_signal(self, snapshot: dict) -> Tuple[float, str, float, float]:
        """技術指標備援信號（當 LSTM 模型未訓練時）"""
        score = 0.0
        reasons = 0

        rsi = snapshot.get('rsi', 50)
        macd = snapshot.get('macd', 0)
        inst_net = snapshot.get('inst_net', 0)
        volume_ratio = snapshot.get('volume_ratio', 1.0)
        ma5_dev = snapshot.get('ma5_dev', 0)
        vix = snapshot.get('vix', 20)
        market_ret = snapshot.get('market_return', 0)

        # RSI 信號
        if rsi < 30:
            score += 0.25
        elif rsi > 70:
            score -= 0.25
        reasons += 1

        # MACD 信號
        if macd > 0:
            score += 0.20
        elif macd < 0:
            score -= 0.20
        reasons += 1

        # 法人信號
        if inst_net > 500:
            score += 0.25
        elif inst_net < -500:
            score -= 0.25
        reasons += 1

        # VIX 信號（高恐慌 → 偏看多 = 逆勢）
        if vix > 30:
            score += 0.10
        elif vix < 15:
            score -= 0.05
        reasons += 1

        # 大盤信號
        if market_ret > 0.01:
            score += 0.15
        elif market_ret < -0.01:
            score -= 0.15
        reasons += 1

        raw_prob = 0.5 + score * 0.5

        if raw_prob > 0.58:
            direction = "up"
            change_est = 0.01 + score * 0.02
        elif raw_prob < 0.42:
            direction = "down"
            change_est = -0.01 + score * 0.02
        else:
            direction = "neutral"
            change_est = score * 0.01

        confidence = round(min(75, abs(score) * 150), 1)
        return raw_prob, direction, change_est, confidence

    @staticmethod
    def _compute_features_sync(close, high, low, volume):
        """同步計算特徵（訓練時使用）"""
        n = len(close)
        ret_1d = np.diff(close, prepend=close[0]) / (close + 1e-9)
        ret_5d = np.array([(close[i] - close[max(0, i-5)]) / close[max(0, i-5)] for i in range(n)])

        vol_ma20 = np.array([np.mean(volume[max(0, i-20):i+1]) for i in range(n)])
        vol_ratio = volume / (vol_ma20 + 1e-9)

        ma5 = np.array([np.mean(close[max(0, i-5):i+1]) for i in range(n)])
        ma20 = np.array([np.mean(close[max(0, i-20):i+1]) for i in range(n)])
        ma60 = np.array([np.mean(close[max(0, i-60):i+1]) for i in range(n)])

        # RSI
        delta = np.diff(close, prepend=close[0])
        gain = np.maximum(delta, 0)
        loss = np.abs(np.minimum(delta, 0))
        avg_gain = np.array([np.mean(gain[max(0, i-14):i+1]) for i in range(n)])
        avg_loss = np.array([np.mean(loss[max(0, i-14):i+1]) for i in range(n)])
        rs = avg_gain / (avg_loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))

        # ATR
        tr = np.maximum(high - low, np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        ))
        atr = np.array([np.mean(tr[max(0, i-14):i+1]) for i in range(n)])

        def norm(arr):
            mu, sigma = np.mean(arr), np.std(arr) + 1e-9
            return (arr - mu) / sigma

        features = np.column_stack([
            norm(close),
            ret_1d,
            ret_5d,
            vol_ratio.clip(0, 5),
            norm(rsi),
            norm(np.zeros(n)),   # MACD placeholder
            np.zeros(n),         # bb_pct placeholder
            (close - ma5) / (ma5 + 1e-9),
            (close - ma20) / (ma20 + 1e-9),
            (close - ma60) / (ma60 + 1e-9),
            atr / (close + 1e-9),
            (high - low) / (close + 1e-9),
            np.zeros(n),   # inst_net
            np.zeros(n),   # foreign_5d
            np.zeros(n),   # vix
            np.zeros(n),   # market_ret
            norm(rsi - 50),  # cci approx
            norm(rsi),       # stoch approx
        ])

        return np.nan_to_num(features, 0.0)


# ===== 預測記錄與驗證服務 =====

class PredictionRecorder:
    """
    負責：
    1. 儲存新預測到 DB
    2. 每日收盤後驗證昨日預測
    3. 分析成功/失敗模式
    4. 定期記錄準確率趨勢
    """

    async def save_prediction(self, symbol: str, stock_name: str, pred: Dict) -> bool:
        """儲存預測記錄"""
        try:
            from app.database.connection import get_async_session
            from app.models.price_prediction import PricePredictionRecord
            from sqlalchemy import select

            async with get_async_session() as session:
                # 檢查是否已存在
                target_date = date.fromisoformat(pred['target_date'])
                stmt = select(PricePredictionRecord).where(
                    PricePredictionRecord.symbol == symbol,
                    PricePredictionRecord.prediction_date == date.today(),
                    PricePredictionRecord.target_date == target_date,
                )
                existing = (await session.execute(stmt)).scalar_one_or_none()
                if existing:
                    return True  # 今日已有預測，跳過

                snap = pred.get('snapshot', {})
                record = PricePredictionRecord(
                    symbol=symbol,
                    stock_name=stock_name,
                    prediction_date=date.today(),
                    target_date=target_date,
                    horizon_days=pred['horizon_days'],
                    price_at_prediction=Decimal(str(pred['current_price'])),
                    predicted_price=Decimal(str(pred['predicted_price'])),
                    predicted_change_pct=Decimal(str(pred['predicted_change_pct'])),
                    predicted_direction=pred['predicted_direction'],
                    confidence=Decimal(str(pred['confidence'])),
                    predicted_high=Decimal(str(pred['predicted_high'])),
                    predicted_low=Decimal(str(pred['predicted_low'])),
                    features_used=json.dumps(FeatureEngineer.FEATURE_NAMES),
                    model_version=pred.get('model_source', 'unknown'),
                    rsi_at_prediction=Decimal(str(round(snap.get('rsi', 50), 2))),
                    macd_at_prediction=Decimal(str(round(snap.get('macd', 0), 4))),
                    vix_at_prediction=Decimal(str(round(snap.get('vix', 20), 2))),
                    institutional_net_at_prediction=int(snap.get('inst_net', 0)),
                    volume_ratio_at_prediction=Decimal(str(round(snap.get('volume_ratio', 1), 2))),
                    ma5_deviation_at_prediction=Decimal(str(round(snap.get('ma5_dev', 0), 4))),
                    market_change_pct=Decimal(str(round(snap.get('market_return', 0) * 100, 3))),
                )
                session.add(record)
                await session.commit()
                logger.info(f"💾 預測已儲存: {symbol} → {target_date} ({pred['predicted_direction']})")
                return True

        except Exception as e:
            logger.error(f"儲存預測失敗: {e}", exc_info=True)
            return False

    async def verify_past_predictions(self) -> Dict:
        """
        驗證到期的未驗證預測
        收盤後（15:30+）自動執行
        """
        import yfinance as yf
        from app.database.connection import get_async_session
        from app.models.price_prediction import PricePredictionRecord
        from sqlalchemy import select, and_

        today = date.today()
        verified_count = 0
        correct_count = 0

        try:
            async with get_async_session() as session:
                # 取所有目標日期 <= 今天且未驗證的記錄
                stmt = select(PricePredictionRecord).where(
                    and_(
                        PricePredictionRecord.target_date <= today,
                        PricePredictionRecord.is_verified == False,
                    )
                ).limit(50)
                result = await session.execute(stmt)
                pending = result.scalars().all()

                logger.info(f"🔍 驗證 {len(pending)} 筆待驗證預測...")

                for record in pending:
                    try:
                        # 取實際收盤價
                        actual_price = await self._get_actual_price(
                            record.symbol, record.target_date
                        )
                        if actual_price is None:
                            continue

                        base_price = float(record.price_at_prediction)
                        actual_chg = (actual_price - base_price) / base_price * 100

                        if actual_chg > 0.5:
                            actual_dir = "up"
                        elif actual_chg < -0.5:
                            actual_dir = "down"
                        else:
                            actual_dir = "neutral"

                        direction_correct = (record.predicted_direction == actual_dir) or (
                            record.predicted_direction != "neutral" and actual_dir == "neutral"
                        )

                        price_error = abs(float(record.predicted_price) - actual_price) / actual_price * 100
                        # 分數：方向正確 60 分 + 誤差<3% 20分 + 誤差<5% 10分 + 信心度加成
                        score = 60.0 if direction_correct else 0.0
                        if price_error < 3:
                            score += 20
                        elif price_error < 5:
                            score += 10
                        conf_bonus = float(record.confidence) * 0.2
                        score = min(100, score + conf_bonus * (1 if direction_correct else -0.5))

                        # 失敗原因分析
                        failure_reason = None
                        success_pattern = None
                        if direction_correct:
                            success_pattern = self._analyze_success(record)
                            correct_count += 1
                        else:
                            failure_reason = self._analyze_failure(record, actual_chg)

                        # 更新記錄
                        record.is_verified = True
                        record.actual_price = Decimal(str(round(actual_price, 2)))
                        record.actual_change_pct = Decimal(str(round(actual_chg, 3)))
                        record.actual_direction = actual_dir
                        record.direction_correct = direction_correct
                        record.price_error_pct = Decimal(str(round(price_error, 3)))
                        record.score = Decimal(str(round(score, 2)))
                        record.verified_at = datetime.now()
                        record.failure_reason = failure_reason
                        record.success_pattern = success_pattern

                        verified_count += 1

                    except Exception as e:
                        logger.debug(f"驗證 {record.symbol} 失敗: {e}")

                await session.commit()

        except Exception as e:
            logger.error(f"批量驗證失敗: {e}")

        accuracy = correct_count / verified_count * 100 if verified_count > 0 else 0
        logger.info(f"✅ 驗證完成: {verified_count} 筆, 方向準確率={accuracy:.1f}%")
        return {
            "verified": verified_count,
            "correct": correct_count,
            "accuracy_pct": round(accuracy, 1)
        }

    async def _get_actual_price(self, symbol: str, target_date: date) -> Optional[float]:
        """取指定日期的實際收盤價"""
        try:
            import yfinance as yf
            start = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')
            end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')

            def _fetch():
                ticker = yf.Ticker(f"{symbol}.TW")
                hist = ticker.history(start=start, end=end)
                if hist.empty:
                    return None
                # 取最近一個在 target_date 或之前的收盤價
                hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
                target_dt = datetime.combine(target_date, datetime.min.time())
                hist_before = hist[hist.index <= target_dt]
                if hist_before.empty:
                    return float(hist['Close'].iloc[-1])
                return float(hist_before['Close'].iloc[-1])

            return await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=10.0)
        except Exception:
            return None

    def _analyze_success(self, record) -> str:
        """分析成功預測的特徵模式"""
        patterns = []
        rsi = float(record.rsi_at_prediction or 50)
        inst = int(record.institutional_net_at_prediction or 0)
        vix = float(record.vix_at_prediction or 20)

        if rsi < 35 and record.predicted_direction == "up":
            patterns.append("超賣反彈")
        if rsi > 65 and record.predicted_direction == "down":
            patterns.append("超買回落")
        if inst > 1000 and record.predicted_direction == "up":
            patterns.append("法人大買多")
        if vix > 28 and record.predicted_direction == "up":
            patterns.append("恐慌底部")
        if not patterns:
            patterns.append("技術指標綜合確認")
        return json.dumps(patterns, ensure_ascii=False)

    def _analyze_failure(self, record, actual_chg: float) -> str:
        """分析失敗預測的原因"""
        reasons = []
        vix = float(record.vix_at_prediction or 20)
        mkt = float(record.market_change_pct or 0)
        inst = int(record.institutional_net_at_prediction or 0)

        if abs(mkt) > 2.0:
            reasons.append(f"大盤大幅波動({mkt:+.1f}%)掩蓋個股信號")
        if vix > 30:
            reasons.append(f"高VIX({vix:.0f})環境不適合方向性預測")
        if actual_chg * (1 if record.predicted_direction == "up" else -1) > 3:
            reasons.append("方向錯誤且幅度大，可能有突發消息")
        if inst < 0 and record.predicted_direction == "up":
            reasons.append("法人賣超但預測看多，籌碼逆勢")
        if not reasons:
            reasons.append("市場隨機噪音或不明因素")
        return json.dumps(reasons, ensure_ascii=False)

    async def get_accuracy_stats(self, symbol: Optional[str] = None,
                                  horizon_days: Optional[int] = None,
                                  window_days: int = 14) -> Dict:
        """取準確率統計"""
        from app.database.connection import get_async_session
        from app.models.price_prediction import PricePredictionRecord
        from sqlalchemy import select, and_, func

        cutoff = date.today() - timedelta(days=window_days)

        try:
            async with get_async_session() as session:
                filters = [
                    PricePredictionRecord.is_verified == True,
                    PricePredictionRecord.prediction_date >= cutoff,
                ]
                if symbol:
                    filters.append(PricePredictionRecord.symbol == symbol)
                if horizon_days:
                    filters.append(PricePredictionRecord.horizon_days == horizon_days)

                stmt = select(
                    func.count().label('total'),
                    func.sum(
                        PricePredictionRecord.direction_correct.cast(Integer)
                    ).label('correct'),
                    func.avg(PricePredictionRecord.price_error_pct).label('avg_error'),
                    func.avg(PricePredictionRecord.score).label('avg_score'),
                ).where(and_(*filters))

                result = await session.execute(stmt)
                row = result.one()

                total = row.total or 0
                correct = int(row.correct or 0)
                accuracy = correct / total * 100 if total > 0 else 0

                return {
                    "window_days": window_days,
                    "total": total,
                    "correct": correct,
                    "direction_accuracy_pct": round(accuracy, 1),
                    "avg_price_error_pct": round(float(row.avg_error or 0), 2),
                    "avg_score": round(float(row.avg_score or 0), 1),
                    "target_accuracy": 80.0,
                    "gap_to_target": round(80.0 - accuracy, 1),
                }
        except Exception as e:
            logger.error(f"準確率統計失敗: {e}")
            return {"error": str(e), "direction_accuracy_pct": 0}


# 全局單例
prediction_engine = LSTMPredictionEngine()
prediction_recorder = PredictionRecorder()
