"""
LSTM 模式分類器
Order Flow Pattern Classifier using Hybrid LSTM Architecture

混合架構：
- Bidirectional LSTM: 捕獲時間依賴
- Conv1D: 捕獲局部模式
- Attention: 關注重要時間點
- Dense layers with regularization

替代傳統 LSTM 價格預測，改為進行市場模式分類
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# 嘗試導入 TensorFlow
try:
    import tensorflow as tf
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import (
        Input, LSTM, Bidirectional, Dense, Dropout,
        BatchNormalization, Concatenate, Conv1D,
        GlobalAveragePooling1D, GlobalMaxPooling1D,
        Attention, MultiHeadAttention, LayerNormalization
    )
    from tensorflow.keras.regularizers import l2
    from tensorflow.keras.callbacks import (
        EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, TensorBoard
    )
    from tensorflow.keras.optimizers import Adam
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("⚠️ TensorFlow 未安裝，LSTM 模式分類器將無法使用")


@dataclass
class ModelConfig:
    """模型配置"""
    # 輸入形狀
    sequence_length: int = 100
    num_features: int = 14
    num_aux_features: int = 5
    num_classes: int = 7  # 6種模式 + 中性
    
    # LSTM 配置
    lstm_units: int = 64
    lstm_dropout: float = 0.3
    lstm_recurrent_dropout: float = 0.2
    
    # Conv1D 配置
    conv_filters: int = 32
    conv_kernel_size: int = 5
    
    # Dense 配置
    dense_units: List[int] = field(default_factory=lambda: [128, 64])
    dense_dropout: float = 0.4
    
    # 正則化
    l2_reg: float = 0.01
    
    # 訓練配置
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    patience: int = 15
    
    # 多標籤 vs 單標籤
    multi_label: bool = False  # True: sigmoid, False: softmax


class FocalLoss(tf.keras.losses.Loss):
    """
    Focal Loss for handling class imbalance
    
    用於處理模式分類中的類別不平衡問題
    """
    def __init__(self, gamma: float = 2.0, alpha: float = 0.25, **kwargs):
        super().__init__(**kwargs)
        self.gamma = gamma
        self.alpha = alpha
    
    def call(self, y_true, y_pred):
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)
        
        # 計算 focal weight
        pt = tf.where(tf.equal(y_true, 1), y_pred, 1 - y_pred)
        alpha_t = tf.where(tf.equal(y_true, 1), self.alpha, 1 - self.alpha)
        
        focal_weight = alpha_t * tf.pow(1.0 - pt, self.gamma)
        
        # 計算交叉熵
        ce = -y_true * tf.math.log(y_pred) - (1 - y_true) * tf.math.log(1 - y_pred)
        
        return tf.reduce_mean(focal_weight * ce)


class OrderFlowPatternClassifier:
    """
    訂單流模式分類器
    
    使用混合 LSTM 架構進行市場微觀模式識別
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow 未安裝，請執行: pip install tensorflow")
        
        self.config = config or ModelConfig()
        self.model: Optional[Model] = None
        self.history = None
        self._is_compiled = False
    
    def build_model(self) -> Model:
        """構建混合模型架構"""
        config = self.config
        
        # ===== 主輸入：訂單流時間序列 =====
        sequence_input = Input(
            shape=(config.sequence_length, config.num_features),
            name='order_flow_sequence'
        )
        
        # ===== 輔助輸入：技術指標（非時間序列）=====
        auxiliary_input = Input(
            shape=(config.num_aux_features,),
            name='auxiliary_features'
        )
        
        # ===== 分支1：雙向 LSTM =====
        lstm_out = Bidirectional(
            LSTM(
                config.lstm_units,
                return_sequences=True,
                dropout=config.lstm_dropout,
                recurrent_dropout=config.lstm_recurrent_dropout,
                kernel_regularizer=l2(config.l2_reg)
            ),
            name='bidirectional_lstm'
        )(sequence_input)
        
        lstm_out = BatchNormalization()(lstm_out)
        lstm_out = Dropout(config.lstm_dropout)(lstm_out)
        
        # Self-Attention
        attention_output = Attention(name='self_attention')([lstm_out, lstm_out])
        
        # 第二層 LSTM（可選，用於更深的時間依賴）
        lstm_out2 = LSTM(
            config.lstm_units // 2,
            return_sequences=False,
            kernel_regularizer=l2(config.l2_reg)
        )(attention_output)
        
        # ===== 分支2：Conv1D 捕獲局部模式 =====
        conv_out = Conv1D(
            filters=config.conv_filters,
            kernel_size=config.conv_kernel_size,
            activation='relu',
            padding='same',
            kernel_regularizer=l2(config.l2_reg)
        )(sequence_input)
        conv_out = BatchNormalization()(conv_out)
        conv_out = Dropout(0.2)(conv_out)
        
        conv_out = Conv1D(
            filters=config.conv_filters // 2,
            kernel_size=3,
            activation='relu',
            padding='same'
        )(conv_out)
        
        # 池化
        conv_avg = GlobalAveragePooling1D()(conv_out)
        conv_max = GlobalMaxPooling1D()(conv_out)
        conv_pooled = Concatenate()([conv_avg, conv_max])
        
        # ===== 合併所有特徵 =====
        merged = Concatenate()([lstm_out2, conv_pooled, auxiliary_input])
        
        # ===== 全連接層 =====
        x = merged
        for i, units in enumerate(config.dense_units):
            x = Dense(
                units,
                activation='relu',
                kernel_regularizer=l2(config.l2_reg / 2),
                name=f'dense_{i}'
            )(x)
            x = BatchNormalization()(x)
            x = Dropout(config.dense_dropout)(x)
        
        # ===== 輸出層 =====
        if config.multi_label:
            # 多標籤分類（一個樣本可能屬於多個模式）
            output = Dense(
                config.num_classes,
                activation='sigmoid',
                name='pattern_prediction'
            )(x)
        else:
            # 單標籤分類
            output = Dense(
                config.num_classes,
                activation='softmax',
                name='pattern_prediction'
            )(x)
        
        # 構建模型
        self.model = Model(
            inputs=[sequence_input, auxiliary_input],
            outputs=output,
            name='OrderFlowPatternClassifier'
        )
        
        logger.info(f"✅ 模型構建完成, 參數量: {self.model.count_params():,}")
        
        return self.model
    
    def compile_model(
        self,
        use_focal_loss: bool = True,
        focal_gamma: float = 2.0,
        focal_alpha: float = 0.25,
    ):
        """編譯模型"""
        if self.model is None:
            self.build_model()
        
        # 選擇損失函數
        if use_focal_loss and self.config.multi_label:
            loss = FocalLoss(gamma=focal_gamma, alpha=focal_alpha)
        elif self.config.multi_label:
            loss = 'binary_crossentropy'
        else:
            loss = 'sparse_categorical_crossentropy'
        
        # 選擇指標
        if self.config.multi_label:
            metrics = [
                tf.keras.metrics.Precision(name='precision'),
                tf.keras.metrics.Recall(name='recall'),
                tf.keras.metrics.AUC(name='auc'),
            ]
        else:
            metrics = [
                'accuracy',
                tf.keras.metrics.SparseCategoricalAccuracy(name='sparse_acc'),
            ]
        
        self.model.compile(
            optimizer=Adam(learning_rate=self.config.learning_rate),
            loss=loss,
            metrics=metrics,
        )
        
        self._is_compiled = True
        logger.info("✅ 模型編譯完成")
    
    def train(
        self,
        X_seq: np.ndarray,
        X_aux: np.ndarray,
        y: np.ndarray,
        validation_split: float = 0.2,
        class_weights: Optional[Dict[int, float]] = None,
        callbacks: Optional[List] = None,
        verbose: int = 1,
    ) -> Dict[str, Any]:
        """
        訓練模型
        
        Args:
            X_seq: 序列特徵 (samples, sequence_length, features)
            X_aux: 輔助特徵 (samples, aux_features)
            y: 標籤
            validation_split: 驗證集比例
            class_weights: 類別權重
            callbacks: 回調函數
            verbose: 詳細程度
        
        Returns:
            訓練歷史
        """
        if not self._is_compiled:
            self.compile_model()
        
        # 預設回調
        if callbacks is None:
            callbacks = self._get_default_callbacks()
        
        logger.info(f"🚀 開始訓練...")
        logger.info(f"   訓練樣本: {len(X_seq)}")
        logger.info(f"   序列長度: {X_seq.shape[1]}")
        logger.info(f"   特徵數: {X_seq.shape[2]}")
        
        self.history = self.model.fit(
            [X_seq, X_aux],
            y,
            validation_split=validation_split,
            epochs=self.config.epochs,
            batch_size=self.config.batch_size,
            callbacks=callbacks,
            class_weight=class_weights,
            verbose=verbose,
        )
        
        logger.info("✅ 訓練完成")
        
        return {
            "history": self.history.history,
            "epochs_trained": len(self.history.history['loss']),
            "final_loss": self.history.history['loss'][-1],
            "final_val_loss": self.history.history.get('val_loss', [None])[-1],
        }
    
    def _get_default_callbacks(self) -> List:
        """獲取預設回調函數"""
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=self.config.patience,
                restore_best_weights=True,
                verbose=1,
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=7,
                min_lr=1e-6,
                verbose=1,
            ),
        ]
        return callbacks
    
    def predict(
        self,
        X_seq: np.ndarray,
        X_aux: np.ndarray,
    ) -> np.ndarray:
        """預測"""
        if self.model is None:
            raise ValueError("模型未訓練")
        
        return self.model.predict([X_seq, X_aux], verbose=0)
    
    def predict_classes(
        self,
        X_seq: np.ndarray,
        X_aux: np.ndarray,
        threshold: float = 0.5,
    ) -> np.ndarray:
        """預測類別"""
        probs = self.predict(X_seq, X_aux)
        
        if self.config.multi_label:
            return (probs > threshold).astype(int)
        else:
            return np.argmax(probs, axis=1)
    
    def evaluate(
        self,
        X_seq: np.ndarray,
        X_aux: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, float]:
        """評估模型"""
        if self.model is None:
            raise ValueError("模型未訓練")
        
        results = self.model.evaluate([X_seq, X_aux], y, verbose=0)
        
        metrics = {}
        for name, value in zip(self.model.metrics_names, results):
            metrics[name] = float(value)
        
        return metrics
    
    def save(self, filepath: str):
        """保存模型"""
        if self.model is None:
            raise ValueError("模型未訓練")
        
        self.model.save(filepath)
        logger.info(f"✅ 模型已保存到 {filepath}")
    
    def load(self, filepath: str):
        """載入模型"""
        self.model = tf.keras.models.load_model(
            filepath,
            custom_objects={'FocalLoss': FocalLoss}
        )
        self._is_compiled = True
        logger.info(f"✅ 模型已從 {filepath} 載入")
    
    def summary(self):
        """顯示模型摘要"""
        if self.model is not None:
            self.model.summary()


# ==================== 簡化版分類器（不需要輔助輸入）====================

class SimplePatternClassifier:
    """
    簡化版模式分類器
    
    只需要序列輸入，適合快速原型開發
    """
    
    def __init__(
        self,
        sequence_length: int = 100,
        num_features: int = 14,
        num_classes: int = 7,
        lstm_units: int = 64,
    ):
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow 未安裝")
        
        self.sequence_length = sequence_length
        self.num_features = num_features
        self.num_classes = num_classes
        self.lstm_units = lstm_units
        self.model = None
    
    def build_and_compile(self):
        """構建並編譯模型"""
        inputs = Input(shape=(self.sequence_length, self.num_features))
        
        x = LSTM(self.lstm_units, return_sequences=True)(inputs)
        x = Dropout(0.3)(x)
        x = LSTM(self.lstm_units // 2)(x)
        x = Dropout(0.3)(x)
        x = Dense(64, activation='relu')(x)
        x = Dropout(0.3)(x)
        outputs = Dense(self.num_classes, activation='softmax')(x)
        
        self.model = Model(inputs, outputs)
        self.model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return self.model
    
    def train(self, X, y, epochs=50, batch_size=32, validation_split=0.2):
        if self.model is None:
            self.build_and_compile()
        
        return self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[EarlyStopping(patience=10, restore_best_weights=True)],
            verbose=1,
        )
    
    def predict(self, X):
        return self.model.predict(X, verbose=0)
    
    def predict_classes(self, X):
        return np.argmax(self.predict(X), axis=1)
