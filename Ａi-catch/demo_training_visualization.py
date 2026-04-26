"""
LSTM 訓練可視化演示
快速生成示例訓練曲線，展示訓練完成後的可視化效果

執行時間：< 10 秒
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

# 設置中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 創建輸出目錄
output_dir = "/Users/Mac/Documents/ETF/AI/Ａi-catch/training_results"
os.makedirs(output_dir, exist_ok=True)

print("=" * 70)
print("🎨 LSTM 訓練可視化演示")
print("=" * 70)
print("\n正在生成示例訓練曲線...\n")

# ==================== 模擬訓練數據 ====================

def simulate_training_data(epochs=100, early_stop_epoch=35):
    """模擬訓練過程數據"""
    np.random.seed(42)
    
    # 訓練損失：持續下降
    train_loss = []
    base_loss = 0.015
    for i in range(early_stop_epoch):
        # 指數衰減 + 小波動
        loss = base_loss * np.exp(-i/15) + np.random.normal(0, 0.0002)
        train_loss.append(max(loss, 0.0005))
    
    # 驗證損失：先下降，後期略微上升（防止過擬合）
    val_loss = []
    for i in range(early_stop_epoch):
        # 初期下降
        if i < 20:
            loss = base_loss * 1.2 * np.exp(-i/18) + np.random.normal(0, 0.0003)
        # 後期穩定或略升
        else:
            loss = train_loss[20] * 1.1 + np.random.normal(0, 0.0002)
        val_loss.append(max(loss, 0.0008))
    
    # MAE 數據（與損失類似但數值更大）
    train_mae = [np.sqrt(l) * 1.5 for l in train_loss]
    val_mae = [np.sqrt(l) * 1.5 for l in val_loss]
    
    return train_loss, val_loss, train_mae, val_mae, early_stop_epoch


# ==================== 生成多支股票的模擬數據 ====================

stocks = ['2330', '2317', '2454', '2303', '6770', '3037']
all_results = []

for stock in stocks:
    np.random.seed(hash(stock) % 1000)
    epochs = np.random.randint(30, 45)
    train_loss, val_loss, train_mae, val_mae, actual_epochs = simulate_training_data(epochs=epochs, early_stop_epoch=epochs)
    
    all_results.append({
        'symbol': stock,
        'epoch_losses': train_loss,
        'epoch_val_losses': val_loss,
        'epoch_maes': train_mae,
        'epoch_val_maes': val_mae,
        'epochs_trained': actual_epochs,
        'train_loss': train_loss[-1],
        'test_loss': val_loss[-1],
        'train_mae': train_mae[-1],
        'test_mae': val_mae[-1]
    })

print(f"✅ 已生成 {len(stocks)} 支股票的模擬訓練數據\n")


# ==================== 繪製訓練損失曲線 ====================

print("📊 正在繪製訓練損失曲線...")

n_stocks = len(all_results)
n_cols = 3
n_rows = (n_stocks + n_cols - 1) // n_cols

fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 6*n_rows))
fig.suptitle(
    '🤖 LSTM v2.1 訓練損失曲線 - 演示範例\n'
    '改進版架構：2層LSTM + L2正則化 + Early Stopping + Learning Rate調整',
    fontsize=16,
    fontweight='bold'
)

axes = axes.flatten() if n_stocks > 1 else [axes]

for idx, result in enumerate(all_results):
    ax = axes[idx]
    symbol = result['symbol']
    losses = result['epoch_losses']
    val_losses = result['epoch_val_losses']
    epochs = range(1, len(losses) + 1)
    
    # 繪製損失曲線
    ax.plot(epochs, losses, 'b-', linewidth=2.5, label='訓練損失', alpha=0.9)
    ax.plot(epochs, val_losses, 'r--', linewidth=2.5, label='驗證損失', alpha=0.9)
    
    # 標題和標籤
    ax.set_title(
        f'{symbol} - 損失下降曲線\n'
        f'({len(losses)} epochs, Early Stop)',
        fontsize=13,
        fontweight='bold'
    )
    ax.set_xlabel('Epoch', fontsize=11)
    ax.set_ylabel('MSE Loss (痛苦值)', fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 標註最佳點
    min_idx = np.argmin(val_losses)
    min_loss = val_losses[min_idx]
    ax.plot(min_idx+1, min_loss, 'g*', markersize=18, zorder=5)
    ax.annotate(
        f'最佳點\n{min_loss:.6f}\n(Epoch {min_idx+1})',
        xy=(min_idx+1, min_loss),
        xytext=(15, 15),
        textcoords='offset points',
        bbox=dict(boxstyle='round,pad=0.6', facecolor='yellow', alpha=0.7, edgecolor='green', linewidth=2),
        arrowprops=dict(arrowstyle='->', color='green', linewidth=2),
        fontsize=9,
        fontweight='bold'
    )
    
    # 標註 Early Stop
    ax.axvline(x=len(losses), color='purple', linestyle=':', linewidth=2, alpha=0.6)
    ax.text(len(losses), ax.get_ylim()[1]*0.9, 'Early\nStop', 
            ha='center', va='top', fontsize=9, color='purple', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lavender', alpha=0.7))

# 隱藏多餘子圖
for idx in range(n_stocks, len(axes)):
    axes[idx].axis('off')

plt.tight_layout()

# 保存
plot_path = f"{output_dir}/demo_training_curves_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
plt.savefig(plot_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ 訓練損失曲線已保存: {plot_path}")

plt.show()


# ==================== 繪製 MAE 曲線 ====================

print("\n📊 正在繪製 MAE 曲線...")

fig2, axes2 = plt.subplots(n_rows, n_cols, figsize=(18, 6*n_rows))
fig2.suptitle(
    '📈 LSTM v2.1 MAE (平均絕對誤差) 曲線 - 演示範例\n'
    'MAE 越小，預測越準確',
    fontsize=16,
    fontweight='bold'
)

axes2 = axes2.flatten() if n_stocks > 1 else [axes2]

for idx, result in enumerate(all_results):
    ax = axes2[idx]
    symbol = result['symbol']
    maes = result['epoch_maes']
    val_maes = result['epoch_val_maes']
    epochs = range(1, len(maes) + 1)
    
    # 繪製 MAE 曲線
    ax.plot(epochs, maes, 'g-', linewidth=2.5, label='訓練 MAE', alpha=0.9)
    ax.plot(epochs, val_maes, 'm--', linewidth=2.5, label='驗證 MAE', alpha=0.9)
    
    # 標題和標籤
    ax.set_title(f'{symbol} - MAE 下降曲線', fontsize=13, fontweight='bold')
    ax.set_xlabel('Epoch', fontsize=11)
    ax.set_ylabel('MAE (平均絕對誤差)', fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 標註最佳點
    min_idx = np.argmin(val_maes)
    min_mae = val_maes[min_idx]
    ax.plot(min_idx+1, min_mae, 'r*', markersize=18, zorder=5)
    ax.annotate(
        f'最低 MAE\n{min_mae:.6f}',
        xy=(min_idx+1, min_mae),
        xytext=(15, 15),
        textcoords='offset points',
        bbox=dict(boxstyle='round,pad=0.6', facecolor='lightcoral', alpha=0.7, edgecolor='red', linewidth=2),
        arrowprops=dict(arrowstyle='->', color='red', linewidth=2),
        fontsize=9,
        fontweight='bold'
    )

# 隱藏多餘子圖
for idx in range(n_stocks, len(axes2)):
    axes2[idx].axis('off')

plt.tight_layout()

# 保存
mae_plot_path = f"{output_dir}/demo_mae_curves_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
plt.savefig(mae_plot_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ MAE 曲線已保存: {mae_plot_path}")

plt.show()


# ==================== 繪製統計對比圖 ====================

print("\n📊 正在繪製統計對比圖...")

fig3, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
fig3.suptitle('📊 訓練統計總覽 - 演示範例', fontsize=16, fontweight='bold')

# 1. 最終損失對比
symbols = [r['symbol'] for r in all_results]
test_losses = [r['test_loss'] for r in all_results]
train_losses = [r['train_loss'] for r in all_results]

x = np.arange(len(symbols))
width = 0.35

bars1 = ax1.bar(x - width/2, train_losses, width, label='訓練損失', 
                color='lightblue', edgecolor='navy', linewidth=1.5)
bars2 = ax1.bar(x + width/2, test_losses, width, label='測試損失', 
                color='lightcoral', edgecolor='darkred', linewidth=1.5)

ax1.set_xlabel('股票代碼', fontsize=12, fontweight='bold')
ax1.set_ylabel('MSE Loss', fontsize=12, fontweight='bold')
ax1.set_title('各股票最終損失對比', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(symbols, fontsize=11)
ax1.legend(fontsize=11)
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# 標註平均值
avg_test_loss = np.mean(test_losses)
ax1.axhline(y=avg_test_loss, color='red', linestyle='--', linewidth=2, alpha=0.7,
            label=f'平均測試損失: {avg_test_loss:.6f}')
ax1.legend(fontsize=10)

# 2. 訓練輪數對比
epochs_trained = [r['epochs_trained'] for r in all_results]

bars = ax2.bar(symbols, epochs_trained, color='lightgreen', edgecolor='darkgreen', linewidth=1.5)
ax2.set_xlabel('股票代碼', fontsize=12, fontweight='bold')
ax2.set_ylabel('訓練 Epochs', fontsize=12, fontweight='bold')
ax2.set_title('Early Stopping 實際訓練輪數', fontsize=14, fontweight='bold')
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# 標註平均值和節省的時間
avg_epochs = np.mean(epochs_trained)
ax2.axhline(y=avg_epochs, color='blue', linestyle='--', linewidth=2, alpha=0.7)
ax2.axhline(y=100, color='red', linestyle=':', linewidth=2, alpha=0.5)

ax2.text(len(symbols)/2, avg_epochs+2, f'平均: {avg_epochs:.1f} epochs', 
         ha='center', fontsize=10, fontweight='bold',
         bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
ax2.text(len(symbols)/2, 95, f'最大: 100 epochs', 
         ha='center', fontsize=10, color='red',
         bbox=dict(boxstyle='round', facecolor='mistyrose', alpha=0.7))

# 添加數值標籤
for i, (bar, epoch) in enumerate(zip(bars, epochs_trained)):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{int(epoch)}',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()

# 保存
stats_plot_path = f"{output_dir}/demo_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
plt.savefig(stats_plot_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ 統計對比圖已保存: {stats_plot_path}")

plt.show()


# ==================== 繪製機器學習痛苦減少圖 ====================

print("\n📊 正在繪製「機器學習痛苦減少」示意圖...")

fig4, ax = plt.subplots(1, 1, figsize=(14, 8))

# 選擇一支股票進行詳細展示
demo_stock = all_results[0]
losses = demo_stock['epoch_losses']
val_losses = demo_stock['epoch_val_losses']
epochs = range(1, len(losses) + 1)

# 繪製損失曲線
line1, = ax.plot(epochs, losses, 'b-', linewidth=3, label='訓練損失', alpha=0.9)
line2, = ax.plot(epochs, val_losses, 'r--', linewidth=3, label='驗證損失', alpha=0.9)

# 美化
ax.set_title(
    f'🤖 機器如何一步步減少「痛苦」(Loss)\n'
    f'股票: {demo_stock["symbol"]} | 訓練: {len(losses)} Epochs | '
    f'最終損失: {val_losses[-1]:.6f}',
    fontsize=18,
    fontweight='bold',
    pad=20
)
ax.set_xlabel('訓練輪數 (Epoch)', fontsize=14, fontweight='bold')
ax.set_ylabel('MSE Loss - 機器的「痛苦值」', fontsize=14, fontweight='bold')
ax.legend(fontsize=13, loc='upper right')
ax.grid(True, alpha=0.3, linestyle='--', linewidth=1)

# 添加情緒標籤
pain_levels = [
    (0, losses[0], '😫\n很痛苦', 'top'),
    (len(losses)//3, losses[len(losses)//3], '😐\n有點痛', 'top'),
    (len(losses)*2//3, losses[len(losses)*2//3], '🙂\n還好', 'top'),
    (len(losses)-1, losses[-1], '😊\n很開心', 'bottom')
]

for epoch_idx, loss_val, emoji_text, va in pain_levels:
    ax.plot(epoch_idx+1, loss_val, 'go', markersize=15, zorder=5)
    y_offset = 0.001 if va == 'top' else -0.001
    ax.text(epoch_idx+1, loss_val + y_offset, emoji_text,
            ha='center', va=va, fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', 
                     alpha=0.8, edgecolor='orange', linewidth=2))

# 標註最佳點
min_idx = np.argmin(val_losses)
min_loss = val_losses[min_idx]
ax.plot(min_idx+1, min_loss, 'g*', markersize=25, zorder=6)
ax.annotate(
    f'✨ 最佳狀態！\n損失最小: {min_loss:.6f}\nEpoch {min_idx+1}',
    xy=(min_idx+1, min_loss),
    xytext=(30, -50),
    textcoords='offset points',
    bbox=dict(boxstyle='round,pad=0.8', facecolor='gold', alpha=0.9, 
             edgecolor='darkgreen', linewidth=3),
    arrowprops=dict(arrowstyle='->', color='darkgreen', linewidth=3,
                   connectionstyle='arc3,rad=0.3'),
    fontsize=12,
    fontweight='bold'
)

# 添加說明文字
explanation_text = (
    "📚 機器學習過程：\n\n"
    "1️⃣ 初期：損失很大 → 預測很差 → 機器很「痛苦」😫\n"
    "2️⃣ 中期：逐步學習 → 預測改善 → 痛苦減少 😐\n"
    "3️⃣ 後期：找到規律 → 預測準確 → 機器「開心」😊\n\n"
    "🎯 目標：讓損失越來越小 = 預測越來越準！"
)

ax.text(0.02, 0.98, explanation_text,
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment='top',
        bbox=dict(boxstyle='round,pad=1', facecolor='lightcyan', 
                 alpha=0.9, edgecolor='navy', linewidth=2),
        family='monospace')

plt.tight_layout()

# 保存
pain_plot_path = f"{output_dir}/demo_pain_reduction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
plt.savefig(pain_plot_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ 痛苦減少圖已保存: {pain_plot_path}")

plt.show()


# ==================== 總結 ====================

print("\n" + "=" * 70)
print("🎉 可視化演示完成！")
print("=" * 70)
print(f"\n📁 所有圖表已保存至: {output_dir}/\n")

print("📊 生成的圖表：")
print(f"  1. 訓練損失曲線圖")
print(f"  2. MAE 曲線圖")
print(f"  3. 統計對比圖")
print(f"  4. 機器學習痛苦減少圖")

print("\n💡 這些是使用模擬數據生成的演示圖表")
print("   實際訓練完成後，您將獲得真實的訓練曲線！")

print("\n🚀 開始實際訓練：")
print("   python3 train_lstm_improved_v2.1.py")

print("\n✨ 預期訓練時間：0.8-1.7 小時")
print("=" * 70)


# 自動打開結果目錄
import subprocess
import platform

if platform.system() == 'Darwin':  # macOS
    subprocess.run(['open', output_dir])
    print(f"\n📂 已自動打開結果目錄")
