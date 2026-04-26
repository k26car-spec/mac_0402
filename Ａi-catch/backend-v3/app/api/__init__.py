"""
API package
所有 API 路由（簡化版 - 只啟用 premarket）
"""

from . import premarket

__all__ = ["premarket"]

# 其他模塊待數據庫配置完成後啟用
# from . import stocks, cache, analysis, alerts
# __all__ = ["stocks", "cache", "analysis", "alerts", "premarket"]
