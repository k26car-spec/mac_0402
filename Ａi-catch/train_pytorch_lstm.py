"""
train_pytorch_lstm.py
使用 PyTorch (LSTM + Attention) 與 v4 特徵產生器訓練模型
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import yfinance as yf
from datetime import datetime
import numpy as np
from lstm_feature_builder_v4 import build_dataset

# ──────────────────────────────────────────
# 1. 您的最強設計：LSTM + Attention 模型
# ──────────────────────────────────────────

class LSTMWithAttention(nn.Module):
    def __init__(self, input_size=15, seq_len=20):
        super().__init__()
        
        self.lstm1 = nn.LSTM(input_size, 64, batch_first=True)
        
        # ⚠️ 修正：在 RNN/LSTM 中，通常正規化「特徵維度 (64)」，並使用 LayerNorm 最穩定
        # LayerNorm 原生支援 (batch_size, seq_len, features) 的結構
        self.ln1   = nn.LayerNorm(64)
        self.drop1 = nn.Dropout(0.3)
        
        self.lstm2 = nn.LSTM(64, 32, batch_first=True)
        self.ln2   = nn.LayerNorm(32)
        self.drop2 = nn.Dropout(0.3)
        
        # 新增：Attention — 學習哪幾天最重要
        self.attn = nn.Linear(32, 1)
        
        self.fc = nn.Sequential(
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, 1),
            nn.Sigmoid()  # 輸出 0 ~ 1 機率
        )
    
    def forward(self, x):
        # 第一層 LSTM
        out, _ = self.lstm1(x)
        out = self.drop1(self.ln1(out))
        
        # 第二層 LSTM
        out, _ = self.lstm2(out)
        out = self.drop2(self.ln2(out))
        
        # Attention 加權：讓模型自己決定重視哪幾天 (1 到 seq_len 天的權重分配)
        weights = torch.softmax(self.attn(out), dim=1)   # shape: (batch, seq_len, 1)
        context = (weights * out).sum(dim=1)             # shape: (batch, 32)
        
        return self.fc(context)


# ──────────────────────────────────────────
# 2. 訓練流程 (Training Pipeline)
# ──────────────────────────────────────────

def smooth_labels(y, epsilon=0.05):
    """應用 Label Smoothing，把 0/1 軟化為更具連續性的機率分佈"""
    return y * (1 - epsilon) + epsilon * 0.5


def train_and_evaluate(X_tr, y_tr, X_va, y_va, device, epochs=40, batch_size=64, patience=8):
    """單次訓練與評估 (無保存模型，純算 WF 分數)"""
    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_tr), torch.tensor(y_tr).unsqueeze(1)),
        batch_size=batch_size, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(torch.tensor(X_va), torch.tensor(y_va).unsqueeze(1)),
        batch_size=batch_size, shuffle=False
    )
    
    model = LSTMWithAttention(input_size=15, seq_len=20).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4) # AdamW
    
    best_loss = float('inf')
    best_acc = 0.0
    early_stop_counter = 0
    
    for epoch in range(epochs):
        model.train()
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_x)
            
            # 🔥 Label Smoothing
            batch_y_smooth = smooth_labels(batch_y, epsilon=0.05)
            loss = criterion(outputs, batch_y_smooth)
            
            loss.backward()
            optimizer.step()
            
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)   # 驗證時用原始硬標籤算 loss
                val_loss += loss.item() * batch_x.size(0)
                
                preds = (outputs > 0.5).float()
                correct += (preds == batch_y).sum().item()
                total += batch_y.size(0)
                
        val_loss /= len(val_loader.dataset)
        val_acc = correct / total
        
        if val_loss < best_loss:
            best_loss = val_loss
            best_acc = val_acc
            early_stop_counter = 0
        else:
            early_stop_counter += 1
            if early_stop_counter >= patience:
                break
                
    return best_acc


def train_model(symbol: str, epochs: int = 50, batch_size: int = 64, n_splits: int = 5):
    print(f"\n🚀 開始訓練 [{symbol}] PyTorch Attention LSTM模型...")
    
    hist = yf.Ticker(f"{symbol}.TW").history(period="5y")
    if len(hist) < 300:
        print(f"❌ {symbol} 數據不足，跳過。")
        return
    
    X, y = build_dataset(hist, seq_len=20, horizon=5, norm_window=60)
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    
    # ──────────────────────────────────────────
    # 🌟 Walk-Forward Validation (滾動時間窗驗證)
    # ──────────────────────────────────────────
    print(f"🔄 進行 Walk-Forward Validation ({n_splits} 折)...")
    fold_size = len(X) // (n_splits + 1)
    wf_results = []
    
    for i in range(1, n_splits + 1):
        train_end = i * fold_size
        val_end   = train_end + fold_size
        
        X_tr, y_tr = X[:train_end], y[:train_end]
        X_va, y_va = X[train_end:val_end], y[train_end:val_end]
        
        acc = train_and_evaluate(X_tr, y_tr, X_va, y_va, device, epochs=30, batch_size=batch_size)
        wf_results.append(acc)
        print(f"  > Fold {i}: Acc={acc:.1%}")

    mean_acc = np.mean(wf_results)
    std_acc  = np.std(wf_results)
    print(f"📊 WF 驗證總結 | 平均勝率: {mean_acc:.1%} | 標準差: {std_acc:.1%} (越小越穩)")
    
    if mean_acc < 0.50:
        print(f"⚠️ 警告: 該模型在滾動市場測試中平均勝率 < 50%。")

    # ──────────────────────────────────────────
    # 🌟 最終生產環境模型訓練 (在 80% 資料上訓練，保留最後 20% 當驗證與存檔)
    # ──────────────────────────────────────────
    print(f"\n💾 開始訓練最終模型並存檔...")
    split_idx = int(len(X) * 0.8)
    X_train, y_train = X[:split_idx], y[:split_idx]
    X_val, y_val     = X[split_idx:], y[split_idx:]
    
    train_loader = DataLoader(TensorDataset(torch.tensor(X_train), torch.tensor(y_train).unsqueeze(1)), batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(TensorDataset(torch.tensor(X_val), torch.tensor(y_val).unsqueeze(1)), batch_size=batch_size, shuffle=False)
    
    final_model = LSTMWithAttention(input_size=15, seq_len=20).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.AdamW(final_model.parameters(), lr=0.001, weight_decay=1e-4)
    
    best_loss = float('inf')
    patience_limit = 8
    early_stop_counter = 0
    os.makedirs("models/pytorch_smart_entry", exist_ok=True)
    save_path = f"models/pytorch_smart_entry/{symbol}_model.pt"

    for epoch in range(epochs):
        final_model.train()
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = final_model(batch_x)
            
            # 🔥 Label Smoothing 在最終訓練時依然生效
            batch_y_smooth = smooth_labels(batch_y, epsilon=0.05)
            loss = criterion(outputs, batch_y_smooth)
            
            loss.backward()
            optimizer.step()
            
        final_model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = final_model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item() * batch_x.size(0)
        val_loss /= len(val_loader.dataset)
        
        if val_loss < best_loss:
            best_loss = val_loss
            early_stop_counter = 0
            torch.save(final_model.state_dict(), save_path)
        else:
            early_stop_counter += 1
            if early_stop_counter >= patience_limit:
                break
                
    print(f"✅ [{symbol}] 終極模型儲存於 {save_path}\n")


# ──────────────────────────────────────────
# 3. 執行入口：挑選「嚴選白名單」進行重訓
# ──────────────────────────────────────────
if __name__ == "__main__":
    import random
    
    # 先前 LSTM 回測中 勝率 >= 40% 且 盈虧比 >= 1.3 的嚴選名單 (請依據真實回測結果修正)
    target_stocks = ["2337", "2454", "3163", "6285"]
    
    # 確保再現性
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    for sym in target_stocks:
        train_model(symbol=sym, epochs=50)
