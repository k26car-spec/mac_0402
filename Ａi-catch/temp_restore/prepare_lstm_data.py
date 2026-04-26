#!/usr/bin/env python3
"""
LSTM历史数据准备脚本
Prepare Historical Data for LSTM Training

功能:
1. 下载历史数据
2. 数据清洗和预处理
3. 创建训练/验证/测试集
4. 保存为CSV和NumPy格式
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Tuple, Optional


class LSTMDataPreparator:
    """LSTM数据准备器"""
    
    def __init__(self, data_dir: str = "data/lstm"):
        """
        初始化
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def download_historical_data(self, symbol: str, years: int = 2) -> Optional[pd.DataFrame]:
        """
        下载历史数据
        
        Args:
            symbol: 股票代码（如：2330）
            years: 年数
        
        Returns:
            DataFrame: 历史数据
        """
        print(f"\n📊 下载 {symbol} 过去{years}年历史数据...")
        
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years*365)
            
            # 下载数据
            hist = ticker.history(start=start_date.strftime('%Y-%m-%d'),
                                 end=end_date.strftime('%Y-%m-%d'))
            
            if hist.empty:
                print(f"❌ 无法获取{symbol}数据")
                return None
            
            print(f"✅ 成功下载{len(hist)}天数据")
            print(f"   期间: {hist.index[0].date()} 到 {hist.index[-1].date()}")
            
            return hist
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            return None
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加技术指标
        
        Args:
            df: 原始数据
        
        Returns:
            DataFrame: 包含技术指标的数据
        """
        print("\n🔧 计算技术指标...")
        
        # 移动平均
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        # 价格变化
        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # 波动率
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        
        # 成交量变化
        df['Volume_Change'] = df['Volume'].pct_change()
        df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
        
        # RSI (简化版)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD (简化版)
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # 布林带
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # 价格位置（相对于52周高低点）
        df['High_52w'] = df['High'].rolling(window=252).max()
        df['Low_52w'] = df['Low'].rolling(window=252).min()
        df['Price_Position'] = (df['Close'] - df['Low_52w']) / (df['High_52w'] - df['Low_52w'])
        
        print(f"✅ 添加了{len(df.columns) - 6}个技术指标")
        
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据
        
        Args:
            df: 原始数据
        
        Returns:
            DataFrame: 清洗后的数据
        """
        print("\n🧹 清洗数据...")
        
        original_len = len(df)
        
        # 替换无穷大值为NaN
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # 删除NaN值
        df = df.dropna()
        
        # 删除异常值（价格为0或负数）
        df = df[df['Close'] > 0]
        df = df[df['Volume'] > 0]
        
        # 删除极端波动（日涨跌幅>20%）
        if 'Returns' in df.columns:
            df = df[abs(df['Returns']) < 0.2]
        
        cleaned_len = len(df)
        removed = original_len - cleaned_len
        
        print(f"✅ 清洗完成")
        print(f"   原始数据: {original_len}天")
        print(f"   清洗后: {cleaned_len}天")
        print(f"   移除: {removed}天 ({removed/original_len*100:.1f}%)")
        
        return df
    
    def create_sequences(self, df: pd.DataFrame, 
                        sequence_length: int = 60,
                        target_col: str = 'Close') -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        创建序列数据（用于LSTM）
        
        Args:
            df: 数据
            sequence_length: 序列长度
            target_col: 目标列
        
        Returns:
            X, y, scalers: 特征、标签和归一化器
        """
        print(f"\n📦 创建序列数据（序列长度:{sequence_length}）...")
        
        # 选择特征列
        feature_cols = [
            'Open', 'High', 'Low', 'Close', 'Volume',
            'MA5', 'MA10', 'MA20', 'MA60',
            'Returns', 'Volatility', 'Volume_Change',
            'RSI', 'MACD', 'Price_Position'
        ]
        
        available_cols = [col for col in feature_cols if col in df.columns]
        
        # 归一化特征
        from sklearn.preprocessing import MinMaxScaler
        scaler_X = MinMaxScaler()
        scaled_data = scaler_X.fit_transform(df[available_cols])
        
        # 归一化标签（关键修复！）
        scaler_y = MinMaxScaler()
        y_original = df[target_col].values.reshape(-1, 1)
        y_scaled = scaler_y.fit_transform(y_original).flatten()
        
        # 创建序列
        X, y = [], []
        
        for i in range(sequence_length, len(scaled_data)):
            X.append(scaled_data[i-sequence_length:i])
            y.append(y_scaled[i])  # ✅ 使用归一化后的y
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"✅ 序列创建完成")
        print(f"   特征形状: {X.shape}")
        print(f"   标签形状: {y.shape}")
        print(f"   特征数量: {len(available_cols)}")
        print(f"   ✅ 特征和标签都已归一化到 [0, 1]")
        
        scalers = {
            'scaler_X': scaler_X,
            'scaler_y': scaler_y,
            'feature_cols': available_cols
        }
        
        return X, y, scalers
    
    def split_data(self, X: np.ndarray, y: np.ndarray,
                   train_ratio: float = 0.7,
                   val_ratio: float = 0.15) -> dict:
        """
        划分训练/验证/测试集
        
        Args:
            X: 特征
            y: 标签
            train_ratio: 训练集比例
            val_ratio: 验证集比例
        
        Returns:
            dict: 包含各个数据集
        """
        print(f"\n✂️  划分数据集...")
        print(f"   训练集: {train_ratio*100}%")
        print(f"   验证集: {val_ratio*100}%")
        print(f"   测试集: {(1-train_ratio-val_ratio)*100}%")
        
        total_len = len(X)
        train_len = int(total_len * train_ratio)
        val_len = int(total_len * val_ratio)
        
        # 时间序列数据，按时间顺序划分
        X_train = X[:train_len]
        y_train = y[:train_len]
        
        X_val = X[train_len:train_len+val_len]
        y_val = y[train_len:train_len+val_len]
        
        X_test = X[train_len+val_len:]
        y_test = y[train_len+val_len:]
        
        print(f"\n✅ 数据集划分完成")
        print(f"   训练集: {len(X_train)} 样本")
        print(f"   验证集: {len(X_val)} 样本")
        print(f"   测试集: {len(X_test)} 样本")
        
        return {
            'X_train': X_train,
            'y_train': y_train,
            'X_val': X_val,
            'y_val': y_val,
            'X_test': X_test,
            'y_test': y_test
        }
    
    def save_data(self, symbol: str, df: pd.DataFrame, datasets: dict, scalers: dict):
        """
        保存数据
        
        Args:
            symbol: 股票代码
            df: 原始数据
            datasets: 训练/验证/测试集
            scalers: 归一化器
        """
        print(f"\n💾 保存数据...")
        
        # 创建股票专用目录
        stock_dir = os.path.join(self.data_dir, symbol)
        os.makedirs(stock_dir, exist_ok=True)
        
        # 保存原始数据（CSV）
        csv_path = os.path.join(stock_dir, f"{symbol}_historical.csv")
        df.to_csv(csv_path)
        print(f"✅ CSV已保存: {csv_path}")
        
        # 保存训练集（NumPy）
        for key, data in datasets.items():
            npy_path = os.path.join(stock_dir, f"{symbol}_{key}.npy")
            np.save(npy_path, data)
            print(f"✅ {key}已保存: {npy_path}")
        
        # 保存scaler（关键！）
        import joblib
        scaler_X_path = os.path.join(stock_dir, f"{symbol}_scaler_X.pkl")
        scaler_y_path = os.path.join(stock_dir, f"{symbol}_scaler_y.pkl")
        joblib.dump(scalers['scaler_X'], scaler_X_path)
        joblib.dump(scalers['scaler_y'], scaler_y_path)
        print(f"✅ scaler_X已保存: {scaler_X_path}")
        print(f"✅ scaler_y已保存: {scaler_y_path}")
        
        # 保存元数据
        metadata = {
            'symbol': symbol,
            'total_days': len(df),
            'date_range': f"{df.index[0].date()} to {df.index[-1].date()}",
            'features': list(df.columns),
            'feature_cols_used': scalers['feature_cols'],
            'train_samples': len(datasets['X_train']),
            'val_samples': len(datasets['X_val']),
            'test_samples': len(datasets['X_test']),
            'sequence_length': datasets['X_train'].shape[1],
            'created_at': datetime.now().isoformat()
        }
        
        import json
        meta_path = os.path.join(stock_dir, f"{symbol}_metadata.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"✅ 元数据已保存: {meta_path}")
        
        print(f"\n🎉 所有数据已保存到: {stock_dir}")
    
    def prepare_stock_data(self, symbol: str, years: int = 2):
        """
        完整的数据准备流程
        
        Args:
            symbol: 股票代码
            years: 历史年数
        """
        print("="*70)
        print(f"🔬 LSTM数据准备: {symbol}")
        print("="*70)
        
        # 1. 下载数据
        df = self.download_historical_data(symbol, years)
        if df is None:
            return
        
        # 2. 添加技术指标
        df = self.add_technical_indicators(df)
        
        # 3. 清洗数据
        df = self.clean_data(df)
        
        # 4. 创建序列
        X, y, scalers = self.create_sequences(df, sequence_length=60)
        
        # 5. 划分数据集
        datasets = self.split_data(X, y)
        
        # 6. 保存数据
        self.save_data(symbol, df, datasets, scalers)
        
        print("\n" + "="*70)
        print(f"✅ {symbol} 数据准备完成！")
        print("="*70)
        
        return {
            'dataframe': df,
            'datasets': datasets,
            'scalers': scalers
        }


def main():
    """主函数"""
    
    print("\n" + "="*70)
    print("🚀 LSTM历史数据准备系统")
    print("="*70)
    
    # 创建准备器
    preparator = LSTMDataPreparator(data_dir="data/lstm")
    
    # 准备多只股票的数据
    stocks = ["2330", "2317", "2454"]
    
    for symbol in stocks:
        print(f"\n\n")
        preparator.prepare_stock_data(symbol, years=2)
    
    print("\n" + "="*70)
    print("✅ 所有股票数据准备完成！")
    print("="*70)
    print(f"\n📁 数据位置: data/lstm/")
    print(f"\n下一步:")
    print(f"  1. 查看数据: ls data/lstm/*/")
    print(f"  2. 训练模型: python backend-v3/app/lstm_predictor.py")
    print(f"  3. 评估结果: 查看训练输出")


if __name__ == "__main__":
    main()
