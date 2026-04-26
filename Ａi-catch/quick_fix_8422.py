"""
8422快速诊断和修复脚本
时间限制: 1-2小时
目标: 快速判断是否可以改善，如不能则排除

执行: python3 quick_fix_8422.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from improved_stock_training import build_regularized_model, RegularizedConfig
from tensorflow.keras.callbacks import EarlyStopping
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("🔬 8422 快速诊断和修复（1-2小时）")
print("=" * 70)

# ==================== 阶段1: 数据获取和准备 ====================

print("\n📥 阶段1: 获取数据...")

try:
    ticker = yf.Ticker("8422.TW")
    df = ticker.history(period="365d")
    
    if df.empty or len(df) < 100:
        print("❌ 数据不足，建议排除此股票")
        exit(1)
    
    print(f"✅ 成功获取 {len(df)} 天数据")
    
except Exception as e:
    print(f"❌ 获取数据失败: {str(e)}")
    print("建议: 排除此股票")
    exit(1)

# 计算技术指标
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA10'] = df['Close'].rolling(window=10).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()

# RSI
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# 波动率
df['Volatility'] = df['Close'].rolling(window=20).std()

# MACD
exp1 = df['Close'].ewm(span=12, adjust=False).mean()
exp2 = df['Close'].ewm(span=26, adjust=False).mean()
df['MACD'] = exp1 - exp2

# 目标: 预测5天后收益率
df['Target'] = (df['Close'].shift(-5) / df['Close'] - 1) * 100

# 删除NaN
df = df.dropna()

print(f"✅ 计算特征完成，剩余 {len(df)} 个样本")

# ==================== 阶段2: 诊断检查 ====================

print("\n🔍 阶段2: 诊断检查...")

# 检查1: 目标变量分布
target_mean = np.mean(df['Target'])
target_std = np.std(df['Target'])
target_min = np.min(df['Target'])
target_max = np.max(df['Target'])

print(f"\n目标变量统计:")
print(f"  均值: {target_mean:.3f}%")
print(f"  标准差: {target_std:.3f}%")
print(f"  范围: [{target_min:.3f}%, {target_max:.3f}%]")

# 检查异常值
outliers = df[np.abs(df['Target'] - target_mean) > 3 * target_std]
print(f"  异常值: {len(outliers)} 个 ({len(outliers)/len(df)*100:.1f}%)")

if len(outliers) > len(df) * 0.1:
    print(f"  ⚠️ 异常值较多，可能影响模型")

# ==================== 阶段3: 准备序列数据 ====================

print("\n📊 阶段3: 准备序列数据...")

# 选择特征
feature_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20', 
                'Volume_MA5', 'RSI', 'Volatility', 'MACD']

# 标准化
scaler_X = MinMaxScaler()
scaler_y = MinMaxScaler()

df[feature_cols] = scaler_X.fit_transform(df[feature_cols])
df[['Target']] = scaler_y.fit_transform(df[['Target']])

# 创建序列
sequence_length = 60

def create_sequences(data, seq_len):
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[feature_cols].iloc[i:i+seq_len].values)
        y.append(data['Target'].iloc[i+seq_len])
    return np.array(X), np.array(y)

X, y = create_sequences(df, sequence_length)

print(f"✅ 序列数据: X shape={X.shape}, y shape={y.shape}")

# ==================== 阶段4: 测试不同分割点 ====================

print("\n" + "=" * 70)
print("🧪 阶段4: 测试不同训练/测试分割")
print("=" * 70)

split_ratios = [0.70, 0.75, 0.80, 0.85]
results = []

for ratio in split_ratios:
    print(f"\n测试分割比例: {ratio:.0%}")
    
    split_idx = int(len(X) * ratio)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"  训练集: {len(X_train)} 样本")
    print(f"  测试集: {len(X_test)} 样本")
    
    # 训练Baseline模型
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    
    model = Sequential([
        LSTM(64, return_sequences=False, input_shape=(60, 9)),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dropout(0.2),
        Dense(1)
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    
    early_stop = EarlyStopping(
        monitor='val_mae',
        patience=20,
        restore_best_weights=True,
        verbose=0
    )
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=100,
        batch_size=32,
        callbacks=[early_stop],
        verbose=0
    )
    
    # 评估
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    gap = test_mae - train_mae
    
    print(f"  训练MAE: {train_mae:.4f}")
    print(f"  测试MAE: {test_mae:.4f}")
    print(f"  差距:    {gap:+.4f}")
    
    results.append({
        'ratio': ratio,
        'train_mae': train_mae,
        'test_mae': test_mae,
        'gap': gap
    })

# 找出最佳分割
best = min(results, key=lambda x: abs(x['gap']))

print(f"\n" + "=" * 70)
print(f"📊 分割测试结果汇总")
print(f"=" * 70)

for r in results:
    marker = " ⭐" if r == best else ""
    print(f"  {r['ratio']:.0%}: MAE={r['test_mae']:.4f}, Gap={r['gap']:+.4f}{marker}")

print(f"\n最佳分割: {best['ratio']:.0%}")
print(f"  差距: {best['gap']:+.4f}")

# 判断1: 是否通过分割改善
if abs(best['gap']) < 1.0:
    print(f"\n✅ 通过调整分割，差距降到 {abs(best['gap']):.3f} < 1.0")
    print(f"   建议: 使用 {best['ratio']:.0%} 分割继续优化")
    PASSED_SPLIT_TEST = True
else:
    print(f"\n⚠️ 最佳分割的差距仍然 {abs(best['gap']):.3f} > 1.0")
    print(f"   继续下一步测试...")
    PASSED_SPLIT_TEST = False

# ==================== 阶段5: 测试极强正则化 ====================

print(f"\n" + "=" * 70)
print(f"🧪 阶段5: 测试极强正则化")
print(f"=" * 70)

# 使用最佳分割
split_idx = int(len(X) * best['ratio'])
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"\n使用分割比例: {best['ratio']:.0%}")

# 极强正则化配置
config = RegularizedConfig()
config.l2_reg = 0.03  # 极强
config.dropout_rate = 0.5  # 极高
config.recurrent_dropout = 0.3  # 高
config.early_stop_patience = 30

print(f"极强正则化配置:")
print(f"  L2正则化: {config.l2_reg}")
print(f"  Dropout: {config.dropout_rate}")
print(f"  Recurrent Dropout: {config.recurrent_dropout}")

model = build_regularized_model(config)

early_stop = EarlyStopping(
    monitor='val_mae',
    patience=config.early_stop_patience,
    restore_best_weights=True,
    verbose=0
)

print(f"\n训练中...")

history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=config.max_epochs,
    batch_size=config.batch_size,
    callbacks=[early_stop],
    verbose=0
)

# 评估
train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
gap = test_mae - train_mae

print(f"\n✅ 训练完成")
print(f"  训练MAE: {train_mae:.4f}")
print(f"  测试MAE: {test_mae:.4f}")
print(f"  差距:    {gap:+.4f}")
print(f"  训练轮数: {len(history.history['loss'])}")

# 判断2: 是否通过极强正则化改善
if abs(gap) < 1.0:
    print(f"\n✅ 通过极强正则化，差距降到 {abs(gap):.3f} < 1.0")
    PASSED_REG_TEST = True
else:
    print(f"\n⚠️ 即使极强正则化，差距仍然 {abs(gap):.3f} > 1.0")
    PASSED_REG_TEST = False

# ==================== 最终决策 ====================

print(f"\n" + "=" * 70)
print(f"🎯 最终决策")
print(f"=" * 70)

print(f"\n测试结果:")
print(f"  ✅ 分割测试: {'通过' if PASSED_SPLIT_TEST else '未通过'} (最佳gap={best['gap']:+.3f})")
print(f"  ✅ 正则化测试: {'通过' if PASSED_REG_TEST else '未通过'} (gap={gap:+.3f})")

if PASSED_SPLIT_TEST or PASSED_REG_TEST:
    print(f"\n✅ 决策: 保留8422")
    print(f"\n推荐配置:")
    if PASSED_SPLIT_TEST:
        print(f"  • 使用分割比例: {best['ratio']:.0%}")
    if PASSED_REG_TEST:
        print(f"  • 使用极强正则化")
        print(f"    - L2: {config.l2_reg}")
        print(f"    - Dropout: {config.dropout_rate}")
    
    print(f"\n下一步:")
    print(f"  python3 fix_worst_5_stocks.py")
    
else:
    print(f"\n❌ 决策: 排除8422")
    print(f"\n理由:")
    print(f"  • 所有快速修复尝试均未成功")
    print(f"  • 差距仍然过大 (>{abs(gap):.1f})")
    print(f"  • 继续调试可能浪费更多时间")
    
    print(f"\n建议:")
    print(f"  1. 标记8422为排除")
    print(f"  2. 更新监控列表")
    print(f"  3. 继续改进其他42支股票")
    
    print(f"\n执行:")
    print(f"  echo '8422' >> excluded_stocks.txt")
    print(f"  python3 fix_worst_5_stocks.py  # 会跳过8422")

print(f"\n" + "=" * 70)
print(f"✅ 快速诊断完成！")
print(f"=" * 70)
