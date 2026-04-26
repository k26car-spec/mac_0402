"""
Fubon数据源适配器
Fubon Data Source Adapter for AI Stock System
"""

from typing import Dict, Any, Optional
from datetime import datetime
import os
import sys

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from fubon_stock_info import FubonStockInfo
except ImportError:
    # 如果无法导入，使用简化版本
    print("⚠️  未找到fubon_stock_info模块，使用简化版本")
    FubonStockInfo = None


class FubonDataSource:
    """
    Fubon数据源
    整合Fubon API到AI系统
   """
    
    def __init__(self):
        self.name = "Fubon Securities"
        if FubonStockInfo:
            self.fubon_info = FubonStockInfo()
        else:
            self.fubon_info = None
    
    def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取股票数据（从Fubon API）
        
        目前Fubon主要提供股票名称
        价格数据仍然使用Yahoo Finance
        
        Args:
            symbol: 股票代码（如：2330）
        
        Returns:
            包含股票数据的字典
        """
        try:
            # 1. 从Fubon获取股票名称
            stock_name = self.fubon_info.get_stock_name(symbol)
            
            # 2. 从Yahoo Finance获取价格数据（Fubon API暂不提供实时价格）
            import yfinance as yf
            
            ticker_symbol = f"{symbol}.TW"
            stock = yf.Ticker(ticker_symbol)
            hist = stock.history(period="1d")
            
            if hist.empty:
                print(f"⚠️  {symbol} 无数据")
                return None
            
            latest = hist.iloc[-1]
            
            # 3. 组合数据
            data = {
                # 基础信息（来自Fubon）
                "symbol": symbol,
                "name": stock_name if stock_name else symbol,
                "data_source": "Fubon + Yahoo Finance",
                
                # 价格数据（来自Yahoo）
                "current_price": float(latest['Close']),
                "open": float(latest['Open']),
                "high": float(latest['High']),
                "low": float(latest['Low']),
                "volume": int(latest['Volume']),
                
                # 技术指标（简化）
                "ma5": float(hist['Close'].tail(5).mean()) if len(hist) >= 5 else float(latest['Close']),
                "ma20": float(hist['Close'].tail(20).mean()) if len(hist) >= 20 else float(latest['Close']),
                "ma60": float(hist['Close'].mean()),
                
                # 元数据
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"✅ Fubon数据源: {symbol} {stock_name if stock_name else ''}")
            return data
            
        except Exception as e:
            print(f"❌ Fubon数据源获取失败 {symbol}: {e}")
            return None
    
    def batch_get_names(self, symbols: list) -> Dict[str, str]:
        """批量获取股票名称"""
        return self.fubon_info.batch_get_names(symbols)


# 测试函数
def test_fubon_data_source():
    """测试Fubon数据源"""
    print("\n" + "="*70)
    print("🧪 测试Fubon数据源")
    print("="*70 + "\n")
    
    source = FubonDataSource()
    
    # 测试股票列表
    test_symbols = ["2330", "2317", "2454"]
    
    for symbol in test_symbols:
        print(f"\n📊 获取 {symbol} 数据...")
        data = source.get_stock_data(symbol)
        
        if data:
            print(f"   名称: {data.get('name', 'N/A')}")
            print(f"   当前价: {data['current_price']:.2f}")
            print(f"   成交量: {data['volume']:,}")
        else:
            print(f"   ❌ 获取失败")
    
    print("\n" + "="*70)
    print("✅ Fubon数据源测试完成")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_fubon_data_source()
