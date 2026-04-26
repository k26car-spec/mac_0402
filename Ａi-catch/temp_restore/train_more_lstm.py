#!/usr/bin/env python3
"""
批次訓練 LSTM 模型
Train Multiple LSTM Models for New Stocks
"""

import os
import sys

# 添加到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prepare_lstm_data import LSTMDataPreparator
from train_lstm import train_stock_lstm, check_tensorflow

def main():
    """主函數"""
    
    print("\n" + "="*70)
    print("🚀 批次訓練 LSTM 模型")
    print("="*70)
    
    # 檢查 TensorFlow
    if not check_tensorflow():
        return
    
    # 要訓練的新股票
    new_stocks = ["2409", "6669", "3443", "2308", "2382"]
    
    print(f"\n📋 計劃準備和訓練: {', '.join(new_stocks)}")
    print(f"⏰ 預計時間: {len(new_stocks) * 10} 分鐘")
    
    # 創建數據準備器
    preparator = LSTMDataPreparator(data_dir="data/lstm")
    
    results = {}
    
    for i, symbol in enumerate(new_stocks, 1):
        print(f"\n\n{'='*70}")
        print(f"📈 處理 {i}/{len(new_stocks)}: {symbol}")
        print("="*70)
        
        try:
            # 1. 準備數據
            print(f"\n[1/2] 準備 {symbol} 數據...")
            data_result = preparator.prepare_stock_data(symbol, years=2)
            
            if data_result is None:
                print(f"❌ {symbol} 數據準備失敗，跳過")
                continue
            
            # 2. 訓練模型
            print(f"\n[2/2] 訓練 {symbol} 模型...")
            train_result = train_stock_lstm(symbol, epochs=50, batch_size=16)
            
            if train_result:
                results[symbol] = train_result['metrics']
                print(f"✅ {symbol} 完成!")
            else:
                print(f"❌ {symbol} 訓練失敗")
                
        except Exception as e:
            print(f"❌ {symbol} 處理錯誤: {e}")
            continue
    
    # 總結
    print("\n" + "="*70)
    print("📊 訓練總結")
    print("="*70)
    
    for symbol, metrics in results.items():
        print(f"\n{symbol}:")
        print(f"  R²: {metrics['r2']:.4f}")
        print(f"  方向準確率: {metrics['direction_accuracy']:.2%}")
        print(f"  RMSE: {metrics['rmse']:.2f}")
        print(f"  MAPE: {metrics.get('mape', 0):.2f}%")
    
    print("\n" + "="*70)
    print(f"✅ 成功訓練: {len(results)}/{len(new_stocks)} 支股票")
    print("="*70)
    print(f"\n📁 模型位置: models/lstm/")
    print(f"\n現在前端可以使用以下股票:")
    
    # 列出所有可用模型
    all_models = os.listdir("models/lstm")
    trained_stocks = set(f.split("_")[0] for f in all_models if f.endswith("_model.h5"))
    print(f"  {', '.join(sorted(trained_stocks))}")

if __name__ == "__main__":
    main()
