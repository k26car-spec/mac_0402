#!/usr/bin/env python3
"""
測試富邦 WebSocket 連線（Patch websocket 模組）
"""
import ssl

# 創建不驗證 SSL 的 context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Patch websocket 的 run_forever 方法
import websocket

_original_run_forever = websocket.WebSocketApp.run_forever

def patched_run_forever(self, **kwargs):
    # 注入 sslopt 參數
    if 'sslopt' not in kwargs:
        kwargs['sslopt'] = {
            "cert_reqs": ssl.CERT_NONE,
            "check_hostname": False
        }
    return _original_run_forever(self, **kwargs)

websocket.WebSocketApp.run_forever = patched_run_forever
print('✅ websocket.WebSocketApp.run_forever 已 patch')

import os
import sys
import time

# 設定路徑
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

print('=' * 50)
print('富邦 WebSocket 連線測試 (Patch run_forever)')
print('=' * 50)
print()

# 載入環境變數
from dotenv import load_dotenv
load_dotenv('/Users/Mac/Documents/ETF/AI/Ａi-catch/.env')
print('✅ 環境變數已載入')

# 取得憑證
from fubon_config import get_decrypted_credentials
creds = get_decrypted_credentials()
print(f'✅ User ID: {creds["user_id"][:3]}***')

# 連線
from fubon_neo.sdk import FubonSDK
sdk = FubonSDK()

accounts = sdk.login(
    creds['user_id'],
    creds['password'],
    creds['cert_path'],
    creds['cert_password']
)
print('✅ 登入成功')

sdk.init_realtime()
print('✅ init_realtime 成功')

ws_stock = sdk.marketdata.websocket_client.stock
print('✅ 取得 websocket_client')

# 設定回呼
connected = False
data_received = False

def on_connect():
    global connected
    connected = True
    print('🔌 WebSocket 已連線!')

def on_message(msg):
    global data_received
    print(f'📨 收到訊息: {str(msg)[:150]}...')
    if 'books' in str(msg) or 'bids' in str(msg) or 'asks' in str(msg):
        data_received = True
        print('✅ 收到五檔資料!')

def on_error(err):
    print(f'❌ 錯誤: {err}')

def on_disconnect(code, msg):
    print(f'⚠️ 斷線: code={code}, msg={msg}')

ws_stock.on('connect', on_connect)
ws_stock.on('message', on_message)
ws_stock.on('error', on_error)
ws_stock.on('disconnect', on_disconnect)

print()
print('嘗試 WebSocket 連線...')
try:
    ws_stock.connect()
    print('✅ connect() 呼叫完成')
    
    # 等待連線
    for i in range(10):
        time.sleep(0.5)
        if connected:
            break
    
    if connected:
        print()
        print('🎉 WebSocket 連線成功！')
        print('SSL 問題已解決！')
        
        # 訂閱五檔
        print()
        print('訂閱 2330 五檔...')
        ws_stock.subscribe({'channel': 'books', 'symbol': '2330'})
        
        # 等待資料
        for i in range(10):
            time.sleep(0.5)
            if data_received:
                break
                
    else:
        print('⚠️ 連線尚未確認')
        
except Exception as e:
    print(f'❌ 連線錯誤: {e}')
    import traceback
    traceback.print_exc()

# 清理
try:
    ws_stock.disconnect()
except:
    pass

print()
print('測試完成')
