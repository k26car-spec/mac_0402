"""
Alerts API Endpoints
警报相关的 API 端点
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import Alert

router = APIRouter()


@router.get("/", summary="获取警报列表")
async def get_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    symbol: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取警报列表
    
    参数:
    - status: 警报状态（active/acknowledged/resolved）
    - severity: 严重程度（low/medium/high/critical）
    - symbol: 股票代码
    - skip: 跳过数量
    - limit: 返回数量
    """
    query = select(Alert)
    
    # 应用过滤条件
    conditions = []
    if status:
        conditions.append(Alert.status == status)
    if severity:
        conditions.append(Alert.severity == severity)
    if symbol:
        conditions.append(Alert.symbol == symbol)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(desc(Alert.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return {
        "count": len(alerts),
        "alerts": [
            {
                "id": alert.id,
                "symbol": alert.symbol,
                "type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "status": alert.status,
                "triggered_by": alert.triggered_by,
                "is_sent": alert.is_sent,
                "created_at": alert.created_at
            }
            for alert in alerts
        ]
    }


@router.get("/active", summary="获取活跃警报")
async def get_active_alerts(
    db: AsyncSession = Depends(get_db)
):
    """获取所有活跃状态的警报"""
    query = select(Alert).where(
        Alert.status == "active"
    ).order_by(desc(Alert.severity), desc(Alert.created_at))
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    # 按严重程度分组
    grouped = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": []
    }
    
    for alert in alerts:
        severity = alert.severity or "low"
        grouped[severity].append({
            "id": alert.id,
            "symbol": alert.symbol,
            "type": alert.alert_type,
            "title": alert.title,
            "message": alert.message,
            "created_at": alert.created_at
        })
    
    return {
        "total": len(alerts),
        "by_severity": {
            "critical": len(grouped["critical"]),
            "high": len(grouped["high"]),
            "medium": len(grouped["medium"]),
            "low": len(grouped["low"])
        },
        "alerts": grouped
    }


@router.get("/stats", summary="警报统计")
async def get_alert_stats(
    days: int = Query(default=7, le=30),
    db: AsyncSession = Depends(get_db)
):
    """
    获取警报统计信息
    
    参数:
    - days: 统计天数（最多30天）
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # 总数查询
    total_query = select(func.count(Alert.id)).where(
        Alert.created_at >= since
    )
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    # 按状态统计
    status_query = select(
        Alert.status,
        func.count(Alert.id)
    ).where(
        Alert.created_at >= since
    ).group_by(Alert.status)
    
    status_result = await db.execute(status_query)
    status_stats = {row[0]: row[1] for row in status_result}
    
    # 按严重程度统计
    severity_query = select(
        Alert.severity,
        func.count(Alert.id)
    ).where(
        Alert.created_at >= since
    ).group_by(Alert.severity)
    
    severity_result = await db.execute(severity_query)
    severity_stats = {row[0]: row[1] for row in severity_result}
    
    return {
        "period_days": days,
        "total": total,
        "by_status": status_stats,
        "by_severity": severity_stats
    }


@router.patch("/{alert_id}/acknowledge", summary="确认警报")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    确认警报（标记为已读）
    
    参数:
    - alert_id: 警报ID
    """
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="警报不存在")
    
    alert.status = "acknowledged"
    await db.commit()
    
    return {
        "id": alert.id,
        "status": alert.status,
        "message": "警报已确认"
    }


@router.patch("/{alert_id}/resolve", summary="解决警报")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    解决警报（标记为已解决）
    
    参数:
    - alert_id: 警报ID
    """
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="警报不存在")
    
    alert.status = "resolved"
    await db.commit()
    
    return {
        "id": alert.id,
        "status": alert.status,
        "message": "警报已解决"
    }


@router.delete("/{alert_id}", summary="删除警报")
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除警报
    
    参数:
    - alert_id: 警报ID
    """
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="警报不存在")
    
    await db.delete(alert)
    await db.commit()
    
    return {
        "id": alert_id,
        "message": "警报已删除"
    }
