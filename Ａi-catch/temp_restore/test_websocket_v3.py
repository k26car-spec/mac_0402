#!/usr/bin/env python3
"""
WebSocket v3.0 測試腳本
測試 ws://127.0.0.1:8000/ws/test
"""

import asyncio
import websockets
import json
from datetime import datetime


async def test_websocket():
    """測試 WebSocket 連接"""
    uri = "ws://127.0.0.1:8000/ws/test"
    
    print("=" * 60)
    print("🔌 WebSocket v3.0 連接測試")
    print("=" * 60)
    print(f"📡 連接到: {uri}")
    print()
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 連接成功！")
            print()
            
            # 1. 接收連接消息
            print("📥 等待服務器歡迎消息...")
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"✅ 收到: {json.dumps(welcome_data, indent=2, ensure_ascii=False)}")
            print()
            
            # 2. 發送測試消息
            test_messages = [
                "Hello v3.0!",
                "測試中文消息",
                "Test WebSocket Connection",
                "AI Stock Intelligence API"
            ]
            
            for i, msg in enumerate(test_messages, 1):
                print(f"📤 發送消息 #{i}: {msg}")
                await websocket.send(msg)
                
                # 接收回應
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📥 收到回應: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                print()
                
                # 小延遲
                await asyncio.sleep(0.5)
            
            print("=" * 60)
            print("🎉 WebSocket 測試完成！")
            print("=" * 60)
            print()
            print("✅ 所有測試通過：")
            print("   - WebSocket 連接: ✓")
            print("   - 接收消息: ✓")
            print("   - 發送消息: ✓")
            print("   - JSON 格式: ✓")
            print("   - 雙向通信: ✓")
            print()
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ 錯誤: 無法連接到 WebSocket 服務器")
        print("   請確認 FastAPI 服務是否正在運行")
        print("   啟動命令: ./start_api_v3.sh")
        
    except Exception as e:
        print(f"❌ 錯誤: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print()
    print("🚀 開始 WebSocket 測試...")
    print()
    asyncio.run(test_websocket())
