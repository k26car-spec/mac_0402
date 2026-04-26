"""
LSTM股票价格预测模型 - 框架代码
LSTM Stock Price Prediction - Framework

注意：这只是框架代码，需要：
1. 收集历史数据
2. 训练模型（需要GPU，数小时）
3. 调参优化
4. 验证准确率

请在明天/未来完成这些步骤！
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
import pickle


class LSTMStockPredictor:
    """LSTM股票预测器（框架）"""
    
    def __init__(self, sequence_length: int = 60):
        """
        初始化LSTM预测器
        
        Args:
            sequence_length: 输入序列长度（天数）
        """
        self.sequence_length = sequence_length
        self.model = None
        self.scaler = None
    
    def prepare_data(self, prices: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据
        
        Args:
            prices: 历史价格列表
        
        Returns:
            X, y: 特征和标签
        """
        # 标准化
        from sklearn.preprocessing import MinMaxScaler
        
        if self.scaler is None:
            self.scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = self.scaler.fit_transform(np.array(prices).reshape(-1, 1))
        else:
            scaled_data = self.scaler.transform(np.array(prices).reshape(-1, 1))
        
        # 创建序列
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i, 0])
            y.append(scaled_data[i, 0])
        
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape: Tuple[int, int]):
        """
        构建LSTM模型
        
        需要安装：pip install tensorflow
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import Dense, LSTM, Dropout
            
            model = Sequential([
                LSTM(units=50, return_sequences=True, input_shape=input_shape),
                Dropout(0.2),
                LSTM(units=50, return_sequences=True),
                Dropout(0.2),
                LSTM(units=50),
                Dropout(0.2),
                Dense(units=1)
            ])
            
            model.compile(optimizer='adam', loss='mean_squared_error')
            self.model = model
            
            print("✅ LSTM模型已构建")
            print(f"   输入形状: {input_shape}")
            print(f"   参数量: {model.count_params():,}")
            
        except ImportError:
            print("❌ 需要安装TensorFlow: pip install tensorflow")
            return None
    
    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, batch_size: int = 32):
        """
        训练模型
        
        注意：需要GPU加速，训练时间可能数小时
        """
        if self.model is None:
            print("❌ 请先构建模型")
            return
        
        print(f"\n🚀 开始训练...")
        print(f"   训练样本: {len(X)}")
        print(f"   训练轮数: {epochs}")
        print(f"   批次大小: {batch_size}")
        print(f"\n⚠️  这将需要数小时时间！")
        
        # Reshape X for LSTM
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        # 训练模型
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.1,
            verbose=1
        )
        
        print("\n✅ 训练完成！")
        return history
    
    def predict(self, recent_prices: List[float]) -> Optional[float]:
        """
        预测未来价格
        
        Args:
            recent_prices: 最近的价格数据（至少sequence_length个）
        
        Returns:
            预测价格
        """
        if self.model is None:
            print("❌ 模型未训练")
            return None
        
        if len(recent_prices) < self.sequence_length:
            print(f"❌ 需要至少{self.sequence_length}天的数据")
            return None
        
        # 准备输入
        scaled_data = self.scaler.transform(
            np.array(recent_prices[-self.sequence_length:]).reshape(-1, 1)
        )
        X = np.reshape(scaled_data, (1, self.sequence_length, 1))
        
        # 预测
        predicted_scaled = self.model.predict(X, verbose=0)
        predicted_price = self.scaler.inverse_transform(predicted_scaled)[0][0]
        
        return predicted_price
    
    def save_model(self, path: str):
        """保存模型"""
        if self.model is not None:
            self.model.save(f"{path}_model.h5")
            with open(f"{path}_scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
            print(f"✅ 模型已保存到 {path}")
    
    def load_model(self, path: str):
        """加载模型"""
        try:
            from tensorflow.keras.models import load_model
            
            self.model = load_model(f"{path}_model.h5")
            with open(f"{path}_scaler.pkl", 'rb') as f:
                self.scaler = pickle.load(f)
            print(f"✅ 模型已加载从 {path}")
        except Exception as e:
            print(f"❌ 加载模型失败: {e}")


# ===== 使用示例 =====

def example_usage():
    """示例：如何使用LSTM预测器"""
    
    print("="*70)
    print("📚 LSTM股票预测器 - 使用示例")
    print("="*70)
    
    # 1. 创建预测器
    predictor = LSTMStockPredictor(sequence_length=60)
    
    # 2. 准备数据（示例：需要真实历史数据）
    print("\n⚠️  需要真实历史数据！")
    print("   - 至少1年的日线数据")
    print("   - 可以使用Yahoo Finance获取")
    print("   - 示例：yf.download('2330.TW', period='2y')")
    
    # 模拟数据（仅用于演示）
    fake_prices = [100 + i + np.random.randn()*5 for i in range(500)]
    
    # 3. 准备训练数据
    X, y = predictor.prepare_data(fake_prices[:-30])
    print(f"\n✅ 数据准备完成")
    print(f"   特征形状: {X.shape}")
    print(f"   标签形状: {y.shape}")
    
    # 4. 构建模型
    predictor.build_model(input_shape=(X.shape[1], 1))
    
    # 5. 训练模型（注释掉，需要GPU和时间）
    print("\n⚠️  训练已跳过（示例中）")
    print("   实际使用时请取消注释train()调用")
    # predictor.train(X, y, epochs=100, batch_size=32)
    
    # 6. 预测（需要先训练）
    print("\n⚠️  预测需要先训练模型")
    # prediction = predictor.predict(fake_prices[-60:])
    # print(f"明日预测价格: ${prediction:.2f}")
    
    print("\n" + "="*70)
    print("✅ 框架代码演示完成")
    print("="*70)


if __name__ == "__main__":
    example_usage()
