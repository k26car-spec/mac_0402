"""
智能股價預測 API
Smart Price Prediction API

提供：
- GET  /api/prediction/{symbol}?horizon=2       單股預測
- GET  /api/prediction/accuracy/{symbol}        準確率查詢
- POST /api/prediction/train/{symbol}           觸發訓練
- POST /api/prediction/verify-now              手動觸發驗證
- GET  /api/prediction/leaderboard             所有股票準確率排行
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from datetime import date, timedelta
import logging
from typing import Optional

from app.services.smart_prediction_service import prediction_engine, prediction_recorder

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/prediction", tags=["Smart Prediction"])

# 常用股票名稱映射
STOCK_NAMES = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科",
    "2382": "廣達", "2308": "台達電", "2881": "富邦金",
    "2882": "國泰金", "2412": "中華電", "3008": "大立光",
    "2303": "聯電", "2337": "旺宏", "2379": "瑞昱",
    "2357": "華碩", "2395": "研華", "6505": "台塑化",
}


@router.get("/{symbol}")
async def get_prediction(
    symbol: str,
    horizon: int = Query(default=2, ge=1, le=5, description="預測天數（1-5）"),
    save: bool = Query(default=True, description="是否儲存到 DB"),
    background_tasks: BackgroundTasks = None,
):
    """
    取得個股 N 日股價預測
    - 使用 LSTM V2 模型（或技術指標備援）
    - 自動儲存到 PostgreSQL 供事後驗證
    """
    try:
        pred = await prediction_engine.predict(symbol, horizon_days=horizon)
        if pred is None:
            raise HTTPException(404, f"無法取得 {symbol} 的預測數據（可能數據不足）")

        # 取準確率統計（背景查詢，不阻塞回應）
        accuracy_stats = await prediction_recorder.get_accuracy_stats(symbol, horizon)

        # 儲存到 DB
        if save:
            stock_name = STOCK_NAMES.get(symbol, symbol)
            saved = await prediction_recorder.save_prediction(symbol, stock_name, pred)
            pred["saved_to_db"] = saved

        # 組合回應
        direction_emoji = {"up": "📈", "down": "📉", "neutral": "➡️"}.get(pred["predicted_direction"], "")
        direction_text = {"up": "上漲", "down": "下跌", "neutral": "盤整"}.get(pred["predicted_direction"], "")

        return {
            "success": True,
            "symbol": symbol,
            "stock_name": STOCK_NAMES.get(symbol, ""),
            "prediction": {
                "horizon_days": pred["horizon_days"],
                "prediction_date": pred["prediction_date"],
                "target_date": pred["target_date"],
                "current_price": pred["current_price"],
                "predicted_price": pred["predicted_price"],
                "predicted_change_pct": pred["predicted_change_pct"],
                "predicted_direction": pred["predicted_direction"],
                "direction_label": f"{direction_emoji} {direction_text}",
                "predicted_high": pred["predicted_high"],
                "predicted_low": pred["predicted_low"],
                "confidence": pred["confidence"],
            },
            "model": {
                "source": pred["model_source"],
                "historical_accuracy": accuracy_stats.get("direction_accuracy_pct", 0),
                "total_verified_predictions": accuracy_stats.get("total", 0),
                "status": "lstm_v2" if pred["model_source"] == "lstm_v2" else "technical_fallback",
            },
            "key_indicators": pred.get("snapshot", {}),
            "accuracy_stats": accuracy_stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"預測API失敗 {symbol}: {e}", exc_info=True)
        raise HTTPException(500, f"預測失敗: {str(e)}")


@router.post("/train/{symbol}")
async def trigger_training(symbol: str, horizon: int = Query(default=2)):
    """
    觸發 LSTM 模型訓練（背景執行，約需 30-120 秒）
    - 使用 2 年歷史數據
    - Early Stopping 防止過擬合
    """
    import asyncio

    async def _train_task():
        result = await prediction_engine.train(symbol, horizon_days=horizon)
        logger.info(f"訓練結果 {symbol}: {result}")

    asyncio.create_task(_train_task())

    return {
        "success": True,
        "message": f"已開始訓練 {symbol} LSTM 模型（horizon={horizon}天），訓練中請稍候...",
        "check_accuracy_url": f"/api/prediction/accuracy/{symbol}",
    }


@router.post("/train-batch")
async def trigger_batch_training(
    symbols: list = None,
    horizon: int = Query(default=2),
):
    """批量訓練多支股票 LSTM 模型"""
    import asyncio

    if symbols is None:
        # 預設訓練持倉股 + 主要股票
        symbols = list(STOCK_NAMES.keys())[:10]

    async def _batch_train():
        for sym in symbols:
            try:
                logger.info(f"🤖 開始訓練 {sym}...")
                result = await prediction_engine.train(sym, horizon_days=horizon)
                logger.info(f"{'✅' if result.get('success') else '❌'} {sym}: {result}")
                await asyncio.sleep(2)  # 避免過熱
            except Exception as e:
                logger.error(f"訓練 {sym} 失敗: {e}")

    asyncio.create_task(_batch_train())
    return {"success": True, "message": f"已開始批量訓練 {len(symbols)} 支股票", "symbols": symbols}


@router.get("/accuracy/{symbol}")
async def get_accuracy(
    symbol: str,
    horizon: Optional[int] = Query(default=None),
    window_days: int = Query(default=14),
):
    """查詢個股預測準確率"""
    stats = await prediction_recorder.get_accuracy_stats(symbol, horizon, window_days)
    return {"success": True, "symbol": symbol, **stats}


@router.get("/accuracy-all/summary")
async def get_all_accuracy(window_days: int = Query(default=14)):
    """查詢所有股票的整體預測準確率"""
    from app.database.connection import get_async_session
    from app.models.price_prediction import PricePredictionRecord
    from sqlalchemy import select, func, and_
    from sqlalchemy import Integer as SAInteger

    cutoff = date.today() - timedelta(days=window_days)

    try:
        async with get_async_session() as session:
            stmt = select(
                PricePredictionRecord.symbol,
                func.count().label('total'),
                func.sum(
                    PricePredictionRecord.direction_correct.cast(SAInteger)
                ).label('correct'),
                func.avg(PricePredictionRecord.score).label('avg_score'),
            ).where(
                and_(
                    PricePredictionRecord.is_verified == True,
                    PricePredictionRecord.prediction_date >= cutoff,
                )
            ).group_by(PricePredictionRecord.symbol).order_by(
                func.avg(PricePredictionRecord.score).desc()
            )

            result = await session.execute(stmt)
            rows = result.all()

        leaderboard = []
        for row in rows:
            total = row.total or 0
            correct = int(row.correct or 0)
            acc = correct / total * 100 if total > 0 else 0
            leaderboard.append({
                "symbol": row.symbol,
                "name": STOCK_NAMES.get(row.symbol, ""),
                "total": total,
                "correct": correct,
                "accuracy_pct": round(acc, 1),
                "avg_score": round(float(row.avg_score or 0), 1),
                "hit_target": acc >= 80,
            })

        overall_total = sum(r["total"] for r in leaderboard)
        overall_correct = sum(r["correct"] for r in leaderboard)
        overall_acc = overall_correct / overall_total * 100 if overall_total > 0 else 0

        return {
            "success": True,
            "window_days": window_days,
            "overall_accuracy_pct": round(overall_acc, 1),
            "target": 80.0,
            "total_predictions": overall_total,
            "leaderboard": leaderboard,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/verify-now")
async def manual_verify():
    """手動觸發驗證（測試用）"""
    result = await prediction_recorder.verify_past_predictions()
    return {"success": True, **result}


@router.get("/history/{symbol}")
async def get_prediction_history(
    symbol: str,
    limit: int = Query(default=20, le=100),
):
    """查詢個股預測歷史（包含是否正確）"""
    from app.database.connection import get_async_session
    from app.models.price_prediction import PricePredictionRecord
    from sqlalchemy import select, desc

    try:
        async with get_async_session() as session:
            stmt = (
                select(PricePredictionRecord)
                .where(PricePredictionRecord.symbol == symbol)
                .order_by(desc(PricePredictionRecord.prediction_date))
                .limit(limit)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

        history = []
        for r in records:
            history.append({
                "prediction_date": r.prediction_date.isoformat(),
                "target_date": r.target_date.isoformat(),
                "horizon_days": r.horizon_days,
                "price_at_prediction": float(r.price_at_prediction),
                "predicted_price": float(r.predicted_price),
                "predicted_direction": r.predicted_direction,
                "predicted_change_pct": float(r.predicted_change_pct),
                "confidence": float(r.confidence),
                "is_verified": r.is_verified,
                "actual_price": float(r.actual_price) if r.actual_price else None,
                "actual_direction": r.actual_direction,
                "direction_correct": r.direction_correct,
                "price_error_pct": float(r.price_error_pct) if r.price_error_pct else None,
                "score": float(r.score) if r.score else None,
                "failure_reason": r.failure_reason,
                "success_pattern": r.success_pattern,
                "model_version": r.model_version,
            })

        return {"success": True, "symbol": symbol, "history": history}

    except Exception as e:
        raise HTTPException(500, str(e))
