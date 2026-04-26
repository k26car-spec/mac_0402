"""
生成6種模型對比可視化圖表
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 設置中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 讀取數據
df = pd.read_csv('./improved_results/TEST_STOCK_comparison.csv')

print("=" * 70)
print("📊 生成可視化對比圖表...")
print("=" * 70)

# 創建圖表
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('6種改進模型完整對比分析 - TEST_STOCK', fontsize=16, fontweight='bold')

# ========== 圖1: 驗證MAE對比 ==========
ax1 = axes[0, 0]
colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
bars = ax1.bar(df['方法'], df['驗證MAE'], color=colors, edgecolor='black', linewidth=1.5)

# 標註數值
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.4f}',
             ha='center', va='bottom', fontsize=9, fontweight='bold')

ax1.set_xlabel('模型方法', fontsize=12, fontweight='bold')
ax1.set_ylabel('驗證 MAE', fontsize=12, fontweight='bold')
ax1.set_title('🏆 驗證MAE對比 (越低越好)', fontsize=13, fontweight='bold')
ax1.grid(axis='y', alpha=0.3, linestyle='--')
ax1.set_xticklabels(df['方法'], rotation=45, ha='right')

# 標記最佳
best_idx = df['驗證MAE'].idxmin()
bars[best_idx].set_edgecolor('gold')
bars[best_idx].set_linewidth(3)

# ========== 圖2: 訓練-驗證差距對比 ==========
ax2 = axes[0, 1]
gaps = df['訓練-驗證差距']
colors2 = ['green' if abs(g) < 0.002 else 'orange' if abs(g) < 0.004 else 'red' for g in gaps]

bars2 = ax2.bar(df['方法'], gaps, color=colors2, edgecolor='black', linewidth=1.5, alpha=0.7)

# 標註數值
for bar, gap in zip(bars2, gaps):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{gap:+.5f}',
             ha='center', va='bottom' if height > 0 else 'top', 
             fontsize=9, fontweight='bold')

ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.set_xlabel('模型方法', fontsize=12, fontweight='bold')
ax2.set_ylabel('訓練-驗證差距', fontsize=12, fontweight='bold')
ax2.set_title('🎯 泛化能力對比 (越接近0越好)', fontsize=13, fontweight='bold')
ax2.grid(axis='y', alpha=0.3, linestyle='--')
ax2.set_xticklabels(df['方法'], rotation=45, ha='right')

# ========== 圖3: 訓練效率對比 ==========
ax3 = axes[1, 0]
epochs = df['實際Epochs']
colors3 = ['#27ae60' if e < 50 else '#f39c12' if e < 80 else '#e74c3c' for e in epochs]

bars3 = ax3.bar(df['方法'], epochs, color=colors3, edgecolor='black', linewidth=1.5)

# 標註數值
for bar in bars3:
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height)}',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

ax3.set_xlabel('模型方法', fontsize=12, fontweight='bold')
ax3.set_ylabel('實際訓練 Epochs', fontsize=12, fontweight='bold')
ax3.set_title('⚡ 訓練效率對比 (越少越快)', fontsize=13, fontweight='bold')
ax3.grid(axis='y', alpha=0.3, linestyle='--')
ax3.set_xticklabels(df['方法'], rotation=45, ha='right')

# ========== 圖4: 綜合性能雷達圖 ==========
ax4 = axes[1, 1]

# 準備數據（需要標準化）
from sklearn.preprocessing import MinMaxScaler

# 選擇前3名
top3 = df.nsmallest(3, '驗證MAE')

# 4個維度：驗證MAE(越低越好), 差距(越小越好), Epochs(越少越好), 訓練MAE(越低越好)
metrics = ['驗證MAE', '|差距|', 'Epochs', '訓練MAE']
angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
angles += angles[:1]

# 標準化（反轉，使得越高越好）
scaler = MinMaxScaler()
top3_data = top3.copy()
top3_data['|差距|'] = abs(top3_data['訓練-驗證差距'])
top3_data['Epochs'] = top3_data['實際Epochs']

# 反轉（使得越高越好）
for col in ['驗證MAE', '|差距|', 'Epochs', '訓練MAE']:
    top3_data[col] = 1 - scaler.fit_transform(top3_data[[col]])

ax4 = plt.subplot(2, 2, 4, projection='polar')

colors_radar = ['#2ecc71', '#3498db', '#f39c12']
for idx, (i, row) in enumerate(top3_data.iterrows()):
    values = row[['驗證MAE', '|差距|', 'Epochs', '訓練MAE']].tolist()
    values += values[:1]
    ax4.plot(angles, values, 'o-', linewidth=2, label=row['方法'], color=colors_radar[idx])
    ax4.fill(angles, values, alpha=0.15, color=colors_radar[idx])

ax4.set_xticks(angles[:-1])
ax4.set_xticklabels(metrics, fontsize=10)
ax4.set_ylim(0, 1)
ax4.set_title('📊 Top 3 綜合性能雷達圖\n(越往外越好)', fontsize=13, fontweight='bold', pad=20)
ax4.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
ax4.grid(True)

plt.tight_layout()

# 保存
output_path = './improved_results/TEST_STOCK_comparison_chart.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"\n✅ 對比圖表已保存: {output_path}")

plt.show()

print("\n" + "=" * 70)
print("✅ 可視化完成！")
print("=" * 70)
