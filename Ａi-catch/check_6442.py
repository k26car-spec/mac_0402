import yfinance as yf
from eps_super_scanner import analyze_super_stock

res = analyze_super_stock("6442")
print("6442 分析結果:", res)

# 手動印出 6442 數值
ticker = yf.Ticker("6442.TW")
info = ticker.info
print("\n--- 6442 原始資料 ---")
print("現價:", info.get('currentPrice') or info.get('regularMarketPrice'))
print("目標價:", info.get('targetMeanPrice'))
print("Forward EPS:", info.get('forwardEps'))
print("Trailing EPS:", info.get('trailingEps'))

hist = ticker.history(period="6mo")
if not hist.empty:
    close = hist['Close']
    ma10 = close.rolling(10).mean()
    recent_close = close[-60:]
    recent_ma10 = ma10[-60:]
    above_ma10_days = sum(recent_close > recent_ma10)
    print("過去60天在MA10之上天數:", above_ma10_days, "比例:", (above_ma10_days/60)*100, "%")
