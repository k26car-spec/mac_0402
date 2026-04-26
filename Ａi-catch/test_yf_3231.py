import yfinance as yf
import pandas as pd

def test_yf():
    symbol = "3231.TW"
    print(f"Testing yfinance for {symbol}...")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d", interval="5m")
    if hist.empty:
        print("Empty history")
    else:
        print(f"Returns {len(hist)} rows")
        print(hist.tail())

if __name__ == "__main__":
    test_yf()
