
import asyncio
import sys
import os
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from dotenv import load_dotenv
load_dotenv('/Users/Mac/Documents/ETF/AI/Ａi-catch/.env')

async def test_fubon_realtime_init():
    print("🔍 測試富邦 SDK init_realtime")
    print("=" * 70)
    
    try:
        from fubon_neo.sdk import FubonSDK
        from fubon_config import get_decrypted_credentials
        
        creds = get_decrypted_credentials()
        sdk = FubonSDK()
        
        print("1. 登入中...")
        accounts = sdk.login(
            creds['user_id'],
            creds['password'],
            creds['cert_path'],
            creds['cert_password']
        )
        print(f"✅ 登入成功")
        
        print("\n2. 初始化 Realtime (WebSocket)...")
        try:
            # 這是關鍵步驟
            sdk.init_realtime() 
            print("✅ init_realtime() 執行完畢")
        except Exception as e:
            print(f"❌ init_realtime() 失敗: {e}")
            return

        print(f"\n3. 檢查 marketdata 屬性: {hasattr(sdk, 'marketdata')}")
        
        if hasattr(sdk, 'marketdata') and sdk.marketdata:
            print("\n4. 測試獲取 2330 報價 (REST)...")
            try:
                # 測試我修復的代碼中使用的 API 路徑
                quote = sdk.marketdata.rest_client.stock.intraday.quote(symbol='2330')
                print(f"✅ Quote 結果: {quote}")
            except Exception as e:
                print(f"❌ Quote 失敗: {e}")
        else:
            print("❌ sdk.marketdata 不存在！")

    except Exception as e:
        print(f"❌ 發生未預期錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fubon_realtime_init())
