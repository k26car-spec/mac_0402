"""
準確率評估背景任務
Accuracy Evaluation Background Task

定期評估待處理的預測，追蹤價格變化
"""

import asyncio
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class AccuracyEvaluationTask:
    """
    準確率評估背景任務
    
    定期獲取價格並評估待處理的預測
    """
    
    def __init__(
        self,
        api_base: str = "http://localhost:8000",
        evaluation_interval: float = 5.0,  # 每 5 秒評估一次
    ):
        self.api_base = api_base
        self.evaluation_interval = evaluation_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._price_cache: dict = {}  # 價格快取
    
    async def start(self):
        """啟動背景任務"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("🔄 準確率評估背景任務已啟動")
    
    async def stop(self):
        """停止背景任務"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 準確率評估背景任務已停止")
    
    async def _run_loop(self):
        """主循環"""
        while self._running:
            try:
                await self._evaluate()
                await asyncio.sleep(self.evaluation_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"評估循環錯誤: {e}")
                await asyncio.sleep(1)
    
    async def _evaluate(self):
        """執行評估"""
        from app.ml.order_flow.accuracy_evaluator import accuracy_evaluator
        
        await accuracy_evaluator.evaluate_pending(self._get_price)
    
    async def _get_price(self, symbol: str) -> float:
        """獲取股票當前價格"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"{self.api_base}/api/realtime/quote/{symbol}"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return float(data.get("price", 0))
        except Exception as e:
            logger.debug(f"獲取價格失敗: {e}")
        
        return 0.0
    
    def is_running(self) -> bool:
        return self._running


# 全域任務實例
accuracy_evaluation_task = AccuracyEvaluationTask()


async def start_accuracy_evaluation():
    """啟動準確率評估"""
    await accuracy_evaluation_task.start()


async def stop_accuracy_evaluation():
    """停止準確率評估"""
    await accuracy_evaluation_task.stop()
