"""
ML 訊號追蹤服務
Signal Tracking Service for Machine Learning

功能：
1. 記錄每個訊號的完整特徵
2. 自動追蹤後續價格 (5分鐘/30分鐘/收盤)
3. 計算成功/失敗標籤
4. 提供 ML 訓練數據
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

logger = logging.getLogger(__name__)


class MLSignalTracker:
    """ML 訊號追蹤器"""
    
    def __init__(self):
        self.pending_checks: Dict[str, Dict] = {}  # signal_id -> check info
        self.is_running = False
        logger.info("📊 ML 訊號追蹤器已初始化")
    
    async def start(self):
        """啟動追蹤任務"""
        if self.is_running:
            return
        
        self.is_running = True
        asyncio.create_task(self._tracking_loop())
        logger.info("🚀 ML 訊號追蹤器已啟動")
    
    async def stop(self):
        """停止追蹤"""
        self.is_running = False
        logger.info("🛑 ML 訊號追蹤器已停止")
    
    async def record_signal(
        self,
        stock_code: str,
        stock_name: str,
        signal_type: str,
        entry_price: float,
        features: Dict[str, Any],
        signal_source: str = "day_trading",
        stop_loss: float = None,
        take_profit: float = None,
        confidence: float = 0
    ) -> str:
        """
        記錄一個新訊號
        
        Returns:
            signal_id: 唯一訊號 ID
        """
        try:
            from app.database.connection import get_async_session
            from app.models.ml_signal import TradingSignal
            
            signal_id = f"SIG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_{uuid.uuid4().hex[:6]}"
            now = datetime.now()
            
            signal = TradingSignal(
                signal_id=signal_id,
                timestamp=now,
                stock_code=stock_code,
                stock_name=stock_name,
                signal_type=signal_type,
                signal_source=signal_source,
                entry_price=entry_price,
                
                # VWAP
                vwap=features.get('vwap'),
                vwap_deviation=features.get('vwap_deviation'),
                
                # 資金流
                ofi=features.get('ofi'),
                foreign_net=features.get('foreign_net'),
                trust_net=features.get('trust_net'),
                
                # 價格位置
                support_level=features.get('support'),
                resistance_level=features.get('resistance'),
                distance_to_support=self._calc_distance(entry_price, features.get('support')),
                distance_to_resistance=self._calc_distance(entry_price, features.get('resistance')),
                
                # 量價
                volume_price_signal=features.get('volume_price_signal'),
                volume_ratio=features.get('volume_ratio'),
                
                # 技術指標
                rsi=features.get('rsi'),
                macd_signal=features.get('macd_signal'),
                
                # 時間
                hour_of_day=now.hour,
                minute_of_hour=now.minute,
                day_of_week=now.weekday(),
                market_phase=features.get('market_phase'),
                
                # 停損停利
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence_score=confidence,
                
                # 額外特徵
                extra_features=features.get('extra_features')
            )
            
            async with get_async_session() as session:
                session.add(signal)
                await session.commit()
            
            # 加入追蹤佇列
            self.pending_checks[signal_id] = {
                'stock_code': stock_code,
                'entry_price': entry_price,
                'entry_time': now,
                'signal_type': signal_type,
                'check_5min': now + timedelta(minutes=5),
                'check_30min': now + timedelta(minutes=30),
                'check_close': self._get_close_time(now)
            }
            
            logger.info(f"📝 已記錄訊號: {signal_id} | {stock_code} {signal_type} @ {entry_price}")
            return signal_id
            
        except Exception as e:
            logger.error(f"❌ 記錄訊號失敗: {e}")
            return None
    
    def _calc_distance(self, price: float, level: float) -> Optional[float]:
        """計算價格與支撐/壓力的距離百分比"""
        if not price or not level or level == 0:
            return None
        return round((price - level) / level * 100, 2)
    
    def _get_close_time(self, dt: datetime) -> datetime:
        """取得收盤時間 (13:30)"""
        return dt.replace(hour=13, minute=30, second=0, microsecond=0)
    
    async def _tracking_loop(self):
        """追蹤循環 - 檢查待追蹤的訊號"""
        while self.is_running:
            try:
                now = datetime.now()
                to_remove = []
                
                for signal_id, check_info in self.pending_checks.items():
                    # 檢查 5 分鐘
                    if not check_info.get('checked_5min') and now >= check_info['check_5min']:
                        await self._check_and_update(signal_id, check_info, '5min')
                        check_info['checked_5min'] = True
                    
                    # 檢查 30 分鐘
                    if not check_info.get('checked_30min') and now >= check_info['check_30min']:
                        await self._check_and_update(signal_id, check_info, '30min')
                        check_info['checked_30min'] = True
                    
                    # 檢查收盤
                    if not check_info.get('checked_close') and now >= check_info['check_close']:
                        await self._check_and_update(signal_id, check_info, 'close')
                        check_info['checked_close'] = True
                        to_remove.append(signal_id)  # 完成追蹤
                
                # 移除已完成的
                for signal_id in to_remove:
                    del self.pending_checks[signal_id]
                    logger.info(f"✅ 訊號追蹤完成: {signal_id}")
                
                await asyncio.sleep(30)  # 每 30 秒檢查一次
                
            except Exception as e:
                logger.error(f"追蹤循環錯誤: {e}")
                await asyncio.sleep(10)
    
    async def _check_and_update(self, signal_id: str, check_info: Dict, check_type: str):
        """檢查並更新訊號結果"""
        try:
            stock_code = check_info['stock_code']
            entry_price = check_info['entry_price']
            signal_type = check_info['signal_type']
            
            # 取得當前價格
            from app.services.fubon_service import get_realtime_quote
            quote = await get_realtime_quote(stock_code)
            
            if not quote or quote.get('price', 0) <= 0:
                return
            
            current_price = quote['price']
            return_pct = round((current_price - entry_price) / entry_price * 100, 2)
            
            # 判斷是否成功 (做多: 上漲=成功, 做空: 下跌=成功)
            is_long = 'LONG' in signal_type.upper() or signal_type == 'ENTRY_LONG'
            is_success = (return_pct > 0) if is_long else (return_pct < 0)
            
            # 更新資料庫
            from app.database.connection import get_async_session
            from app.models.ml_signal import TradingSignal
            
            async with get_async_session() as session:
                result = await session.execute(
                    select(TradingSignal).where(TradingSignal.signal_id == signal_id)
                )
                signal = result.scalar_one_or_none()
                
                if signal:
                    if check_type == '5min':
                        signal.price_5min = current_price
                        signal.return_5min = return_pct
                        signal.checked_5min = True
                        signal.is_success_5min = is_success
                    elif check_type == '30min':
                        signal.price_30min = current_price
                        signal.return_30min = return_pct
                        signal.checked_30min = True
                        signal.is_success_30min = is_success
                    elif check_type == 'close':
                        signal.price_close = current_price
                        signal.return_close = return_pct
                        signal.checked_close = True
                        signal.is_success_close = is_success
                        signal.final_return = return_pct
                    
                    signal.updated_at = datetime.now()
                    await session.commit()
                    
                    logger.info(f"📈 {signal_id} {check_type}: {return_pct:+.2f}% ({'✓' if is_success else '✗'})")
            
        except Exception as e:
            logger.error(f"更新訊號結果失敗 {signal_id}: {e}")
    
    async def get_training_data(self, min_samples: int = 100) -> Optional[Dict]:
        """
        取得 ML 訓練數據
        
        Returns:
            {
                'features': [[...], [...], ...],  # 特徵矩陣
                'labels': [0, 1, 1, 0, ...],      # 標籤
                'sample_count': 150,
                'ready_for_training': True
            }
        """
        try:
            from app.database.connection import get_async_session
            from app.models.ml_signal import TradingSignal
            
            async with get_async_session() as session:
                result = await session.execute(
                    select(TradingSignal).where(
                        and_(
                            TradingSignal.checked_30min == True,
                            TradingSignal.is_success_30min.isnot(None)
                        )
                    )
                )
                signals = result.scalars().all()
                
                if len(signals) < min_samples:
                    return {
                        'ready_for_training': False,
                        'sample_count': len(signals),
                        'required': min_samples,
                        'message': f'需要累積 {min_samples - len(signals)} 筆訊號'
                    }
                
                features = []
                labels = []
                
                for sig in signals:
                    feat = sig.to_ml_features()
                    features.append(list(feat.values()))
                    labels.append(1 if sig.is_success_30min else 0)
                
                return {
                    'ready_for_training': True,
                    'sample_count': len(signals),
                    'feature_names': list(signals[0].to_ml_features().keys()),
                    'features': features,
                    'labels': labels
                }
                
        except Exception as e:
            logger.error(f"取得訓練數據失敗: {e}")
            return None
    
    async def get_accuracy_stats(self, days: int = 30) -> Dict:
        """取得準確度統計"""
        try:
            from app.database.connection import get_async_session
            from app.models.ml_signal import TradingSignal
            
            cutoff = datetime.now() - timedelta(days=days)
            
            async with get_async_session() as session:
                # 總數
                total_result = await session.execute(
                    select(func.count(TradingSignal.id)).where(
                        TradingSignal.timestamp >= cutoff
                    )
                )
                total = total_result.scalar()
                
                # 5 分鐘成功數
                success_5min_result = await session.execute(
                    select(func.count(TradingSignal.id)).where(
                        and_(
                            TradingSignal.timestamp >= cutoff,
                            TradingSignal.is_success_5min == True
                        )
                    )
                )
                success_5min = success_5min_result.scalar()
                
                # 30 分鐘成功數
                success_30min_result = await session.execute(
                    select(func.count(TradingSignal.id)).where(
                        and_(
                            TradingSignal.timestamp >= cutoff,
                            TradingSignal.is_success_30min == True
                        )
                    )
                )
                success_30min = success_30min_result.scalar()
                
                return {
                    'period_days': days,
                    'total_signals': total,
                    'accuracy_5min': round(success_5min / total * 100, 1) if total > 0 else 0,
                    'accuracy_30min': round(success_30min / total * 100, 1) if total > 0 else 0,
                    'success_5min': success_5min,
                    'success_30min': success_30min
                }
                
        except Exception as e:
            logger.error(f"取得統計失敗: {e}")
            return {}


# 全域單例
ml_signal_tracker = MLSignalTracker()
