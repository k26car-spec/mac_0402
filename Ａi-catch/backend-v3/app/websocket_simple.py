"""
简化版WebSocket实时数据推送
Simplified WebSocket Real-time Data Push
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✅ 新连接: {len(self.active_connections)}个活跃连接")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)
        print(f"❌ 断开连接: {len(self.active_connections)}个活跃连接")
    
    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


# 全局连接管理器
manager = ConnectionManager()


async def get_live_analysis(symbol: str) -> dict:
    """获取实时分析（模拟）"""
    from app.experts import expert_manager, TimeFrame
    from app.data_sources import YahooFinanceSource
    
    # 获取实时数据
    data_source = YahooFinanceSource()
    real_data = data_source.get_stock_data(symbol)
    
    if not real_data:
        return {"error": f"无法获取{symbol}数据"}
    
    # 补充数据
    enhanced_data = {
        **real_data,
        "avg_volume": real_data.get("avg_volume", real_data["volume"]),
        "large_buy_orders": int(real_data["volume"] * 0.05),
        "large_sell_orders": int(real_data["volume"] * 0.05),
        "bid_volume": int(real_data["volume"] * 0.4),
        "ask_volume": int(real_data["volume"] * 0.4),
        "price_change_1d": real_data["price_change_percent"],
        "price_change_5d": real_data["price_change_percent"] * 2,
        "volume_change": 0.1,
        "atr": real_data["current_price"] * 0.02,
        "atr_avg": real_data["current_price"] * 0.02,
        "bb_upper": real_data["current_price"] * 1.05,
        "bb_lower": real_data["current_price"] * 0.95,
        "bb_middle": real_data["current_price"],
        "advance_decline_ratio": 1.2,
        "value_change": 0.1,
        "foreign_net_buy": 100,
        "fear_greed_index": 50,
        "close": real_data["current_price"],
    }
    
    # 运行AI分析
    analysis = await expert_manager.analyze_stock(
        symbol,
        TimeFrame.D1,
        enhanced_data
    )
    
    return {
        "symbol": symbol,
        "price": real_data["current_price"],
        "change": real_data["price_change_percent"],
        "volume": real_data["volume"],
        "signal": analysis["overall_signal"],
        "strength": analysis["overall_strength"],
        "confidence": analysis["overall_confidence"],
        "expert_count": analysis["expert_count"],
        "timestamp": real_data["timestamp"]
    }


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    await manager.connect(websocket)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket连接成功",
            "timestamp": str(asyncio.get_event_loop().time())
        })
        
        while True:
            # 接收客户端请求
            data = await websocket.receive_json()
            
            if data.get("action") == "subscribe":
                # 订阅股票
                symbol = data.get("symbol", "2330")
                
                # 获取实时分析
                analysis = await get_live_analysis(symbol)
                
                # 发送分析结果
                await websocket.send_json({
                    "type": "analysis",
                    "data": analysis
                })
            
            elif data.get("action") == "ping":
                # 心跳
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": str(asyncio.get_event_loop().time())
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
        manager.disconnect(websocket)
