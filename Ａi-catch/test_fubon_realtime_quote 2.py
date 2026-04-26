"""
測試富邦API即時報價
"""
import asyncio
import sys
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

async def test_fubon_quote():
    print("🔍 測試富邦API即時報價")
    print("=" * 70)
    
    # 導入SDK
    try:
        from fubon_neo.sdk import FubonSDK
        from fubon_config import get_decrypted_credentials
        
        # 獲取憑證
        creds = get_decrypted_credentials()
        
        if not creds['user_id'] or not creds['password']:
            print("❌ 憑證未設定")
            return
        
        print(f"✅ 憑證: {creds['user_id'][:4]}****")
        
        # 初始化SDK
        sdk = FubonSDK()
        
        # 登入
        print("登入中...")
        accounts = sdk.login(
            creds['user_id'],
            creds['password'],
            creds['cert_path'],
            creds['cert_password']
        )
        print(f"✅ 登入成功: {accounts}")
        
        # 測試獲取即時報價 - 使用正確的SDK方法
        print("\n測試即時報價...")
        symbol = "2330"
        
        # 方法1: 使用marketdata.rest_client
        try:
            print(f"\n方法1: sdk.marketdata.rest_client.stock.snapshot.quotes()")
            snapshot = sdk.marketdata.rest_client.stock.snapshot.quotes(symbol=symbol)
            print(f"✅ 成功！")
            print(f"返回數據: {snapshot}")
            
            if snapshot and hasattr(snapshot, 'data'):
                data = snapshot.data
                print(f"\n📊 台積電即時報價:")
                print(f"   成交價: {data.get('close', 'N/A')}")
                print(f"   開盤: {data.get('open', 'N/A')}")
                print(f"   最高: {data.get('high', 'N/A')}")
                print(f"   最低: {data.get('low', 'N/A')}")
                print(f"   成交量: {data.get('volume', 'N/A')}")
        except Exception as e:
            print(f"❌ 方法1失敗: {e}")
            import traceback
            traceback.print_exc()
        
        # 登出
        print("\n登出...")
        # sdk.logout()  # 如果有logout方法
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fubon_quote())
