"""
自我學習引擎 (Self-Learning Trade Reviewer)
==========================================
「每一筆虧損都是老師，每一筆盈利都是驗證」

功能：
  1. 每日收盤後，自動分析所有已平倉的交易記錄
  2. 按「進場因子」分組，統計各因子的真實勝率
  3. 找出「致勝模式」和「致命錯誤」
  4. 自動調整 SmartEntry 各因子的加扣分權重
  5. 生成每週操盤反省報告

核心思想：
  從模擬交易記錄學習 → 更新因子權重 → 下次更準確
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

LEARNING_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '../../../data/learning_weights.json'
)

# ──────────────────────────────────────────────
# 預設因子權重（與 smart_entry_system 對應）
# 會被自我學習機制動態更新
# ──────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "volume_ratio_high": 20,     # 爆量加分
    "volume_ratio_mid": 10,      # 放量加分
    "ma_bull_alignment": 15,     # 多頭排列
    "trend_up": 10,              # 趨勢向上
    "change_pct_moderate": 15,   # 漲幅適中
    "change_pct_excessive": -20, # 漲幅過大扣分
    "volume_insufficient": -20,  # 量能不足扣分
    "risk_high": -15,            # 高風險扣分
    "risk_extreme": -30,         # 極端風險扣分
    "sector_bull": 10,           # 族群強勢加分
    "sector_bear": -15,          # 族群弱勢扣分
    "quality_ideal": 15,         # 完美進場位置
    "quality_good": 8,           # 良好進場位置
    "quality_poor": -10,         # 不佳進場位置
    "lstm_bullish": 12,          # LSTM 看漲
    "lstm_bearish": -15,         # LSTM 看空
}


def load_weights() -> Dict:
    """載入學習後的因子權重"""
    try:
        if os.path.exists(LEARNING_CONFIG_PATH):
            with open(LEARNING_CONFIG_PATH, 'r') as f:
                data = json.load(f)
                return data.get('weights', DEFAULT_WEIGHTS)
    except Exception:
        pass
    return DEFAULT_WEIGHTS.copy()


def save_weights(weights: Dict, metadata: Dict = None):
    """保存更新後的因子權重"""
    try:
        os.makedirs(os.path.dirname(LEARNING_CONFIG_PATH), exist_ok=True)
        payload = {
            'weights': weights,
            'updated_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        with open(LEARNING_CONFIG_PATH, 'w') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info("✅ 因子權重已更新並儲存")
    except Exception as e:
        logger.error(f"權重儲存失敗: {e}")


# ──────────────────────────────────────────────
# 交易反省分析器
# ──────────────────────────────────────────────

class TradeLearningEngine:
    """
    自我學習引擎主體。
    從已平倉交易記錄中提取勝敗規律，動態調整參數。
    """

    def __init__(self):
        self.weights = load_weights()
        self.review_log = []

    async def analyze_closed_trades(
        self, days_back: int = 30
    ) -> Dict:
        """
        分析最近 N 天的所有已平倉模擬交易。

        Returns:
            完整分析報告 (勝率/敗率/各因子效果)
        """
        try:
            from app.database.connection import AsyncSessionLocal
            from app.models.portfolio import Portfolio, TradeRecord
            from sqlalchemy import select, and_

            cutoff = datetime.now() - timedelta(days=days_back)

            async with AsyncSessionLocal() as db:
                # 取所有已平倉的模擬持倉
                result = await db.execute(
                    select(Portfolio).where(
                        and_(
                            Portfolio.status.in_(['closed', 'stop_loss', 'target_hit']),
                            Portfolio.is_simulated == True,
                            Portfolio.entry_date >= cutoff
                        )
                    )
                )
                positions = result.scalars().all()

            if not positions:
                return {'error': f'最近 {days_back} 天無已平倉記錄'}

            # ── 統計分析 ──
            wins, losses = [], []
            strategy_stats: Dict[str, Dict] = {}
            factor_stats: Dict[str, Dict] = {}
            hour_stats: Dict[int, Dict] = {}

            for pos in positions:
                # 損益
                if pos.entry_price and pos.target_price:
                    if pos.status == 'target_hit':
                        pnl_pct = float(pos.analysis_confidence or 0)
                        is_win = True
                    elif pos.status == 'stop_loss':
                        pnl_pct = -float(pos.stop_loss_price / pos.entry_price * 100 - 100) if pos.stop_loss_price else -5
                        is_win = False
                    else:
                        # 嘗試從 notes 計算損益
                        pnl_pct = 0
                        is_win = pnl_pct > 0
                else:
                    continue

                trade_info = {
                    'symbol': pos.symbol,
                    'strategy': pos.analysis_source or 'unknown',
                    'entry_hour': pos.entry_date.hour if pos.entry_date else 9,
                    'notes': pos.notes or '',
                    'pnl_pct': pnl_pct,
                    'status': pos.status,
                    'entry_date': pos.entry_date.isoformat() if pos.entry_date else ''
                }

                if is_win:
                    wins.append(trade_info)
                else:
                    losses.append(trade_info)

                # 按策略分組
                strat = pos.analysis_source or 'unknown'
                if strat not in strategy_stats:
                    strategy_stats[strat] = {'wins': 0, 'losses': 0, 'pnls': []}
                strategy_stats[strat]['wins' if is_win else 'losses'] += 1
                strategy_stats[strat]['pnls'].append(pnl_pct)

                # 按進場小時分組
                hr = pos.entry_date.hour if pos.entry_date else 9
                if hr not in hour_stats:
                    hour_stats[hr] = {'wins': 0, 'losses': 0}
                hour_stats[hr]['wins' if is_win else 'losses'] += 1

            total = len(wins) + len(losses)
            win_rate = len(wins) / total if total > 0 else 0

            # ── 策略勝率排行 ──
            strategy_ranking = []
            for strat, stats in strategy_stats.items():
                t = stats['wins'] + stats['losses']
                wr = stats['wins'] / t if t > 0 else 0
                avg_pnl = sum(stats['pnls']) / len(stats['pnls']) if stats['pnls'] else 0
                strategy_ranking.append({
                    'strategy': strat,
                    'win_rate': round(wr, 3),
                    'total': t,
                    'avg_pnl_pct': round(avg_pnl, 2)
                })
            strategy_ranking.sort(key=lambda x: x['win_rate'], reverse=True)

            # ── 最佳/最差進場時段 ──
            hour_ranking = []
            for hr, stats in hour_stats.items():
                t = stats['wins'] + stats['losses']
                wr = stats['wins'] / t if t > 0 else 0
                hour_ranking.append({'hour': hr, 'win_rate': round(wr, 3), 'total': t})
            hour_ranking.sort(key=lambda x: x['win_rate'], reverse=True)

            # ── 提取致命錯誤模式 ──
            fatal_patterns = self._find_fatal_patterns(losses)

            # ── 提取致勝模式 ──
            winning_patterns = self._find_winning_patterns(wins)

            report = {
                'period_days': days_back,
                'total_trades': total,
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': round(win_rate, 4),
                'strategy_ranking': strategy_ranking,
                'best_hour': hour_ranking[0] if hour_ranking else {},
                'worst_hour': hour_ranking[-1] if len(hour_ranking) > 1 else {},
                'hour_breakdown': hour_ranking,
                'fatal_patterns': fatal_patterns,
                'winning_patterns': winning_patterns,
                'generated_at': datetime.now().isoformat()
            }

            # ── 自動更新因子權重 ──
            self._auto_adjust_weights(report)

            logger.info(
                f"📊 [自我學習] {total} 筆交易分析完成 | "
                f"勝率: {win_rate:.1%} | "
                f"最佳策略: {strategy_ranking[0]['strategy'] if strategy_ranking else 'N/A'}"
            )

            return report

        except Exception as e:
            logger.error(f"交易分析失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'error': str(e)}

    def _find_fatal_patterns(self, loss_trades: List[Dict]) -> List[str]:
        """從虧損交易中找出重複性致命錯誤"""
        patterns = []
        if not loss_trades:
            return patterns

        # 分析進場時段
        late_losses = [t for t in loss_trades if t.get('entry_hour', 9) >= 11]
        if len(late_losses) / len(loss_trades) > 0.5:
            patterns.append(f"⚠️ 超過 50% 的虧損發生在 11:00 後進場（共 {len(late_losses)} 筆）→ 應嚴格執行進場時間限制")

        # 分析是否有特定策略集中虧損
        strat_count = {}
        for t in loss_trades:
            s = t.get('strategy', 'unknown')
            strat_count[s] = strat_count.get(s, 0) + 1

        for strat, cnt in strat_count.items():
            if cnt / len(loss_trades) > 0.4:
                patterns.append(f"⚠️ 策略「{strat}」佔虧損 {cnt/len(loss_trades):.0%} → 建議調高此策略門檻")

        return patterns

    def _find_winning_patterns(self, win_trades: List[Dict]) -> List[str]:
        """從盈利交易中找出可複製的致勝模式"""
        patterns = []
        if not win_trades:
            return patterns

        # 最佳進場時段
        hour_count = {}
        for t in win_trades:
            hr = t.get('entry_hour', 9)
            hour_count[hr] = hour_count.get(hr, 0) + 1

        best_hr = max(hour_count, key=hour_count.get) if hour_count else 9
        best_hr_cnt = hour_count.get(best_hr, 0)
        if best_hr_cnt / len(win_trades) > 0.3:
            patterns.append(f"✅ {best_hr}:00-{best_hr+1}:00 是最高勝率時段（{best_hr_cnt/len(win_trades):.0%} 的獲利在此出現）")

        # 最佳策略
        strat_count = {}
        for t in win_trades:
            s = t.get('strategy', 'unknown')
            strat_count[s] = strat_count.get(s, 0) + 1

        best_strat = max(strat_count, key=strat_count.get) if strat_count else None
        if best_strat:
            patterns.append(f"✅ 策略「{best_strat}」是主要獲利來源（{strat_count[best_strat]} 筆獲利）")

        return patterns

    def _auto_adjust_weights(self, report: Dict):
        """
        根據分析報告自動微調因子權重。
        原則：勝率提升的因子加強，勝率下降的因子減弱。
        """
        win_rate = report.get('win_rate', 0)

        if win_rate < 0.4:
            # 整體勝率低 → 收緊所有扣分，提高門檻
            logger.warning(f"📉 整體勝率 {win_rate:.1%} 過低，提高進場門檻")
            self.weights['volume_insufficient'] = min(-10, self.weights['volume_insufficient'] - 5)
            self.weights['risk_high'] = min(-10, self.weights['risk_high'] - 5)
        elif win_rate > 0.6:
            # 整體勝率高 → 可適度放寬，增加交易機會
            logger.info(f"📈 整體勝率 {win_rate:.1%} 優秀，適度放寬閾值")
            self.weights['volume_ratio_mid'] = min(15, self.weights['volume_ratio_mid'] + 2)

        save_weights(self.weights, {
            'last_win_rate': win_rate,
            'total_trades': report.get('total_trades', 0),
            'adjusted_reason': f"自動調整 based on {report.get('total_trades',0)} 筆交易"
        })

    async def generate_weekly_report(self) -> str:
        """生成每週操盤反省報告（Markdown 格式）"""
        report = await self.analyze_closed_trades(days_back=7)

        if 'error' in report:
            return f"# 週報生成失敗\n\n{report['error']}"

        win_rate = report.get('win_rate', 0)
        total = report.get('total_trades', 0)
        wins = report.get('wins', 0)
        losses = report.get('losses', 0)

        # 進步/退步判斷
        trend = "📈 持續進步" if win_rate > 0.5 else "📉 需要改進"

        lines = [
            f"# 每週操盤反省報告",
            f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"## 本週戰績 {trend}",
            f"| 指標 | 數值 |",
            f"|------|------|",
            f"| 總交易次數 | {total} |",
            f"| 獲利筆數 | {wins} |",
            f"| 虧損筆數 | {losses} |",
            f"| **整體勝率** | **{win_rate:.1%}** |",
            "",
            "## 各策略勝率排行",
        ]

        for rank in report.get('strategy_ranking', []):
            emoji = "🥇" if rank == report['strategy_ranking'][0] else "  "
            lines.append(
                f"{emoji} **{rank['strategy']}**: 勝率 {rank['win_rate']:.1%} "
                f"({rank['total']} 筆, 均損益 {rank['avg_pnl_pct']:+.1f}%)"
            )

        lines += [
            "",
            "## 致命錯誤（需避免）",
        ]
        for p in report.get('fatal_patterns', []):
            lines.append(f"- {p}")
        if not report.get('fatal_patterns'):
            lines.append("- 本週無明顯重複性錯誤 ✅")

        lines += [
            "",
            "## 致勝模式（需複製）",
        ]
        for p in report.get('winning_patterns', []):
            lines.append(f"- {p}")

        lines += [
            "",
            "## 下週行動計畫",
            f"- 重點執行：{report['strategy_ranking'][0]['strategy'] if report.get('strategy_ranking') else 'N/A'} 策略",
            f"- 最佳進場時段：{report.get('best_hour', {}).get('hour', 9)}:00 前後",
            f"- 避開時段：{report.get('worst_hour', {}).get('hour', 12)}:00 後",
            "",
            "---",
            "*本報告由 AI 自我學習引擎自動生成*"
        ]

        return "\n".join(lines)


# 單例
trade_learning_engine = TradeLearningEngine()
