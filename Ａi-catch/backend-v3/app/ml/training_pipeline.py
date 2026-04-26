"""
模型訓練管道
Model Training Pipeline

完整的訓練流程：
1. 資料載入與預處理
2. 特徵工程
3. 模型訓練
4. 評估與驗證
5. 模型保存
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """訓練配置"""
    # 資料配置
    data_source: str = "api"  # "api", "csv", "database"
    train_symbols: List[str] = None
    train_start_date: Optional[str] = None
    train_end_date: Optional[str] = None
    
    # 資料集配置
    sequence_length: int = 100
    prediction_horizon_sec: int = 10
    train_split: float = 0.7
    val_split: float = 0.15
    
    # 模型選擇
    model_type: str = "lstm"  # "lstm", "xgboost", "ensemble"
    
    # 訓練配置
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    patience: int = 15
    
    # 保存配置
    model_dir: str = "models"
    save_best_only: bool = True
    
    def __post_init__(self):
        if self.train_symbols is None:
            self.train_symbols = ["2330", "2454", "2317"]


class TrainingPipeline:
    """
    模型訓練管道
    
    提供端到端的模型訓練流程
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.results: Dict[str, Any] = {}
        self._models = {}
    
    def run(
        self,
        X_seq: np.ndarray,
        X_aux: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        執行完整訓練流程
        
        Args:
            X_seq: 序列特徵
            X_aux: 輔助特徵
            y: 標籤
            feature_names: 特徵名稱
        
        Returns:
            訓練結果
        """
        logger.info("=" * 60)
        logger.info("🚀 開始模型訓練管道")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. 資料分割
        logger.info("\n📊 Step 1: 資料分割")
        splits = self._split_data(X_seq, X_aux, y)
        
        # 2. 訓練模型
        logger.info(f"\n🤖 Step 2: 訓練 {self.config.model_type} 模型")
        model_results = self._train_model(splits, feature_names)
        
        # 3. 評估模型
        logger.info("\n📈 Step 3: 評估模型")
        eval_results = self._evaluate_model(splits)
        
        # 4. 保存模型
        logger.info("\n💾 Step 4: 保存模型")
        save_path = self._save_model()
        
        # 彙總結果
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.results = {
            "config": asdict(self.config),
            "data_info": {
                "total_samples": len(y),
                "train_samples": len(splits["train_y"]),
                "val_samples": len(splits["val_y"]),
                "test_samples": len(splits["test_y"]),
                "sequence_length": X_seq.shape[1],
                "num_features": X_seq.shape[2],
            },
            "training": model_results,
            "evaluation": eval_results,
            "model_path": save_path,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 訓練完成，耗時 {duration:.2f} 秒")
        logger.info("=" * 60)
        
        return self.results
    
    def _split_data(
        self,
        X_seq: np.ndarray,
        X_aux: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """時間序列分割"""
        n = len(y)
        train_end = int(n * self.config.train_split)
        val_end = int(n * (self.config.train_split + self.config.val_split))
        
        splits = {
            "train_X_seq": X_seq[:train_end],
            "train_X_aux": X_aux[:train_end],
            "train_y": y[:train_end],
            "val_X_seq": X_seq[train_end:val_end],
            "val_X_aux": X_aux[train_end:val_end],
            "val_y": y[train_end:val_end],
            "test_X_seq": X_seq[val_end:],
            "test_X_aux": X_aux[val_end:],
            "test_y": y[val_end:],
        }
        
        logger.info(f"   訓練集: {len(splits['train_y'])} 樣本")
        logger.info(f"   驗證集: {len(splits['val_y'])} 樣本")
        logger.info(f"   測試集: {len(splits['test_y'])} 樣本")
        
        return splits
    
    def _train_model(
        self,
        splits: Dict[str, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """訓練模型"""
        if self.config.model_type == "lstm":
            return self._train_lstm(splits)
        elif self.config.model_type == "xgboost":
            return self._train_xgboost(splits, feature_names)
        elif self.config.model_type == "ensemble":
            return self._train_ensemble(splits, feature_names)
        else:
            raise ValueError(f"未知模型類型: {self.config.model_type}")
    
    def _train_lstm(self, splits: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """訓練 LSTM 模型"""
        try:
            from app.ml.models import OrderFlowPatternClassifier, ModelConfig
        except ImportError:
            logger.error("LSTM 模型不可用，請安裝 TensorFlow")
            return {"error": "TensorFlow not available"}
        
        # 創建模型配置
        model_config = ModelConfig(
            sequence_length=splits["train_X_seq"].shape[1],
            num_features=splits["train_X_seq"].shape[2],
            num_aux_features=splits["train_X_aux"].shape[1],
            epochs=self.config.epochs,
            batch_size=self.config.batch_size,
            learning_rate=self.config.learning_rate,
            patience=self.config.patience,
        )
        
        # 創建並訓練模型
        classifier = OrderFlowPatternClassifier(config=model_config)
        classifier.build_model()
        classifier.compile_model(use_focal_loss=True)
        
        # 計算類別權重
        unique, counts = np.unique(splits["train_y"], return_counts=True)
        class_weights = {
            int(label): len(splits["train_y"]) / (len(unique) * count)
            for label, count in zip(unique, counts)
        }
        
        # 訓練
        results = classifier.train(
            X_seq=splits["train_X_seq"],
            X_aux=splits["train_X_aux"],
            y=splits["train_y"],
            validation_split=0.0,  # 使用預分割的驗證集
            class_weights=class_weights,
        )
        
        self._models["lstm"] = classifier
        
        return results
    
    def _train_xgboost(
        self,
        splits: Dict[str, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """訓練 XGBoost 模型"""
        try:
            from app.ml.models import MarketStateClassifier, XGBConfig
        except ImportError:
            logger.error("XGBoost 模型不可用，請安裝 xgboost")
            return {"error": "XGBoost not available"}
        
        # 將序列特徵展平（取最後時間點或平均）
        X_train = np.concatenate([
            splits["train_X_seq"][:, -1, :],  # 最後時間點
            splits["train_X_aux"],
        ], axis=1)
        
        X_val = np.concatenate([
            splits["val_X_seq"][:, -1, :],
            splits["val_X_aux"],
        ], axis=1)
        
        # 創建模型
        config = XGBConfig(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
        )
        
        classifier = MarketStateClassifier(config=config)
        
        # 訓練
        results = classifier.train(
            X=X_train,
            y=splits["train_y"],
            feature_names=feature_names,
            eval_set=(X_val, splits["val_y"]),
        )
        
        self._models["xgboost"] = classifier
        
        return results
    
    def _train_ensemble(
        self,
        splits: Dict[str, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """訓練集成模型"""
        results = {}
        
        # 訓練 LSTM
        logger.info("   訓練 LSTM 子模型...")
        lstm_results = self._train_lstm(splits)
        results["lstm"] = lstm_results
        
        # 訓練 XGBoost
        logger.info("   訓練 XGBoost 子模型...")
        xgb_results = self._train_xgboost(splits, feature_names)
        results["xgboost"] = xgb_results
        
        return results
    
    def _evaluate_model(self, splits: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """評估模型"""
        eval_results = {}
        
        if "lstm" in self._models:
            model = self._models["lstm"]
            
            # 測試集評估
            test_metrics = model.evaluate(
                splits["test_X_seq"],
                splits["test_X_aux"],
                splits["test_y"],
            )
            
            # 預測
            test_pred = model.predict_classes(
                splits["test_X_seq"],
                splits["test_X_aux"],
            )
            
            # 計算準確率
            accuracy = np.mean(test_pred == splits["test_y"])
            
            eval_results["lstm"] = {
                "test_accuracy": float(accuracy),
                "test_metrics": test_metrics,
            }
            
            logger.info(f"   LSTM 測試準確率: {accuracy:.4f}")
        
        if "xgboost" in self._models:
            model = self._models["xgboost"]
            
            X_test = np.concatenate([
                splits["test_X_seq"][:, -1, :],
                splits["test_X_aux"],
            ], axis=1)
            
            metrics = model.evaluate(X_test, splits["test_y"])
            
            eval_results["xgboost"] = {
                "test_accuracy": metrics["accuracy"],
                "test_metrics": metrics,
            }
            
            logger.info(f"   XGBoost 測試準確率: {metrics['accuracy']:.4f}")
        
        return eval_results
    
    def _save_model(self) -> Optional[str]:
        """保存模型"""
        if not self._models:
            return None
        
        # 創建模型目錄
        model_dir = self.config.model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_paths = []
        
        for name, model in self._models.items():
            if name == "lstm":
                path = os.path.join(model_dir, f"pattern_classifier_{timestamp}.h5")
                model.save(path)
            elif name == "xgboost":
                path = os.path.join(model_dir, f"market_state_{timestamp}.json")
                model.save(path)
            
            saved_paths.append(path)
            logger.info(f"   已保存: {path}")
        
        return saved_paths[0] if len(saved_paths) == 1 else saved_paths
    
    def get_model(self, name: str = None):
        """獲取訓練好的模型"""
        if name:
            return self._models.get(name)
        return self._models


def create_sample_training_data(
    num_samples: int = 1000,
    sequence_length: int = 100,
    num_features: int = 14,
    num_aux_features: int = 5,
    num_classes: int = 7,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    創建示範訓練數據
    
    用於測試訓練管道
    """
    np.random.seed(42)
    
    X_seq = np.random.randn(num_samples, sequence_length, num_features).astype(np.float32)
    X_aux = np.random.randn(num_samples, num_aux_features).astype(np.float32)
    y = np.random.randint(0, num_classes, num_samples).astype(np.int32)
    
    return X_seq, X_aux, y


# ==================== CLI 入口 ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="訓練訂單流模式識別模型")
    parser.add_argument("--model", type=str, default="lstm", choices=["lstm", "xgboost", "ensemble"])
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--demo", action="store_true", help="使用示範數據")
    
    args = parser.parse_args()
    
    # 配置
    config = TrainingConfig(
        model_type=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
    
    # 創建訓練管道
    pipeline = TrainingPipeline(config=config)
    
    if args.demo:
        # 使用示範數據
        logger.info("📊 使用示範數據進行訓練測試")
        X_seq, X_aux, y = create_sample_training_data()
        
        results = pipeline.run(X_seq, X_aux, y)
        
        print("\n📋 訓練結果摘要:")
        print(json.dumps(results, indent=2, default=str))
    else:
        print("請提供訓練數據，或使用 --demo 標誌進行測試")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
