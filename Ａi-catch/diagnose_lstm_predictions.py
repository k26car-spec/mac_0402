"""
LSTM预测诊断工具
分析为什么精确率/召回率=0，准确率低
找出问题根源

执行: python3 diagnose_lstm_predictions.py --stock 2314
"""

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model
import matplotlib
matplotlib.use('Agg')  # 非GUI后端
import matplotlib.pyplot as plt
import argparse
import warnings
warnings.filterwarnings('ignore')

def prepare_data(stock_code, period='1y'):
    """准备数据（与回测相同）"""
    ticker = yf.Ticker(f"{stock_code}.TW")
    df = ticker.history(period=period)
    
    if df.empty or len(df) < 100:
        return None
    
    # 技术指标
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
    
    df['Future_Return'] = (df['Close'].shift(-5) / df['Close'] - 1) * 100
    df['Target'] = df['Future_Return']
    
    df = df.dropna()
    
    if len(df) < 120:
        return None
    
    feature_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20', 
                    'Volume_MA5', 'RSI', 'Volatility', 'MACD']
    
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    df[feature_cols] = scaler_X.fit_transform(df[feature_cols])
    df[['Target']] = scaler_y.fit_transform(df[['Target']])
    
    SEQUENCE_LENGTH = 60
    X, y_continuous, y_binary = [], [], []
    future_returns = []
    
    for i in range(len(df) - SEQUENCE_LENGTH - 5):
        X.append(df[feature_cols].iloc[i:i+SEQUENCE_LENGTH].values)
        y_continuous.append(df['Target'].iloc[i+SEQUENCE_LENGTH])
        
        future_ret = df['Future_Return'].iloc[i+SEQUENCE_LENGTH]
        y_binary.append(1 if future_ret > 0 else 0)
        future_returns.append(future_ret)
    
    X = np.array(X)
    y_continuous = np.array(y_continuous)
    y_binary = np.array(y_binary)
    future_returns = np.array(future_returns)
    
    # 80/20分割
    split_idx = int(len(X) * 0.8)
    
    return {
        'X_test': X[split_idx:],
        'y_continuous': y_continuous[split_idx:],
        'y_binary': y_binary[split_idx:],
        'future_returns': future_returns[split_idx:],
        'scaler_y': scaler_y
    }


def diagnose_model(stock_code):
    """诊断单个模型"""
    print(f"\n{'='*70}")
    print(f"🔍 诊断股票: {stock_code}")
    print(f"{'='*70}")
    
    # 加载模型
    model_path = f"models/lstm_smart_entry/{stock_code}_model.h5"
    try:
        model = load_model(model_path, compile=False)
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        print(f"✅ 模型加载成功")
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return
    
    # 准备数据
    print(f"\n📊 准备数据...")
    data = prepare_data(stock_code)
    
    if data is None:
        print(f"❌ 数据准备失败")
        return
    
    X_test = data['X_test']
    y_binary = data['y_binary']
    future_returns = data['future_returns']
    
    print(f"   测试样本数: {len(X_test)}")
    print(f"   实际上涨: {np.sum(y_binary)} ({np.sum(y_binary)/len(y_binary)*100:.1f}%)")
    print(f"   实际下跌: {len(y_binary) - np.sum(y_binary)} ({(1-np.sum(y_binary)/len(y_binary))*100:.1f}%)")
    
    # LSTM预测
    print(f"\n🤖 LSTM预测...")
    predictions = model.predict(X_test, verbose=0)
    pred_continuous = predictions.flatten()
    
    print(f"   预测值范围: [{pred_continuous.min():.4f}, {pred_continuous.max():.4f}]")
    print(f"   预测值均值: {pred_continuous.mean():.4f}")
    print(f"   预测值std: {pred_continuous.std():.4f}")
    
    # 分析预测分布
    print(f"\n📈 预测分布分析:")
    quantiles = np.percentile(pred_continuous, [0, 25, 50, 75, 100])
    print(f"   Min:  {quantiles[0]:.4f}")
    print(f"   Q1:   {quantiles[1]:.4f}")
    print(f"   Q2:   {quantiles[2]:.4f}")
    print(f"   Q3:   {quantiles[3]:.4f}")
    print(f"   Max:  {quantiles[4]:.4f}")
    
    # 测试不同阈值
    print(f"\n🎯 不同阈值的准确率:")
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    
    best_threshold = 0.5
    best_accuracy = 0
    
    for threshold in thresholds:
        pred_binary = (pred_continuous > threshold).astype(int)
        accuracy = np.sum(pred_binary == y_binary) / len(y_binary)
        n_positive = np.sum(pred_binary)
        
        print(f"   阈值={threshold:.1f}: 准确率={accuracy*100:.2f}%, "
              f"预测上涨={n_positive}/{len(y_binary)} ({n_positive/len(y_binary)*100:.1f}%)")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
    
    print(f"\n✅ 最佳阈值: {best_threshold} (准确率={best_accuracy*100:.2f}%)")
    
    # 使用最佳阈值
    pred_binary = (pred_continuous > best_threshold).astype(int)
    
    # 混淆矩阵
    print(f"\n📊 混淆矩阵（阈值={best_threshold}）:")
    tp = np.sum((pred_binary == 1) & (y_binary == 1))
    fp = np.sum((pred_binary == 1) & (y_binary == 0))
    tn = np.sum((pred_binary == 0) & (y_binary == 0))
    fn = np.sum((pred_binary == 0) & (y_binary == 1))
    
    print(f"                实际上涨  实际下跌")
    print(f"   预测上涨      {tp:3d}      {fp:3d}")
    print(f"   预测下跌      {fn:3d}      {tn:3d}")
    
    # 计算指标
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\n📈 性能指标:")
    print(f"   准确率: {best_accuracy*100:.2f}%")
    print(f"   精确率: {precision*100:.2f}%")
    print(f"   召回率: {recall*100:.2f}%")
    print(f"   F1分数: {f1*100:.2f}%")
    
    # 预测vs实际
    print(f"\n💰 预测效果（如果交易）:")
    if np.sum(pred_binary) > 0:
        avg_return_if_traded = future_returns[pred_binary == 1].mean()
        print(f"   预测上涨时买入，平均收益: {avg_return_if_traded:.2f}%")
    else:
        print(f"   ⚠️ 从未预测上涨")
    
    # 可视化（保存图片）
    print(f"\n📊 生成可视化...")
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. 预测分布
    axes[0, 0].hist(pred_continuous, bins=50)
    axes[0, 0].axvline(best_threshold, color='r', linestyle='--', label=f'最佳阈值={best_threshold}')
    axes[0, 0].set_title(f'{stock_code} - LSTM预测值分布')
    axes[0, 0].set_xlabel('预测值')
    axes[0, 0].set_ylabel('频数')
    axes[0, 0].legend()
    
    # 2. 预测vs实际
    axes[0, 1].scatter(range(len(future_returns)), future_returns, alpha=0.5, label='实际收益')
    axes[0, 1].scatter(range(len(pred_continuous)), pred_continuous, alpha=0.5, label='LSTM预测')
    axes[0, 1].set_title(f'{stock_code} - 预测 vs 实际')
    axes[0, 1].set_xlabel('样本')
    axes[0, 1].set_ylabel('值')
    axes[0, 1].legend()
    
    # 3. 准确率 vs 阈值
    thresholds_test = np.linspace(0.1, 0.9, 50)
    accuracies = []
    for t in thresholds_test:
        pb = (pred_continuous > t).astype(int)
        acc = np.sum(pb == y_binary) / len(y_binary)
        accuracies.append(acc)
    
    axes[1, 0].plot(thresholds_test, accuracies)
    axes[1, 0].axvline(best_threshold, color='r', linestyle='--', label=f'最佳={best_threshold}')
    axes[1, 0].axhline(0.5, color='g', linestyle='--', label='随机=50%')
    axes[1, 0].set_title(f'{stock_code} - 准确率 vs 阈值')
    axes[1, 0].set_xlabel('阈值')
    axes[1, 0].set_ylabel('准确率')
    axes[1, 0].legend()
    axes[1, 0].grid(True)
    
    # 4. 混淆矩阵可视化
    cm = np.array([[tn, fp], [fn, tp]])
    im = axes[1, 1].imshow(cm, cmap='Blues')
    axes[1, 1].set_xticks([0, 1])
    axes[1, 1].set_yticks([0, 1])
    axes[1, 1].set_xticklabels(['实际下跌', '实际上涨'])
    axes[1, 1].set_yticklabels(['预测下跌', '预测上涨'])
    axes[1, 1].set_title(f'{stock_code} - 混淆矩阵')
    
    for i in range(2):
        for j in range(2):
            text = axes[1, 1].text(j, i, cm[i, j], ha="center", va="center", color="black")
    
    plt.tight_layout()
    output_file = f'diagnosis_{stock_code}.png'
    plt.savefig(output_file, dpi=100, bbox_inches='tight')
    print(f"   保存图表: {output_file}")
    
    # 返回诊断结果
    return {
        'stock_code': stock_code,
        'best_threshold': best_threshold,
        'best_accuracy': best_accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'pred_mean': float(pred_continuous.mean()),
        'pred_std': float(pred_continuous.std()),
        'n_samples': len(X_test)
    }


def main():
    parser = argparse.ArgumentParser(description='LSTM预测诊断')
    parser.add_argument('--stock', type=str, required=True, help='股票代码')
    
    args = parser.parse_args()
    
    result = diagnose_model(args.stock)
    
    if result:
        print(f"\n{'='*70}")
        print(f"✅ 诊断完成")
        print(f"{'='*70}")
        
        print(f"\n💡 诊断结论:")
        
        if result['best_accuracy'] < 0.5:
            print(f"   ⚠️ 最佳准确率({result['best_accuracy']*100:.1f}%)低于随机(50%)")
            print(f"   问题: 模型预测能力不足")
            print(f"   建议: ")
            print(f"      1. 检查训练数据质量")
            print(f"      2. 调整模型架构")
            print(f"      3. 增加特征工程")
        elif result['precision'] == 0 or result['recall'] == 0:
            print(f"   ⚠️ 精确率或召回率为0")
            print(f"   问题: 模型预测极端偏向")
            if result['pred_mean'] < 0.3:
                print(f"   原因: 预测值均值({result['pred_mean']:.3f})太低，几乎不预测上涨")
            elif result['pred_mean'] > 0.7:
                print(f"   原因: 预测值均值({result['pred_mean']:.3f})太高，几乎全预测上涨")
            
            print(f"   建议: 使用最佳阈值{result['best_threshold']}而不是0.5")
        elif result['best_accuracy'] >= 0.55:
            print(f"   ✅ 准确率达标({result['best_accuracy']*100:.1f}%)")
            print(f"   建议: 使用阈值{result['best_threshold']}")
        else:
            print(f"   🔶 准确率接近目标({result['best_accuracy']*100:.1f}%)")
            print(f"   建议: 可以尝试使用，但需谨慎")


if __name__ == "__main__":
    main()
