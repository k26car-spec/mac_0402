"""
Yahoo Finance Data Source
获取真实市场数据
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class YahooFinanceSource:
    """Yahoo Finance数据源"""
    
    def __init__(self):
        self.name = "Yahoo Finance"
    
    def get_stock_data(self, symbol: str, period: str = "1mo") -> Optional[Dict[str, Any]]:
        """
        获取股票数据
        
        Args:
            symbol: 股票代码（如：2330）
            period: 时间周期（1d, 5d, 1mo, 3mo, 1y）
        
        Returns:
            包含股票数据的字典
        """
        try:
            # 添加.TW后缀（台股）
            ticker_symbol = f"{symbol}.TW"
            stock = yf.Ticker(ticker_symbol)
            
            # 获取历史数据
            hist = stock.history(period=period)
            
            if hist.empty:
                print(f"⚠️  {symbol} 无数据")
                return None
            
            # 获取最新数据
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest
            
            # 计算技术指标
            ma5 = hist['Close'].tail(5).mean() if len(hist) >= 5 else latest['Close']
            ma20 = hist['Close'].tail(20).mean() if len(hist) >= 20 else latest['Close']
            
            # 返回标准化数据
            data = {
                # 基础数据
                "symbol": symbol,
                "current_price": float(latest['Close']),
                "open": float(latest['Open']),
                "high": float(latest['High']),
                "low": float(latest['Low']),
                "volume": int(latest['Volume']),
                
                # 前一日数据
                "prev_close": float(prev['Close']),
                "prev_high": float(prev['High']),
                "prev_low": float(prev['Low']),
                
                # 计算数据
                "price_change_percent": float((latest['Close'] - prev['Close']) / prev['Close']),
                "avg_volume": int(hist['Volume'].mean()),
                
                # 技术指标
                "ma5": float(ma5),
                "ma20": float(ma20),
                "ma60": float(hist['Close'].mean()),  # 简化版
                
                # 52周高低点
                "high_52w": float(hist['High'].max()),
                "low_52w": float(hist['Low'].min()),
                
                # 元数据
                "data_source": self.name,
                "timestamp": datetime.now().isoformat()
            }
            
            return data
            
        except Exception as e:
            print(f"❌ 获取{symbol}数据失败: {e}")
            return None
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息"""
        try:
            ticker_symbol = f"{symbol}.TW"
            stock = yf.Ticker(ticker_symbol)
            info = stock.info
            
            return {
                "symbol": symbol,
                "name": info.get("longName", symbol),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "market_cap": info.get("marketCap", 0),
            }
        except Exception as e:
            print(f"❌ 获取{symbol}信息失败: {e}")
            return None


# 测试函数
def test_yahoo_finance():
    """测试Yahoo Finance数据源"""
    print("\n" + "="*60)
    print("🧪 测试 Yahoo Finance 数据源")
    print("="*60 + "\n")
    
    source = YahooFinanceSource()
    
    # 测试股票列表
    test_symbols = ["2330", "2317", "2454"]
    
    for symbol in test_symbols:
        print(f"\n📊 获取 {symbol} 数据...")
        data = source.get_stock_data(symbol)
        
        if data:
            print(f"✅ {symbol} 数据获取成功")
            print(f"   当前价: {data['current_price']:.2f}")
            print(f"   涨跌幅: {data['price_change_percent']:.2%}")
            print(f"   成交量: {data['volume']:,}")
            print(f"   MA5: {data['ma5']:.2f}")
            print(f"   MA20: {data['ma20']:.2f}")
        else:
            print(f"❌ {symbol} 数据获取失败")
    
    print("\n" + "="*60)
    print("✅ Yahoo Finance 测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_yahoo_finance()
