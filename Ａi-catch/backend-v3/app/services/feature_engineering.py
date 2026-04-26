"""
特徵工程引擎
從原始訊號提取機器學習特徵
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ============================================================
# 🚀 RandomForest 特徵重要性篩選
# ============================================================

def get_refined_features(df: pd.DataFrame, labels: pd.Series, top_n: int = 12) -> List[str]:
    """
    用 RandomForest 評估每個特徵的貢獻度，回傳最重要的前 top_n 個特徵名稱。

    Args:
        df:     原始特徵 DataFrame（行=樣本, 列=特徵）
        labels: 漲跌標籤 Series（0/1 或多分類）
        top_n:  要保留的最大特徵數

    Returns:
        特徵名稱清單（依重要性由高至低排序）
    """
    if df.empty or len(df) < 10:
        logger.warning("⚠️ [特徵篩選] 樣本數不足 10 筆，跳過自動篩選，回傳全部特徵")
        return df.columns.tolist()

    try:
        from sklearn.ensemble import RandomForestClassifier

        model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(df, labels)

        importances = pd.Series(model.feature_importances_, index=df.columns)
        # 最多保留 top_n，但不超過實際特徵數
        top_n = min(top_n, len(df.columns))
        top_features = importances.nlargest(top_n).index.tolist()

        logger.info(f"🚀 [AI 診斷] 偵測到當前環境下最強的 {top_n} 個特徵：")
        for i, feat in enumerate(top_features):
            logger.info(f"  {i+1:>2}. {feat:<30} 貢獻度: {importances[feat]:.4f}")

        # 額外印出「被剔除」的特徵，方便偵錯
        dropped = importances.nsmallest(len(df.columns) - top_n).index.tolist()
        if dropped:
            logger.info(f"  ℹ️  已剔除貢獻度低的 {len(dropped)} 個特徵: {dropped}")

        return top_features

    except ImportError:
        logger.warning("⚠️ scikit-learn 未安裝，跳過特徵篩選")
        return df.columns.tolist()
    except Exception as e:
        logger.error(f"❌ 特徵篩選失敗: {e}")
        return df.columns.tolist()


# ============================================================
# 特徵工程引擎
# ============================================================

class FeatureEngineer:
    """特徵工程引擎"""

    def __init__(self):
        self.feature_names: List[str] = []
        # 上次 select_top_features() 篩選後保留的特徵清單
        self.selected_features: Optional[List[str]] = None

    def extract_features(self, signal_data: Dict) -> np.ndarray:
        """從原始訊號提取特徵"""

        features = {}

        # === 1. 基礎特徵 ===
        features['vwap_deviation'] = signal_data.get('vwap_deviation', 0)
        features['kd_k'] = signal_data.get('kd_k', 50)
        features['kd_d'] = signal_data.get('kd_d', 50)
        features['ofi'] = signal_data.get('ofi', 0)

        # === 2. KD 衍生特徵 ===
        kd_k = features['kd_k']
        kd_d = features['kd_d']

        features['kd_diff'] = kd_k - kd_d
        features['kd_avg'] = (kd_k + kd_d) / 2
        features['kd_is_overbought'] = 1 if kd_k > 80 else 0
        features['kd_is_oversold'] = 1 if kd_k < 20 else 0
        features['kd_golden_cross'] = 1 if (kd_k > kd_d and kd_k < 50) else 0

        # === 3. VWAP 衍生特徵 ===
        vwap_dev = features['vwap_deviation']

        features['vwap_dev_squared'] = vwap_dev ** 2
        features['vwap_dev_category'] = self._categorize_vwap_dev(vwap_dev)
        features['price_above_vwap'] = 1 if vwap_dev > 0 else 0

        # === 4. OFI 衍生特徵 ===
        ofi = features['ofi']

        features['ofi_abs'] = abs(ofi)
        features['ofi_category'] = self._categorize_ofi(ofi)
        features['ofi_is_strong_buy'] = 1 if ofi > 50 else 0
        features['ofi_is_strong_sell'] = 1 if ofi < -50 else 0

        # === 5. 交互特徵 ===
        features['vwap_ofi_interaction'] = vwap_dev * ofi / 100 if ofi != 0 else 0
        features['kd_vwap_interaction'] = kd_k * vwap_dev / 100 if vwap_dev != 0 else 0

        # === 6. 組合風險分數 ===
        risk_score = 0
        if vwap_dev >= 30:
            risk_score += 3
        elif vwap_dev >= 20:
            risk_score += 2
        elif vwap_dev >= 10:
            risk_score += 1

        if kd_k > 90:
            risk_score += 3
        elif kd_k > 85:
            risk_score += 2
        elif kd_k > 80:
            risk_score += 1

        if ofi < -50:
            risk_score += 3
        elif ofi < -10:
            risk_score += 2
        elif ofi < 0:
            risk_score += 1

        features['combined_risk_score'] = risk_score

        # === 7. 時間特徵 ===
        if 'timestamp' in signal_data and signal_data['timestamp']:
            ts = signal_data['timestamp']
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            features['hour'] = ts.hour
            features['minute'] = ts.minute
            features['is_opening'] = 1 if ts.hour == 9 and ts.minute < 30 else 0
            features['is_closing'] = 1 if ts.hour == 13 and ts.minute > 20 else 0
            features['is_morning'] = 1 if ts.hour < 12 else 0
        else:
            features['hour'] = 10
            features['minute'] = 0
            features['is_opening'] = 0
            features['is_closing'] = 0
            features['is_morning'] = 1

        # === 8. 量價特徵 ===
        volume_trend = signal_data.get('volume_trend', '')
        price_trend = signal_data.get('price_trend', '')
        features['volume_price_sync'] = self._encode_volume_price(volume_trend, price_trend)

        # 記錄特徵名稱（固定排序）
        self.feature_names = sorted(features.keys())

        # 轉換為 numpy array
        feature_vector = np.array([features[name] for name in self.feature_names])

        return feature_vector

    # ----------------------------------------------------------
    # 🚀 特徵篩選入口（整合 get_refined_features）
    # ----------------------------------------------------------

    def select_top_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        top_n: int = 12,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        使用 RandomForest 篩選貢獻度最高的前 top_n 個特徵。

        Args:
            X:     全特徵 DataFrame
            y:     標籤 Series
            top_n: 保留特徵數（預設 12）

        Returns:
            (篩選後的 DataFrame, 選出的特徵名稱清單)
        """
        selected = get_refined_features(X, y, top_n=top_n)
        self.selected_features = selected
        return X[selected], selected

    # ----------------------------------------------------------
    # 原有分類輔助方法
    # ----------------------------------------------------------

    def _categorize_vwap_dev(self, deviation: float) -> int:
        """VWAP 乖離分類"""
        if deviation < -20:
            return 0
        elif deviation < -10:
            return 1
        elif deviation < 0:
            return 2
        elif deviation < 10:
            return 3
        elif deviation < 20:
            return 4
        elif deviation < 30:
            return 5
        else:
            return 6

    def _categorize_ofi(self, ofi: float) -> int:
        """OFI 分類"""
        if ofi < -100:
            return 0
        elif ofi < -50:
            return 1
        elif ofi < -10:
            return 2
        elif ofi < 0:
            return 3
        elif ofi < 10:
            return 4
        elif ofi < 50:
            return 5
        else:
            return 6

    def _encode_volume_price(self, volume_trend: str, price_trend: str) -> int:
        """編碼量價關係"""
        mapping = {
            ('增', '漲'): 3,    # 價漲量增 - 最健康
            ('增', '跌'): -3,   # 價跌量增 - 出貨
            ('縮', '漲'): 1,    # 價漲量縮 - 可能假突破
            ('縮', '跌'): -1,   # 價跌量縮 - 可能止跌
            ('平', '漲'): 2,
            ('平', '跌'): -2,
            ('增', '平'): 0,
            ('縮', '平'): 0,
            ('平', '平'): 0
        }
        return mapping.get((volume_trend, price_trend), 0)

    # ----------------------------------------------------------
    # 訓練資料集產生（支援自動特徵篩選）
    # ----------------------------------------------------------

    def create_training_dataset(
        self,
        signals: List[Dict],
        auto_select_features: bool = False,
        top_n: int = 12,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        從歷史訊號創建訓練數據集。

        Args:
            signals:               訊號清單（每筆需含 virtual_pnl_percent）
            auto_select_features:  若 True 且樣本 >= 30，自動用 RF 篩選前 top_n 個特徵
            top_n:                 auto_select_features 時保留的特徵數

        Returns:
            (X: DataFrame, y: Series)
        """
        X_list = []
        y_list = []

        for signal in signals:
            if signal.get('virtual_pnl_percent') is None:
                continue

            # 提取特徵
            signal_data = {
                'stock_code': signal.get('stock_code'),
                'current_price': signal.get('price_at_reject'),
                'vwap': signal.get('vwap'),
                'vwap_deviation': signal.get('vwap_deviation', 0),
                'kd_k': signal.get('kd_k', 50),
                'kd_d': signal.get('kd_d', 50),
                'ofi': signal.get('ofi', 0),
                'volume_trend': signal.get('volume_trend', ''),
                'price_trend': signal.get('price_trend', ''),
                'timestamp': signal.get('reject_time'),
            }

            features = self.extract_features(signal_data)
            X_list.append(features)

            # 標籤：是否應該進場（虛擬損益為正視為成功）
            y_list.append(1 if signal.get('virtual_pnl_percent', 0) > 0 else 0)

        if not X_list:
            return pd.DataFrame(), pd.Series()

        X = pd.DataFrame(X_list, columns=self.feature_names)
        y = pd.Series(y_list, name='should_enter')

        # 若啟用自動特徵篩選且樣本夠多
        if auto_select_features and len(X) >= 30:
            logger.info(f"🔍 [特徵篩選] 共 {len(X)} 筆樣本，開始 RF 自動篩選...")
            X, _ = self.select_top_features(X, y, top_n=top_n)
        elif auto_select_features:
            logger.warning(
                f"⚠️ [特徵篩選] 樣本數 {len(X)} < 30，跳過自動篩選（使用全部 {len(self.feature_names)} 個特徵）"
            )

        return X, y


# 全局實例
feature_engineer = FeatureEngineer()
