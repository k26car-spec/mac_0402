"""
LSTM模型自适应阈值回测
解决固定0.5阈值导致的偏差问题
"""

import numpy as np
import pandas as pd
import yfinance as yf
import json
import os
import pickle
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import argparse
import warnings
warnings.filterwarnings('ignore')

# TensorFlow
import tensorflow as tf
from tensorflow.keras.models import load_model

print("=" * 70)
print("📊 LSTM自适应阈值回测系统")
print("=" * 70)

# 配置
MODEL_DIR = "models/lstm_smart_entry"
SEQUENCE_LENGTH = 60

def convert_numpy_types(obj):
    """递归转换numpy类型为Python原生类型"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    else:
        return obj

class LSTMAdaptiveBacktester:
    
    def __init__(self, model_dir=MODEL_DIR):
        self.model_dir = model_dir
        self.models = {}
        self.scalers = {} # 如果有保存scaler的话
        self.load_models()
    
    def load_models(self):
        """加载所有LSTM模型"""
        print(f"\n📁 加载LSTM模型...")
        
        if not os.path.exists(self.model_dir):
            print(f"   ⚠️ 目录不存在: {self.model_dir}")
            return
        
        model_files = [f for f in os.listdir(self.model_dir) if f.endswith('.h5')]
        print(f"   找到 {len(model_files)} 个模型文件")
        
        for model_file in model_files:
            try:
                stock_code = model_file.replace('_model.h5', '')
                model_path = os.path.join(self.model_dir, model_file)
                
                # 加载模型（兼容性处理）
                try:
                    model = load_model(model_path, compile=False)
                except:
                    import tensorflow.keras.metrics as metrics
                    custom_objects = {
                        'mse': metrics.MeanSquaredError(),
                        'mae': metrics.MeanAbsoluteError()
                    }
                    model = load_model(model_path, custom_objects=custom_objects, compile=False)
                
                model.compile(optimizer='adam', loss='mse', metrics=['mae'])
                self.models[stock_code] = model
                
                # 尝试加载对应的scaler信息（如果有）
                scaler_path = os.path.join(self.model_dir, f'{stock_code}_scaler.pkl')
                if os.path.exists(scaler_path):
                    with open(scaler_path, 'rb') as f:
                        self.scalers[stock_code] = pickle.load(f)
                        
            except Exception as e:
                print(f"   ❌ {model_file}: {str(e)[:50]}")
        
        print(f"   成功加载: {len(self.models)} 个模型")

    def prepare_data(self, stock_code, period='1y'): # 使用较长周期以确保有足够数据进行校准
        """准备数据：取足够长的数据来进行 calibration + test"""
        try:
            ticker = yf.Ticker(f"{stock_code}.TW")
            
            # 强制使用较长周期，因为我们需要切分数据来找阈值
            if period == '6m':
                fetch_period = '1y' 
            elif period == '3m':
                fetch_period = '9mo'
            else:
                fetch_period = '2y' # 默认更长
            
            df = ticker.history(period=fetch_period)
            
            if df.empty or len(df) < 150:
                print(f"   ⚠️ 数据不足 ({len(df)}行)")
                return None
            
            # 技术指标计算 (与训练一致)
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            df['Volatility'] = df['Close'].rolling(window=20).std()
            
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            
            # Label
            df['Future_Return'] = (df['Close'].shift(-5) / df['Close'] - 1) * 100
            df['Target'] = df['Future_Return']
            
            df = df.dropna()
            
            feature_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20', 
                            'Volume_MA5', 'RSI', 'Volatility', 'MACD']
            
            if len(df) < SEQUENCE_LENGTH + 20:
                return None
            
            # 归一化
            scaler_X = MinMaxScaler()
            scaler_y = MinMaxScaler()
            
            df[feature_cols] = scaler_X.fit_transform(df[feature_cols])
            df[['Target']] = scaler_y.fit_transform(df[['Target']])
            
            # 创建序列
            X, y_labels, returns = [], [], []
            
            for i in range(len(df) - SEQUENCE_LENGTH - 5):
                X.append(df[feature_cols].iloc[i:i+SEQUENCE_LENGTH].values)
                
                # 真实涨跌 (二分类标签)
                ret = df['Future_Return'].iloc[i+SEQUENCE_LENGTH]
                y_labels.append(1 if ret > 0 else 0)
                returns.append(ret)
            
            return np.array(X), np.array(y_labels), np.array(returns)
            
        except Exception as e:
            print(f"   数据准备错误: {e}")
            return None

    def find_optimal_threshold(self, predictions, y_true):
        """
        在给定的预测值和真实值中找到最佳阈值
        策略：遍历所有可能的阈值，找到准确率最高的那个
        """
        pred_flat = predictions.flatten()
        
        # 如果预测值非常集中（方差极小），可能模型失效，直接返回中位数
        if np.std(pred_flat) < 0.0001:
            return np.median(pred_flat)
            
        # 候选阈值：从预测值的 min 到 max
        candidates = np.linspace(pred_flat.min(), pred_flat.max(), 100)
        
        best_acc = 0
        best_threshold = 0.5
        
        for t in candidates:
            pred_binary = (pred_flat > t).astype(int)
            acc = accuracy_score(y_true, pred_binary)
            if acc > best_acc:
                best_acc = acc
                best_threshold = t
                
        return best_threshold

    def run_backtest(self, stock_list=None):
        if stock_list is None:
            stock_list = list(self.models.keys())
            
        print(f"\n🔍 开始自适应阈值回测...")
        print(f"   股票数量: {len(stock_list)}")
        
        results = []
        
        for i, stock in enumerate(stock_list, 1):
            print(f"\n   [{i}/{len(stock_list)}] {stock}...", end="", flush=True)
            
            if stock not in self.models:
                print(" ❌ 模型未加载")
                continue
                
            model = self.models[stock]
            
            # 1. 准备数据
            data = self.prepare_data(stock)
            if data is None:
                print(" ❌ 数据不足")
                continue
                
            X, y, rets = data
            
            # 2. 数据切分：前60%做校准(Calibration)，后40%做测试(Test)
            # 这样模拟我们在"过去"找到了最佳阈值，应用到"未来"
            split_idx = int(len(X) * 0.6)
            
            X_cal, X_test = X[:split_idx], X[split_idx:]
            y_cal, y_test = y[:split_idx], y[split_idx:]
            rets_test = rets[split_idx:]
            
            if len(X_cal) < 10 or len(X_test) < 10:
                print(" ❌ 切分后样本不足")
                continue
            
            # 3. 在校准集上预测 & 找阈值
            pred_cal = model.predict(X_cal, verbose=0)
            best_threshold = self.find_optimal_threshold(pred_cal, y_cal)
            
            # 4. 在测试集上应用阈值
            pred_test = model.predict(X_test, verbose=0)
            pred_test_binary = (pred_test.flatten() > best_threshold).astype(int)
            
            # 5. 计算指标
            acc = accuracy_score(y_test, pred_test_binary)
            
            # 避免除零警告
            precision = precision_score(y_test, pred_test_binary, zero_division=0)
            recall = recall_score(y_test, pred_test_binary, zero_division=0)
            
            # 6. 简单的收益模拟
            # 如果预测涨(1)就买入持有5天，否则空仓
            # 这里的rets是持有5天的收益率
            trade_rets = rets_test[pred_test_binary == 1]
            avg_return = np.mean(trade_rets) if len(trade_rets) > 0 else 0
            
            print(f" ✅ 阈值={best_threshold:.4f}, 准确率={acc*100:.1f}%")
            
            results.append({
                'stock_code': stock,
                'threshold': float(best_threshold),
                'accuracy': float(acc),
                'precision': float(precision),
                'recall': float(recall),
                'samples_test': len(y_test),
                'avg_return': float(avg_return),
                'pred_mean': float(np.mean(pred_test)),
                'pred_std': float(np.std(pred_test))
            })
            
        return results

def analyze_results(results):
    if not results:
        return
        
    avg_acc = np.mean([r['accuracy'] for r in results])
    avg_prec = np.mean([r['precision'] for r in results])
    avg_rec = np.mean([r['recall'] for r in results])
    
    print(f"\n\n{'='*70}")
    print(f"📊 自适应阈值回测结果分析")
    print(f"{'='*70}")
    print(f"参与股票: {len(results)} 支")
    print(f"平均准确率: {avg_acc*100:.2f}%  (目标: >52%)")
    print(f"平均精确率: {avg_prec*100:.2f}%")
    print(f"平均召回率: {avg_rec*100:.2f}%")
    
    # 分布
    good = [r for r in results if r['accuracy'] >= 0.6]
    okay = [r for r in results if 0.5 <= r['accuracy'] < 0.6]
    bad = [r for r in results if r['accuracy'] < 0.5]
    
    print(f"\n分布:")
    print(f"  🟢 优秀 (≥60%): {len(good)} 支")
    print(f"  🟡及格 (50-60%): {len(okay)} 支")
    print(f"  🔴 不及格 (<50%): {len(bad)} 支")
    
    # Top 5
    print(f"\nTop 5 表现:")
    top5 = sorted(results, key=lambda x: x['accuracy'], reverse=True)[:5]
    for r in top5:
        print(f"  {r['stock_code']}: {r['accuracy']*100:.1f}% (阈值: {r['threshold']:.4f})")
        
    return avg_acc

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stocks', type=str, default='all')
    parser.add_argument('--period', type=str, default='6m')
    args = parser.parse_args()
    
    backtester = LSTMAdaptiveBacktester()
    
    stocks = None
    if args.stocks != 'all':
        stocks = args.stocks.split(',')
        
    results = backtester.run_backtest(stocks)
    analyze_results(results)
    
    # 保存结果
    if results:
        output = convert_numpy_types(results)
        with open('lstm_adaptive_results.json', 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n结果已保存至 lstm_adaptive_results.json")

if __name__ == "__main__":
    main()
