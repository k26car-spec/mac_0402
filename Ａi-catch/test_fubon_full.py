"""
富邦API完整連接測試
測試時間: 2025-12-17 09:10 (開盤時間)
"""

import sys
import os
import asyncio

# 設置路徑
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

print("=" * 60)
print("🔍 富邦API完整連接測試")
print("=" * 60)
print()

# 步驟1: 檢查環境變數
print("步驟1: 檢查環境變數")
print("-" * 60)

# 確保環境變數存在
os.environ['ENCRYPTION_SECRET_KEY'] = 'K@bm47g7117'

encryption_key = os.environ.get('ENCRYPTION_SECRET_KEY')
print(f"✅ ENCRYPTION_SECRET_KEY: {encryption_key}")
print()

# 步驟2: 測試憑證解密
print("步驟2: 測試憑證解密")
print("-" * 60)

try:
    from fubon_config import get_decrypted_credentials
    
    creds = get_decrypted_credentials()
    
    if creds['user_id']:
        print(f"✅ User ID 解密成功: {creds['user_id'][:4]}****")
    else:
        print("❌ User ID 解密失敗")
    
    if creds['password']:
        print(f"✅ Password 解密成功 (長度: {len(creds['password'])})")
    else:
        print("❌ Password 解密失敗")
    
    if creds['cert_path']:
        print(f"✅ Cert Path: {creds['cert_path']}")
        # 檢查檔案存在
        if os.path.exists(creds['cert_path']):
            print(f"   ✅ 憑證檔案存在")
        else:
            print(f"   ❌ 憑證檔案不存在")
    
    if creds['cert_password']:
        print(f"✅ Cert Password 解密成功")
    else:
        print("❌ Cert Password 解密失敗")
    
    print()
    
except Exception as e:
    print(f"❌ 憑證解密錯誤: {e}")
    print()
    sys.exit(1)

# 步驟3: 檢查富邦SDK
print("步驟3: 檢查富邦SDK")
print("-" * 60)

try:
    import fubon_neo
    print(f"✅ fubon-neo 已安裝")
    if hasattr(fubon_neo, '__version__'):
        print(f"   版本: {fubon_neo.__version__}")
    print()
except ImportError as e:
    print(f"❌ fubon-neo 未安裝: {e}")
    print()
    sys.exit(1)

# 步驟4: 測試FubonClient連接
print("步驟4: 測試FubonClient連接")
print("-" * 60)

try:
    from fubon_client import fubon_client
    
    async def test_connection():
        print("正在連接富邦API...")
        success = await fubon_client.connect()
        
        if success:
            print("✅ 富邦API連接成功！")
            print(f"   連接狀態: {fubon_client.is_connected}")
            return True
        else:
            print("❌ 富邦API連接失敗")
            print(f"   連接狀態: {fubon_client.is_connected}")
            return False
    
    connected = asyncio.run(test_connection())
    print()
    
    if not connected:
        print("⚠️ 無法建立連接，可能原因:")
        print("   1. API權限未開通")
        print("   2. 憑證無效或過期")
        print("   3. 網路連接問題")
        print("   4. 富邦API伺服器問題")
        sys.exit(1)
    
except Exception as e:
    print(f"❌ 連接測試錯誤: {e}")
    import traceback
    traceback.print_exc()
    print()
    sys.exit(1)

# 步驟5: 測試獲取股價
print("步驟5: 測試獲取即時股價")
print("-" * 60)

try:
    async def test_quote():
        # 測試台積電
        symbol = "2330"
        print(f"正在獲取 {symbol} 台積電 報價...")
        
        quote = await fubon_client.get_quote(symbol)
        
        if quote:
            print(f"✅ 成功獲取報價！")
            print(f"   股票: {quote.get('symbol', 'N/A')}")
            print(f"   價格: {quote.get('close', 'N/A')}")
            print(f"   成交量: {quote.get('volume', 'N/A')}")
            return True
        else:
            print(f"❌ 無法獲取報價")
            return False
    
    got_quote = asyncio.run(test_quote())
    print()
    
except Exception as e:
    print(f"❌ 獲取報價錯誤: {e}")
    import traceback
    traceback.print_exc()
    print()

# 最終結果
print("=" * 60)
print("📊 測試結果總結")
print("=" * 60)

if connected and got_quote:
    print("✅ 所有測試通過！")
    print("✅ 富邦API可以正常使用")
    print()
    print("💡 建議:")
    print("   重啟後端服務以啟用真實股價")
elif connected:
    print("⚠️ 連接成功但無法獲取報價")
    print()
    print("💡 可能原因:")
    print("   1. 現在可能不在交易時間")
    print("   2. API權限不完整")
else:
    print("❌ 連接失敗")
    print()
    print("💡 需要檢查:")
    print("   1. 富邦證券帳戶API權限")
    print("   2. 憑證是否有效")
    print("   3. 聯繫富邦客服確認")

print()
