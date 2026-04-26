"""
訊號追蹤資料庫管理器
用於持久化追蹤數據到 PostgreSQL
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os

from app.services.rejected_signal import RejectedSignal, TrackingSnapshot

logger = logging.getLogger(__name__)


class SignalTrackingDB:
    """訊號追蹤資料庫管理器"""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'ai_stock_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
    
    def get_connection(self):
        """獲取資料庫連接"""
        return psycopg2.connect(**self.connection_params, cursor_factory=RealDictCursor)
    
    def init_tables(self):
        """初始化資料表（如果不存在）"""
        schema_file = os.path.join(
            os.path.dirname(__file__),
            '../database/signal_tracking_schema.sql'
        )
        
        try:
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
            conn.commit()
            conn.close()
            logger.info("✅ 訊號追蹤資料表已初始化")
        except Exception as e:
            logger.error(f"初始化資料表失敗: {e}")
    
    def save_rejected_signal(self, signal: RejectedSignal):
        """保存被拒絕的訊號"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 插入主記錄
                sql = """
                INSERT INTO rejected_signals (
                    signal_id, stock_code, stock_name, reject_time,
                    price_at_reject, vwap, vwap_deviation, 
                    kd_k, kd_d, ofi, volume_trend, price_trend,
                    risk_score, virtual_entry_price, virtual_stop_loss, 
                    virtual_take_profit
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (signal_id) DO NOTHING
                """
                cursor.execute(sql, (
                    signal.signal_id, signal.stock_code, signal.stock_name,
                    signal.reject_time, signal.price_at_reject, signal.vwap,
                    signal.vwap_deviation, signal.kd_k, signal.kd_d,
                    signal.ofi, signal.volume_trend, signal.price_trend,
                    signal.risk_score, signal.virtual_entry_price,
                    signal.virtual_stop_loss, signal.virtual_take_profit
                ))
                
                # 插入拒絕原因
                for reason in signal.rejection_reasons:
                    severity = self._calculate_severity(reason)
                    sql_reason = """
                    INSERT INTO rejection_reasons (signal_id, reason, severity)
                    VALUES (%s, %s, %s)
                    """
                    cursor.execute(sql_reason, (signal.signal_id, reason, severity))
                
            conn.commit()
            logger.info(f"已保存拒絕訊號：{signal.signal_id}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存拒絕訊號失敗：{e}")
        finally:
            conn.close()
    
    def update_tracking_result(self, signal: RejectedSignal):
        """更新追蹤結果"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                UPDATE rejected_signals SET
                    price_after_30min = %s,
                    price_after_1hour = %s,
                    price_after_2hour = %s,
                    highest_price = %s,
                    lowest_price = %s,
                    would_profit = %s,
                    would_hit_stop_loss = %s,
                    would_hit_take_profit = %s,
                    virtual_pnl_percent = %s,
                    decision_quality = %s,
                    tracking_completed = TRUE
                WHERE signal_id = %s
                """
                cursor.execute(sql, (
                    signal.price_after_30min, signal.price_after_1hour,
                    signal.price_after_2hour, signal.highest_price,
                    signal.lowest_price, signal.would_profit,
                    signal.would_hit_stop_loss, signal.would_hit_take_profit,
                    signal.virtual_pnl_percent, signal.decision_quality,
                    signal.signal_id
                ))
            
            conn.commit()
            logger.info(f"已更新追蹤結果：{signal.signal_id}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"更新追蹤結果失敗：{e}")
        finally:
            conn.close()
    
    def save_tracking_snapshot(self, signal_id: str, snapshot: TrackingSnapshot):
        """保存追蹤快照"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO tracking_snapshots (
                    signal_id, snapshot_time, price, volume, ofi
                ) VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    signal_id, snapshot.timestamp, snapshot.price,
                    snapshot.volume, snapshot.ofi
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"保存快照失敗：{e}")
        finally:
            conn.close()
    
    def get_signals_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict]:
        """獲取指定期間的訊號"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT * FROM rejected_signals
                WHERE reject_time BETWEEN %s AND %s
                AND tracking_completed = TRUE
                ORDER BY reject_time
                """
                cursor.execute(sql, (start_date, end_date))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    # 獲取拒絕原因
                    cursor.execute(
                        "SELECT reason FROM rejection_reasons WHERE signal_id = %s",
                        (row['signal_id'],)
                    )
                    reasons = [r['reason'] for r in cursor.fetchall()]
                    
                    result = dict(row)
                    result['rejection_reasons'] = reasons
                    results.append(result)
                
                return results
        finally:
            conn.close()
    
    def get_statistics(self, days: int = 7) -> Dict:
        """獲取統計數據"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # 總數
                cursor.execute("""
                    SELECT COUNT(*) as total FROM rejected_signals
                    WHERE reject_time BETWEEN %s AND %s
                    AND tracking_completed = TRUE
                """, (start_date, end_date))
                total = cursor.fetchone()['total']
                
                if total == 0:
                    return {'total': 0, 'message': '沒有追蹤數據'}
                
                # 決策品質統計
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN decision_quality LIKE '%%正確%%' THEN 1 ELSE 0 END) as correct,
                        SUM(CASE WHEN decision_quality LIKE '%%錯誤%%' THEN 1 ELSE 0 END) as incorrect,
                        AVG(virtual_pnl_percent) as avg_pnl
                    FROM rejected_signals
                    WHERE reject_time BETWEEN %s AND %s
                    AND tracking_completed = TRUE
                """, (start_date, end_date))
                stats = cursor.fetchone()
                
                # 分原因統計
                cursor.execute("""
                    SELECT 
                        rr.reason,
                        COUNT(*) as count,
                        AVG(rs.virtual_pnl_percent) as avg_pnl,
                        SUM(CASE WHEN rs.decision_quality LIKE '%%正確%%' THEN 1 ELSE 0 END) as correct
                    FROM rejection_reasons rr
                    JOIN rejected_signals rs ON rr.signal_id = rs.signal_id
                    WHERE rs.reject_time BETWEEN %s AND %s
                    AND rs.tracking_completed = TRUE
                    GROUP BY rr.reason
                """, (start_date, end_date))
                reason_stats = {}
                for row in cursor.fetchall():
                    reason_stats[row['reason']] = {
                        'count': row['count'],
                        'avg_pnl': float(row['avg_pnl']) if row['avg_pnl'] else 0,
                        'accuracy': row['correct'] / row['count'] if row['count'] > 0 else 0
                    }
                
                correct = stats['correct'] or 0
                incorrect = stats['incorrect'] or 0
                
                return {
                    'total': total,
                    'correct_rejections': correct,
                    'incorrect_rejections': incorrect,
                    'ambiguous': total - correct - incorrect,
                    'accuracy': correct / (correct + incorrect) if (correct + incorrect) > 0 else 0,
                    'avg_pnl_if_entered': float(stats['avg_pnl']) if stats['avg_pnl'] else 0,
                    'reason_stats': reason_stats,
                    'period_days': days
                }
        except Exception as e:
            logger.error(f"獲取統計失敗: {e}")
            return {'error': str(e)}
        finally:
            conn.close()
    
    def save_weekly_report(self, report_data: Dict) -> str:
        """保存週報"""
        report_id = f"WR_{report_data['start_date'].replace('-', '')}_{report_data['end_date'].replace('-', '')}"
        
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO weekly_reports (
                    report_id, start_date, end_date, total_signals, total_rejected,
                    rejection_rate, correct_rejections, incorrect_rejections,
                    ambiguous_decisions, decision_accuracy, avg_missed_profit,
                    avg_avoided_loss, expected_value_if_entered, net_benefit
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (report_id) DO UPDATE SET
                    correct_rejections = EXCLUDED.correct_rejections,
                    incorrect_rejections = EXCLUDED.incorrect_rejections,
                    decision_accuracy = EXCLUDED.decision_accuracy
                """
                cursor.execute(sql, (
                    report_id, 
                    report_data['start_date'], 
                    report_data['end_date'],
                    report_data.get('total_signals', 0),
                    report_data.get('total_rejected', 0),
                    report_data.get('rejection_rate', 1.0),
                    report_data.get('correct_rejections', 0),
                    report_data.get('incorrect_rejections', 0),
                    report_data.get('ambiguous_decisions', 0),
                    report_data.get('decision_accuracy', 0),
                    report_data.get('avg_missed_profit', 0),
                    report_data.get('avg_avoided_loss', 0),
                    report_data.get('expected_value_if_entered', 0),
                    report_data.get('net_benefit', 0)
                ))
            
            conn.commit()
            logger.info(f"已保存週報：{report_id}")
            return report_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存週報失敗：{e}")
            raise
        finally:
            conn.close()
    
    def _calculate_severity(self, reason: str) -> int:
        """計算原因嚴重程度"""
        if '乖離極大' in reason or '極度' in reason or '大量拋售' in reason:
            return 3
        elif '過高' in reason or '超買' in reason:
            return 2
        else:
            return 1


# 全局實例
signal_tracking_db = SignalTrackingDB()
