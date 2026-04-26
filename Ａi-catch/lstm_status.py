#!/usr/bin/env python3
"""
LSTM 狀態快速摘要
執行: python3 lstm_status.py
顯示: 白名單狀態、大盤風向、當日預測
"""
import sys, json, warnings, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from datetime import datetime
import yfinance as yf
import patch_yfinance  # 🆕 導入修補模組

def get_yf_data(symbol, period="3y"):
    # 由於已導入 patch_yfinance，Ticker(symbol) 會自動補上 .TW 或 .TWO
    df = yf.Ticker(symbol).history(period=period)
    return df

NOW = datetime.now().strftime('%Y-%m-%d %H:%M')

print(f"\n{'═'*60}")
print(f"  🤖 LSTM 智慧信號狀態  [{NOW}]")
print(f"{'═'*60}")

# 1. 白名單
try:
    with open('lstm_whitelist.json') as f:
        wl = json.load(f)
    stocks = {k: v for k, v in wl.items() if not k.startswith('_')}
    meta = wl.get('_meta', {})
    print(f"\n📋 白名單：{len(stocks)} 支  (v{meta.get('version','?')}, 更新 {meta.get('last_updated','?')})")
    for sym, info in sorted(stocks.items()):
        print(f"   {sym}  P={info.get('precision',0)*100:.1f}%  R={info.get('recall',0)*100:.1f}%  thr={info['threshold']:.3f}")
except Exception as e:
    print(f"❌ 白名單讀取失敗: {e}")
    sys.exit(1)

if not stocks:
    print("⚠️  白名單為空，請先執行 python3 train_lstm_v5.py")
    sys.exit(0)

# 2. 大盤風向
print(f"\n{'─'*60}")
try:
    from lstm_manager import get_market_context, get_lstm_manager
    mkt = get_market_context()
    icon = '📈' if mkt['status'] == 'BULL' else ('📉' if mkt['status'] == 'BEAR' else '➡️')
    print(f"{icon} 大盤：{mkt['status']}  {mkt['chg_pct']:+.2f}%")
    print(f"   {mkt['desc']}")
except Exception as e:
    print(f"⚠️  大盤風向取得失敗: {e}")
    mkt = {'status': 'NEUTRAL', 'chg_pct': 0.0}

# 3. 預測
print(f"\n{'─'*60}")
print(f"{'股票':^6} {'狀態':^8} {'原始值→閾值':^16} {'信號':^20} {'精確率':^7}")
print(f"{'─'*60}")

try:
    mgr = get_lstm_manager()

    for sym in sorted(stocks.keys()):
        try:
            df = get_yf_data(sym, period="8mo")
            r  = mgr.predict(sym, df)

            if not r['available']:
                print(f"  {sym:^5}  {'N/A':^8}  {r.get('reason',''):^16}")
                continue

            sig  = r['signal']
            conf = r['confidence']
            raw  = r['raw_pred']
            thr  = r['threshold']
            prec = stocks[sym].get('precision', 0) * 100
            mkt_status = mkt['status']

            if sig == 1:
                bonus = 10 + min(conf * 5, 5)
                signal_str = f"🟢 看漲 +{bonus:.0f}分"
            else:
                if mkt_status == 'BULL':
                    penalty = max(2, 5 + min(conf * 5, 5))
                    signal_str = f"🟡 觀望 -{penalty:.0f}分（大盤強減輕）"
                elif mkt_status == 'BEAR':
                    penalty = 15 + min(conf * 10, 10)
                    signal_str = f"🔴 警示 -{penalty:.0f}分（大盤弱加重）"
                else:
                    penalty = 10 + min(conf * 10, 10)
                    signal_str = f"🟠 觀望 -{penalty:.0f}分"

            ratio_str = f"{raw:.3f}→{thr:.3f}"
            print(f"  {sym:^5}  {'✅買進' if sig==1 else '⏸觀望':^8}  {ratio_str:^16}  {signal_str:<22}  {prec:5.1f}%")

        except Exception as e:
            print(f"  {sym:^5}  錯誤: {str(e)[:40]}")

except Exception as e:
    print(f"❌ LSTM Manager 失敗: {e}")

print(f"\n{'═'*60}")
print(f"  使用說明: 看漲 = 信心度 +10~+15, 觀望視大盤調整扣分")
print(f"  進場門檻: 信心度 ≥ 70  (基礎 65 + AI 調整)")
print(f"{'═'*60}\n")
