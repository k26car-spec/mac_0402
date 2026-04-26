#!/usr/bin/env python3
"""
LSTM 修復重訓腳本 v5.1
========================
問題診斷：
  1. 白名單目前是 0 支（total_stocks=0）
  2. 召回率門檻 40% 太嚴，讓精確但保守的模型全被淘汰
  3. 最近幾次訓練都在訓練只有 2-4 支股票

修復策略：
  - 降低 RECALL_THRESHOLD 至 25%
  - 高精確率特例（P >= 70%）只需 R >= 20%
  - 批次重訓全部有 .h5 模型的股票
  - 詳細顯示每支股票未過門檻的原因

使用：
    python3 fix_lstm_retrain.py --batch 10    # 每批 10 支，加快速度
    python3 fix_lstm_retrain.py --stocks 2337,2344,2330  # 指定股票
    python3 fix_lstm_retrain.py --quick       # 只重訓前 20 支（快速驗證）
"""

import subprocess, sys, os, json, time
from datetime import datetime

MODEL_DIR = "models/lstm_smart_entry"
WHITELIST_PATH = "lstm_whitelist.json"

def get_all_model_stocks():
    """取得所有已有模型的股票清單"""
    stocks = []
    if os.path.isdir(MODEL_DIR):
        for f in sorted(os.listdir(MODEL_DIR)):
            if f.endswith("_model.h5"):
                sym = f.replace("_model.h5", "")
                stocks.append(sym)
    return stocks

def get_whitelist_stocks():
    """取得白名單股票"""
    try:
        with open(WHITELIST_PATH) as f:
            wl = json.load(f)
        return [k for k in wl.keys() if not k.startswith("_")]
    except:
        return []

def show_current_status():
    """顯示目前狀況"""
    models = get_all_model_stocks()
    whitelist = get_whitelist_stocks()
    
    print("=" * 60)
    print("📊 LSTM 目前狀況診斷")
    print("=" * 60)
    print(f"  📁 模型數量   : {len(models)} 支")
    print(f"  📋 白名單數量 : {len(whitelist)} 支 {'⚠️  為空！' if len(whitelist)==0 else ''}")
    
    if whitelist:
        print(f"  白名單: {whitelist}")
    
    # 讀最新訓練報告
    reports = sorted([f for f in os.listdir(".") if f.startswith("train_v5_report_")])
    if reports:
        latest = reports[-1]
        print(f"\n  📄 最新報告: {latest}")
        try:
            with open(latest) as f:
                r = json.load(f)
            print(f"  訓練日期: {r['train_date']}")
            print(f"  合格/總數: {r['ok']}/{r['total']}")
        except:
            pass
    
    print()
    return models, whitelist

def run_retrain(stocks: list, batch_label: str = ""):
    """執行重訓"""
    if not stocks:
        print("❌ 無股票可訓練")
        return False
    
    stocks_str = ",".join(stocks)
    cmd = [
        sys.executable, "train_lstm_v5.py",
        "--stocks", stocks_str
    ]
    
    label = f" [{batch_label}]" if batch_label else ""
    print(f"\n{'─'*60}")
    print(f"🔄 開始重訓{label}: {len(stocks)} 支")
    print(f"   股票: {stocks}")
    print(f"{'─'*60}")
    
    start_t = time.time()
    result = subprocess.run(cmd, capture_output=False, text=True)
    elapsed = time.time() - start_t
    
    print(f"\n✅ 完成（{elapsed/60:.1f} 分鐘）")
    return result.returncode == 0

def main():
    import argparse
    parser = argparse.ArgumentParser(description='LSTM 修復重訓工具 v5.1')
    parser.add_argument('--stocks', type=str, default='',
                        help='指定股票（逗號分隔）')
    parser.add_argument('--quick', action='store_true',
                        help='快速模式：只重訓前 20 支')
    parser.add_argument('--batch', type=int, default=0,
                        help='批次大小（0=一次全部）')
    parser.add_argument('--all', action='store_true',
                        help='重訓所有已有模型股票')
    parser.add_argument('--core', action='store_true',
                        help='只重訓核心重要股票')
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🔧 LSTM 修復重訓工具 v5.1")
    print(f"   新門檻: Precision > 55%, Recall > 25%")
    print(f"   高精確率特例: P >= 70% → Recall >= 20%")
    print("=" * 60)
    
    # 顯示目前狀況
    all_models, whitelist = show_current_status()
    
    # 決定訓練清單
    if args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(",")]
        print(f"📋 指定股票: {stock_list}")
    elif args.core:
        # 核心股票（台灣重要科技股）
        stock_list = [
            '2330', '2454', '2317', '2382', '2379',
            '2337', '2344', '2357', '3711', '2308',
            '2327', '2303', '2301', '6770', '3443',
            '2377', '2371', '2408', '2409', '6442',
        ]
        # 過濾出有模型的
        stock_list = [s for s in stock_list if s in all_models]
        print(f"📋 核心股票（有模型的）: {len(stock_list)} 支: {stock_list}")
    elif args.quick:
        stock_list = all_models[:20]
        print(f"📋 快速模式（前 20 支）: {stock_list}")
    elif args.all:
        stock_list = all_models
        print(f"📋 全部重訓: {len(stock_list)} 支")
    else:
        # 預設：重訓有模型的前 30 支核心股票
        stock_list = all_models[:30]
        print(f"📋 預設（前 30 支）: {len(stock_list)} 支")
        print("   提示：加 --all 可重訓所有 {len(all_models)} 支")
    
    if not stock_list:
        print("❌ 找不到可訓練的股票")
        return
    
    total_start = time.time()
    
    if args.batch > 0:
        # 批次模式
        batches = [stock_list[i:i+args.batch] for i in range(0, len(stock_list), args.batch)]
        print(f"\n⚙️  批次模式：{len(batches)} 批，每批 {args.batch} 支")
        
        for i, batch in enumerate(batches, 1):
            run_retrain(batch, f"批次 {i}/{len(batches)}")
    else:
        # 一次全部
        run_retrain(stock_list)
    
    # 最終統計
    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"🎯 重訓完成！總耗時 {total_elapsed/60:.1f} 分鐘")
    
    # 讀取最新白名單
    _, final_whitelist = show_current_status()
    
    print(f"\n📋 白名單結果: {len(final_whitelist)} 支")
    if final_whitelist:
        # 顯示詳細
        try:
            with open(WHITELIST_PATH) as f:
                wl = json.load(f)
            print()
            for sym, info in wl.items():
                if sym.startswith("_"):
                    continue
                print(f"  ✅ {sym}  P={info.get('precision',0)*100:.1f}%  "
                      f"R={info.get('recall',0)*100:.1f}%  "
                      f"thr={info.get('threshold',0):.2f}  "
                      f"v={info.get('version','?')}")
        except:
            pass
    
    print(f"\n{'='*60}")
    print("👉 下一步：")
    print("   python3 lstm_backtest.py --threshold auto --period 3m")
    print("   (確認 backtest 結果改善)")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
