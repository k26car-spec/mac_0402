"""
改進模型快速測試腳本
快速驗證6種模型方案的效果

執行: python3 quick_test_improved_models.py
"""

import numpy as np
from improved_stock_training import *

print("=" * 70)
print("🧪 改進模型快速測試")
print("=" * 70)

# ==================== 生成模擬數據 ====================

print("\n1️⃣  生成模擬數據...")

np.random.seed(42)

# 模擬1000個樣本，60天回看，9個特徵
n_samples = 1000
lookback = 60
n_features = 9

# 生成具有趨勢的模擬數據
X = np.random.randn(n_samples, lookback, n_features) * 0.1

# 添加趨勢
for i in range(n_samples):
    trend = np.linspace(0, np.random.randn() * 0.5, lookback)
    X[i, :, 0] += trend  # Close價格添加趨勢
    
# 生成目標數據（與Close相關）
y = X[:, -1, 0] + np.random.randn(n_samples) * 0.05

print(f"✅ 數據形狀:")
print(f"   X: {X.shape}")
print(f"   y: {y.shape}")


# ==================== 測試單個模型 ====================

print("\n\n2️⃣  測試單個模型（Optimized）...")

# 配置
config = OptimizedConfig()
model = build_optimized_model(config)

print(f"\n📋 模型架構:")
model.summary()

print(f"\n訓練配置:")
print(f"   LSTM單元: {config.lstm_units}")
print(f"   學習率: {config.learning_rate}")
print(f"   L2正則化: {config.l2_reg}")
print(f"   Dropout: {config.dropout_rate}")
print(f"   Recurrent Dropout: {config.recurrent_dropout}")


# ==================== 測試所有6種方法 ====================

print("\n\n3️⃣  測試所有6種方法...")

# 使用綜合測試框架
results = comprehensive_test(
    stock_code='TEST_STOCK',
    X_data=X,
    y_data=y,
    test_all_methods=True,
    save_dir='./improved_results'
)


# ==================== 結果分析 ====================

print("\n\n4️⃣  結果分析...")

# 找出最佳方法
best_method = min(results.items(), key=lambda x: x[1]['val_mae'])
worst_method = max(results.items(), key=lambda x: x[1]['val_mae'])

print(f"\n🏆 最佳方法: {best_method[0]}")
print(f"   驗證MAE: {best_method[1]['val_mae']:.6f}")
print(f"   測試MAE: {best_method[1]['test_mae']:.6f}")
print(f"   訓練-驗證差距: {best_method[1]['gap']:.6f}")

print(f"\n📉 效果最差: {worst_method[0]}")
print(f"   驗證MAE: {worst_method[1]['val_mae']:.6f}")

# 改善幅度
improvement = (worst_method[1]['val_mae'] - best_method[1]['val_mae']) / worst_method[1]['val_mae'] * 100
print(f"\n📊 改善幅度: {improvement:.1f}%")


# ==================== 方法推薦 ====================

print("\n\n5️⃣  問題分類和方法推薦...")

# 使用ProblemClassifier分類
for method_name, result in results.items():
    problem_type = ProblemClassifier.classify(result['history'])
    recommended = ProblemClassifier.recommend_method(problem_type)
    
    print(f"\n{method_name}:")
    print(f"   問題類型: {problem_type}")
    print(f"   推薦方法: {recommended}")
    print(f"   驗證MAE: {result['val_mae']:.6f}")


# ==================== 總結 ====================

print("\n\n" + "=" * 70)
print("✅ 測試完成！")
print("=" * 70)

print("\n📁 結果文件:")
print("   ./improved_results/TEST_STOCK_comparison.csv")
print("   ./improved_results/TEST_STOCK_results.json")
print("   ./improved_results/TEST_STOCK_*_best.h5 (6個模型文件)")

print("\n💡 下一步:")
print("   1. 查看對比報告 CSV")
print("   2. 分析各方法的訓練曲線")
print("   3. 根據實際股票數據選擇最佳方法")

print("\n🚀 使用實際數據:")
print("""
   from improved_stock_training import comprehensive_test
   
   # 載入實際股票數據
   X_real, y_real = load_your_stock_data('2330')
   
   # 測試所有方法
   results = comprehensive_test(
       stock_code='2330',
       X_data=X_real,
       y_data=y_real,
       test_all_methods=True
   )
""")

print("=" * 70)
