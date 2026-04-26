import asyncio
import sys
import os
import json
from datetime import datetime

# 添加專案路徑
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

try:
    from fubon_neo.sdk import FubonSDK
    from dotenv import load_dotenv
    
    # 載入環境變數
    load_dotenv('/Users/Mac/Documents/ETF/AI/Ａi-catch/.env')
    
    # 載入憑證解密函式
    from fubon_config import get_decrypted_credentials
    
except ImportError as e:
    print(f"❌ 導入錯誤: {e}")
    sys.exit(1)

async def main():
    print("🔄 正在登入富邦 API...")
    try:
        creds = get_decrypted_credentials()
        sdk = FubonSDK()
        accounts = sdk.login(creds["user_id"], creds["password"], creds["cert_path"], creds["cert_password"])
        active_account = accounts.data[0]
        print(f"✅ 登入成功: {active_account.account}")
        
        # 初始化行情
        sdk.init_realtime()
        print("✅ 行情初始化完成")
        
        symbol = "2330"  # 台積電
        print(f"\n📊 正在獲取 {symbol} 的原始行情數據...")
        
        # 1. 嘗試 REST API Quote
        print("\n[測試 1] marketdata.rest_client.stock.intraday.quote:")
        try:
            res = sdk.marketdata.rest_client.stock.intraday.quote(symbol=symbol)
            print(f"類型: {type(res)}")
            # 嘗試列出所有屬性
            attrs = [attr for attr in dir(res) if not attr.startswith('__')]
            print(f"屬性列表: {attrs}")
            
            # 打印關鍵值
            for attr in ['date', 'time', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'avgPrice', 
                         'totalVolume', 'dealAmount', 'limitUpPrice', 'limitDownPrice', 'yesterdayVolume', 
                         'previousClose', 'referencePrice', 'lastPrice', 'last_price', 'close_price', 'reference_price']:
                val = getattr(res, attr, 'N/A')
                print(f"  {attr}: {val}")
                
        except Exception as e:
            print(f"❌ REST API 錯誤: {e}")

        # 2. 嘗試 Trading API Query Quote
        print("\n[測試 2] stock.query_symbol_quote:")
        try:
            res = sdk.stock.query_symbol_quote(active_account, symbol)
            print(f"類型: {type(res)}")
            # 如果有 data 屬性
            if hasattr(res, 'data'):
                data = res.data
                print(f"Data 類型: {type(data)}")
                attrs = [attr for attr in dir(data) if not attr.startswith('__')]
                print(f"Data 屬性: {attrs}")
                
                for attr in ['date', 'time', 'open_price', 'high_price', 'low_price', 'close_price', 
                             'last_price', 'reference_price', 'previous_close']:
                    val = getattr(data, attr, 'N/A')
                    print(f"  {attr}: {val}")
            else:
                print(f"直接屬性: {[attr for attr in dir(res) if not attr.startswith('__')]}")

        except Exception as e:
            print(f"❌ Trading API 錯誤: {e}")

    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(main())
