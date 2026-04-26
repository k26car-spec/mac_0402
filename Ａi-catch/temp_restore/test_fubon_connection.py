#!/usr/bin/env python3
# test_fubon_connection.py - 測試富邦 SDK 連接

import asyncio
import os
import sys

# 載入環境變數
env_file = 'fubon.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

print("🧪 測試富邦 SDK 連接\n")
print("=" * 50)

# 測試1: 模組導入
print("\n1️⃣ 測試模組導入...")
try:
    import fubon_neo
    print(f"   ✅ fubon_neo: {fubon_neo.__version__}")
except Exception as e:
    print(f"   ❌ fubon_neo 導入失敗: {e}")
    sys.exit(1)

try:
    from fubon_config import get_decrypted_credentials
    print("   ✅ fubon_config: 可用")
except Exception as e:
    print(f"   ❌ fubon_config 導入失敗: {e}")
    sys.exit(1)

# 測試2: 配置載入
print("\n2️⃣ 測試配置載入...")
try:
    creds = get_decrypted_credentials()
    print(f"   ✅ User ID: {creds['user_id'][:3] if creds['user_id'] else '未設定'}***")
    print(f"   ✅ Password: {'已設定 (******)' if creds['password'] else '未設定'}")
    print(f"   ✅ Cert Path: {creds['cert_path']}")
    
    # 檢查憑證檔案
    if creds['cert_path'] and os.path.exists(creds['cert_path']):
        cert_size = os.path.getsize(creds['cert_path'])
        print(f"   ✅ 憑證檔案存在: {cert_size} bytes")
    else:
        print(f"   ⚠️  憑證檔案不存在: {creds['cert_path']}")
        
except Exception as e:
    print(f"   ❌ 配置載入失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 測試3: 富邦客戶端連接
print("\n3️⃣ 測試富邦客戶端連接...")

async def test_connection():
    try:
        from fubon_client import fubon_client
        print("   📡 正在連接富邦 API...")
        
        success = await fubon_client.connect()
        
        if success:
            print("   ✅ 連接成功！")
            print(f"   ✅ 連接狀態: {fubon_client.is_connected}")
            return True
        else:
            print("   ❌ 連接失敗")
            print("   💡 可能原因:")
            print("      - 憑證路徑不正確")
            print("      - 帳號密碼錯誤")
            print("      - 憑證密碼錯誤")
            print("      - 網路連線問題")
            return False
            
    except Exception as e:
        print(f"   ❌ 連接錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

# 運行測試
try:
    result = asyncio.run(test_connection())
    
    if result:
        print("\n" + "=" * 50)
        print("✅ 富邦 SDK 測試通過！")
        print("=" * 50)
        print("\n💡 下一步:")
        print("   1. 整合到 async_crawler.py")
        print("   2. 整合到 stock_monitor.py")
        print("   3. 重啟監控系統")
    else:
        print("\n" + "=" * 50)
        print("❌ 富邦 SDK 測試失敗")
        print("=" * 50)
        print("\n💡 請檢查:")
        print("   1. fubon.env 中的憑證是否正確")
        print("   2. N123715042.pfx 檔案是否存在")
        print("   3. 富邦證券帳號是否可用")
        
except Exception as e:
    print(f"\n❌ 測試執行錯誤: {e}")
    import traceback
    traceback.print_exc()
