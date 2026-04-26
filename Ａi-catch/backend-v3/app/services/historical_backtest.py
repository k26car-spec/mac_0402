"""
歷史回測引擎 (Historical Backtest Engine)
==========================================
「讓 AI 在幾分鐘內獲得半年的操盤經驗」

工作原理：
  1. 下載目標股票 1~2 年的歷史日 K 線
  2. 模擬在每一天，系統會做出什麼決策（買/不買）
  3. 根據 ATR 動態停損，計算每筆假設交易的結果
  4. 從幾百筆模擬交易中提取勝率/敗率/最佳條件
  5. 自動更新因子權重，讓 SmartEntry 下次更準

支援的評估因子：
  - MA5/MA20/MA60 多空排列
  - 量比（今日 vs 5 日均量）
  - 乖離率
  - 趨勢強度（近 10 日斜率）
  - 時段過濾（09:30-10:30 vs 其他）
  - ATR 停損/停利
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

BACKTEST_RESULT_PATH = os.path.join(
    os.path.dirname(__file__), '../../../data/backtest_results.json'
)


class HistoricalBacktestEngine:
    """歷史回測引擎 - 讓 AI 從過去學習"""

    def __init__(self):
        self.results: List[Dict] = []
        self.summary: Dict = {}

    # ──────────────────────────────────────────────────
    # 核心：對單一股票進行完整歷史回測
    # ──────────────────────────────────────────────────
    async def backtest_symbol(
        self,
        symbol: str,
        period: str = "1y",         # 回測週期: 1y / 2y / 6mo
        sl_atr_mult: float = 1.5,   # 停損距離 (ATR 倍率)
        tp_atr_mult: float = 2.5,   # 停利距離 (ATR 倍率)
        min_volume_ratio: float = 1.5,
        min_confidence_score: float = 60.0,
        entry_window: Tuple[int, int] = (9, 11),  # 進場時段 (9~11 時)
    ) -> Dict:
        """
        對單一股票進行歷史回測。

        Returns:
            {
              'symbol': str,
              'trades': List[Dict],   # 每筆模擬交易詳情
              'win_rate': float,
              'total': int,
              'avg_profit': float,
              'avg_loss': float,
              'best_conditions': Dict,
              'worst_conditions': Dict,
            }
        """
        try:
            import yfinance as yf

            # 取歷史資料
            for suffix in [".TW", ".TWO"]:
                ticker = yf.Ticker(f"{symbol}{suffix}")
                hist = await asyncio.to_thread(ticker.history, period=period, interval="1d")
                if not hist.empty and len(hist) > 60:
                    break
            else:
                return {'symbol': symbol, 'error': '歷史資料不足'}

            highs  = hist['High'].tolist()
            lows   = hist['Low'].tolist()
            closes = hist['Close'].tolist()
            opens  = hist['Open'].tolist()
            vols   = hist['Volume'].tolist()
            dates  = [str(d.date()) for d in hist.index]

            trades = []
            in_position = False
            entry_price = 0.0
            entry_date = ''
            stop_loss = 0.0
            target = 0.0
            entry_idx = 0

            # ──────────────────────────────
            # 逐日掃描（從第 60 天開始，確保有足夠歷史）
            # ──────────────────────────────
            for i in range(60, len(closes) - 1):
                current = closes[i]
                today_high = highs[i]
                today_low  = lows[i]
                today_open = opens[i]
                today_vol  = vols[i]

                # == 持倉中：檢查出場條件 ==
                if in_position:
                    days_held = i - entry_idx
                    # 觸及停利
                    if today_high >= target:
                        pnl = (target - entry_price) / entry_price * 100
                        trades.append({
                            'type': 'TP', 'symbol': symbol,
                            'entry_date': entry_date, 'exit_date': dates[i],
                            'entry': entry_price, 'exit': target,
                            'pnl_pct': round(pnl, 2), 'days': days_held,
                            'result': 'WIN'
                        })
                        in_position = False
                        continue

                    # 觸及停損
                    if today_low <= stop_loss:
                        pnl = (stop_loss - entry_price) / entry_price * 100
                        trades.append({
                            'type': 'SL', 'symbol': symbol,
                            'entry_date': entry_date, 'exit_date': dates[i],
                            'entry': entry_price, 'exit': stop_loss,
                            'pnl_pct': round(pnl, 2), 'days': days_held,
                            'result': 'LOSS'
                        })
                        in_position = False
                        continue

                    # 持倉超過 10 日強制平倉
                    if days_held >= 10:
                        pnl = (current - entry_price) / entry_price * 100
                        trades.append({
                            'type': 'FORCE', 'symbol': symbol,
                            'entry_date': entry_date, 'exit_date': dates[i],
                            'entry': entry_price, 'exit': current,
                            'pnl_pct': round(pnl, 2), 'days': days_held,
                            'result': 'WIN' if pnl > 0 else 'LOSS'
                        })
                        in_position = False
                    continue

                # == 未持倉：評估進場條件 ==
                # 計算技術指標
                prev_closes = closes[i-60:i]
                prev_vols   = vols[i-60:i]
                prev_highs  = highs[i-60:i]
                prev_lows   = lows[i-60:i]

                ma5  = float(np.mean(prev_closes[-5:]))
                ma20 = float(np.mean(prev_closes[-20:]))
                ma60 = float(np.mean(prev_closes[-60:]))
                avg_vol5 = float(np.mean(prev_vols[-6:-1])) if len(prev_vols) >= 6 else 1
                volume_ratio = today_vol / avg_vol5 if avg_vol5 > 0 else 1

                # 乖離率
                deviation = ((current - ma5) / ma5 * 100) if ma5 > 0 else 0

                # 趨勢斜率
                recent10 = np.array(prev_closes[-10:])
                slope = np.polyfit(range(len(recent10)), recent10, 1)[0]
                trend_up = slope > 0

                # 昨日高低點
                pdh = highs[i-1]
                pdl = lows[i-1]

                # ATR
                trs = [max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
                       for j in range(i-14, i)]
                atr = float(np.mean(trs)) if trs else current * 0.02

                # == 進場信號評分 ==
                score = 50.0
                conditions = {}

                # MA 多頭排列
                if current > ma5 > ma20:
                    score += 15
                    conditions['ma_bull'] = True
                if current > ma60:
                    score += 5
                    conditions['above_ma60'] = True

                # 量能
                if volume_ratio > 3:
                    score += 20
                    conditions['vol_ratio'] = volume_ratio
                elif volume_ratio > 1.5:
                    score += 10
                    conditions['vol_ratio'] = volume_ratio
                elif volume_ratio < 1.2:
                    score -= 20
                    conditions['vol_insufficient'] = True

                # 趨勢向上
                if trend_up:
                    score += 10
                    conditions['trend_up'] = True

                # 乖離率適中
                if 2 <= deviation <= 10:
                    score += 10
                elif deviation > 15:
                    score -= 15

                # 突破昨高（最佳進場品質）
                if current >= pdh * 0.99:
                    score += 15
                    conditions['broke_pdh'] = True
                elif current < pdl:
                    score -= 30  # 跌破昨低

                # 漲幅過大扣分
                day_chg = (current - opens[i]) / opens[i] * 100 if opens[i] > 0 else 0
                if day_chg > 8:
                    score -= 15
                elif 3 <= day_chg <= 8:
                    score += 8

                # == 進場決策 ==
                if score >= min_confidence_score and not in_position:
                    sl = round(current - atr * sl_atr_mult, 2)
                    tp = round(current + atr * tp_atr_mult, 2)

                    in_position = True
                    entry_price = current
                    entry_date = dates[i]
                    stop_loss = sl
                    target = tp
                    entry_idx = i
                    conditions['score'] = round(score, 1)
                    conditions['atr'] = round(atr, 2)

            # 如果還有未平倉部位，強制平倉
            if in_position and len(closes) > 0:
                pnl = (closes[-1] - entry_price) / entry_price * 100
                trades.append({
                    'type': 'FORCE_END', 'symbol': symbol,
                    'entry_date': entry_date, 'exit_date': dates[-1],
                    'entry': entry_price, 'exit': closes[-1],
                    'pnl_pct': round(pnl, 2), 'days': len(closes)-1-entry_idx,
                    'result': 'WIN' if pnl > 0 else 'LOSS'
                })

            # == 統計 ==
            wins   = [t for t in trades if t['result'] == 'WIN']
            losses = [t for t in trades if t['result'] == 'LOSS']
            total  = len(trades)
            win_rate = len(wins) / total if total > 0 else 0

            avg_profit = float(np.mean([t['pnl_pct'] for t in wins])) if wins else 0
            avg_loss   = float(np.mean([t['pnl_pct'] for t in losses])) if losses else 0
            expectancy = win_rate * avg_profit + (1-win_rate) * avg_loss  # 期望值

            avg_days_win  = float(np.mean([t['days'] for t in wins])) if wins else 0
            avg_days_loss = float(np.mean([t['days'] for t in losses])) if losses else 0

            result = {
                'symbol': symbol,
                'period': period,
                'total_trades': total,
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': round(win_rate, 4),
                'avg_profit_pct': round(avg_profit, 2),
                'avg_loss_pct': round(avg_loss, 2),
                'expectancy': round(expectancy, 2),
                'avg_days_in_trade': round(
                    float(np.mean([t['days'] for t in trades])) if trades else 0, 1
                ),
                'avg_days_win': round(avg_days_win, 1),
                'avg_days_loss': round(avg_days_loss, 1),
                'trades': trades[-20:],   # 只保留最近 20 筆作為樣本
                'tested_at': datetime.now().isoformat()
            }

            logger.info(
                f"[回測] {symbol} | {total} 筆 | 勝率 {win_rate:.1%} | "
                f"均獲利 {avg_profit:+.2f}% | 均虧損 {avg_loss:+.2f}% | "
                f"期望值 {expectancy:+.2f}%"
            )
            return result

        except Exception as e:
            logger.error(f"[回測] {symbol} 失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'symbol': symbol, 'error': str(e)}

    # ──────────────────────────────────────────────────
    # 批次回測多檔股票
    # ──────────────────────────────────────────────────
    async def run_batch_backtest(
        self,
        symbols: List[str],
        period: str = "1y",
        concurrency: int = 3
    ) -> Dict:
        """
        對多檔股票進行批次回測，並提取整體學習結論。
        """
        logger.info(
            f"🕰️ [回測時光機] 開始批次回測 {len(symbols)} 支股票 | 週期: {period}"
        )

        semaphore = asyncio.Semaphore(concurrency)

        async def _run_one(sym):
            async with semaphore:
                result = await self.backtest_symbol(sym, period=period)
                await asyncio.sleep(0.5)  # 避免 API 限速
                return result

        raw_results = await asyncio.gather(*[_run_one(s) for s in symbols], return_exceptions=True)

        all_results = []
        for r in raw_results:
            if isinstance(r, Exception):
                continue
            if isinstance(r, dict) and 'error' not in r:
                all_results.append(r)

        if not all_results:
            return {'error': '所有回測均失敗'}

        # ── 整合分析 ──
        total_trades = sum(r['total_trades'] for r in all_results)
        total_wins   = sum(r['wins'] for r in all_results)
        overall_wr   = total_wins / total_trades if total_trades > 0 else 0

        all_profits = [r['avg_profit_pct'] for r in all_results if r['avg_profit_pct'] != 0]
        all_losses  = [r['avg_loss_pct']   for r in all_results if r['avg_loss_pct']   != 0]
        all_expect  = [r['expectancy']     for r in all_results]

        # 最佳/最差標的
        sorted_by_wr = sorted(all_results, key=lambda x: x['win_rate'], reverse=True)
        best_symbols  = [(r['symbol'], r['win_rate']) for r in sorted_by_wr[:5]]
        worst_symbols = [(r['symbol'], r['win_rate']) for r in sorted_by_wr[-3:]]

        summary = {
            'tested_symbols': len(all_results),
            'total_trades': total_trades,
            'overall_win_rate': round(overall_wr, 4),
            'avg_profit_pct': round(float(np.mean(all_profits)), 2) if all_profits else 0,
            'avg_loss_pct':   round(float(np.mean(all_losses)),  2) if all_losses  else 0,
            'avg_expectancy': round(float(np.mean(all_expect)),   2) if all_expect  else 0,
            'best_symbols':  best_symbols,
            'worst_symbols': worst_symbols,
            'symbol_results': {r['symbol']: {
                'win_rate':    r['win_rate'],
                'total':       r['total_trades'],
                'expectancy':  r['expectancy'],
                'avg_profit':  r['avg_profit_pct'],
                'avg_loss':    r['avg_loss_pct'],
            } for r in all_results},
            'period': period,
            'run_at': datetime.now().isoformat()
        }

        # ── 自動學習：更新偏好清單與權重 ──
        self._apply_learning(summary, all_results)

        # 儲存結果
        os.makedirs(os.path.dirname(BACKTEST_RESULT_PATH), exist_ok=True)
        with open(BACKTEST_RESULT_PATH, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(
            f"✅ [回測完成] {len(all_results)}/{len(symbols)} 支 | "
            f"總交易 {total_trades} 筆 | 整體勝率 {overall_wr:.1%} | "
            f"平均期望值 {summary['avg_expectancy']:+.2f}%"
        )

        return summary

    def _apply_learning(self, summary: Dict, results: List[Dict]):
        """從回測結果中提取知識，更新系統配置"""
        # 1. 更新優選標的清單
        best_symbols = [s for s, wr in summary['best_symbols'] if wr >= 0.50]
        preferred_path = os.path.join(os.path.dirname(BACKTEST_RESULT_PATH), 'preferred_symbols.json')
        os.makedirs(os.path.dirname(preferred_path), exist_ok=True)

        existing_preferred = []
        try:
            if os.path.exists(preferred_path):
                with open(preferred_path) as f:
                    existing_preferred = json.load(f).get('preferred', [])
        except Exception:
            pass

        merged = list(set(existing_preferred + best_symbols))
        with open(preferred_path, 'w') as f:
            json.dump({
                'preferred': merged,
                'note': f'從回測({summary["period"]})中學到的高勝率標的',
                'updated_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        # 2. 根據整體勝率調整因子權重
        overall_wr = summary['overall_win_rate']
        weights_path = os.path.join(os.path.dirname(BACKTEST_RESULT_PATH), 'learning_weights.json')

        existing_weights = {}
        try:
            if os.path.exists(weights_path):
                with open(weights_path) as f:
                    existing_weights = json.load(f).get('weights', {})
        except Exception:
            pass

        from app.services.trade_learning_engine import DEFAULT_WEIGHTS
        weights = {**DEFAULT_WEIGHTS, **existing_weights}

        if overall_wr < 0.45:
            weights['risk_high'] = max(-25, weights.get('risk_high', -15) - 5)
            weights['volume_insufficient'] = max(-30, weights.get('volume_insufficient', -20) - 5)
            weights['change_pct_excessive'] = max(-25, weights.get('change_pct_excessive', -20) - 5)
            logger.warning(f"📉 整體勝率 {overall_wr:.1%} 偏低，自動提高進場門檻")
        elif overall_wr > 0.60:
            weights['volume_ratio_high'] = min(25, weights.get('volume_ratio_high', 20) + 3)
            weights['ma_bull_alignment'] = min(20, weights.get('ma_bull_alignment', 15) + 2)
            logger.info(f"📈 整體勝率 {overall_wr:.1%} 優秀，強化有效因子")

        with open(weights_path, 'w') as f:
            json.dump({
                'weights': weights,
                'updated_at': datetime.now().isoformat(),
                'metadata': {
                    'source': 'backtest',
                    'period': summary['period'],
                    'overall_win_rate': overall_wr,
                    'total_trades': summary['total_trades']
                }
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"🧠 [學習更新] 優選標的: {merged} | 權重已更新")


# ── 單例 ──
backtest_engine = HistoricalBacktestEngine()


# ── 快速執行入口 ──
async def run_learning_backtest(
    watchlist: List[str] = None,
    period: str = "1y"
) -> Dict:
    """
    對監控清單進行完整歷史回測並學習。
    可在 API 端點或排程任務中呼叫。
    """
    if watchlist is None:
        watchlist = [
            # 主要科技 + 半導體
            "2330", "2317", "2454", "2337", "2344",
            "3034", "2303", "2379", "3231", "6770",
            # 金融
            "2881", "2882", "2886",
            # 精選小型股
            "6257", "8046", "1802",
        ]

    return await backtest_engine.run_batch_backtest(watchlist, period=period)
