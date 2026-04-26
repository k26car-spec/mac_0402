"""
法人籌碼特徵爬取器
====================
從 TWSE 官方 API 獲取：
  1. 三大法人每日買賣超（外資、投信、自營商）
  2. 融資融券餘額
  3. 整合為可訓練的 DataFrame

使用方式：
    from chip_feature_fetcher import ChipFeatureFetcher
    fetcher = ChipFeatureFetcher()
    df = fetcher.get_chip_features('2330', start='2023-01-01', end='2026-02-21')
"""

import requests
import pandas as pd
import numpy as np
import time
import os
import json
import logging
from datetime import datetime, timedelta
from functools import lru_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = "chip_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
SLEEP = 0.5   # 每次請求間隔，避免被封


class ChipFeatureFetcher:
    """
    從 TWSE 官方 API 逐日爬取法人籌碼特徵
    包含：外資買賣超、投信買賣超、自營商買賣超、融資餘額、券資比
    """

    # ─── 1. 三大法人（T86）─────────────────────────────────
    def _fetch_t86_day(self, date: str) -> pd.DataFrame | None:
        """
        爬取單日全市場三大法人買賣超
        date: YYYYMMDD 格式
        回傳: 以代號為 index 的 DataFrame
        """
        cache_file = os.path.join(CACHE_DIR, f"t86_{date}.json")

        # 優先讀取緩存
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                raw = json.load(f)
        else:
            url = ("https://www.twse.com.tw/rwd/zh/fund/T86"
                   f"?response=json&date={date}&selectType=ALLBUT0999")
            try:
                r = requests.get(url, headers=HEADERS, timeout=8)
                raw = r.json()
                if raw.get('data'):
                    with open(cache_file, 'w') as f:
                        json.dump(raw, f)
            except Exception as e:
                logger.warning(f"T86 {date} 請求失敗: {e}")
                return None
            time.sleep(SLEEP)

        if not raw.get('data'):
            return None

        fields = raw.get('fields', [])
        df = pd.DataFrame(raw['data'], columns=fields)
        df = df.rename(columns={
            '證券代號':                         'symbol',
            '外陸資買賣超股數(不含外資自營商)':   'foreign_net',      # 外資買賣超
            '投信買賣超股數':                    'trust_net',        # 投信買賣超
            '自營商買賣超股數':                  'dealer_net',       # 自營商買賣超
            '三大法人買賣超股數':                'inst_net_total',   # 三大法人合計
        })

        # 只保留有用的欄位（部分欄位可能不存在）
        keep = ['symbol', 'foreign_net', 'trust_net', 'dealer_net', 'inst_net_total']
        keep = [c for c in keep if c in df.columns]
        df = df[keep].copy()
        df['symbol'] = df['symbol'].str.strip()

        # 去除逗號、轉數字
        for col in keep[1:]:
            df[col] = (df[col].astype(str)
                       .str.replace(',', '', regex=False)
                       .str.strip()
                       .replace('', '0'))
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df.set_index('symbol', inplace=True)
        return df

    # ─── 2. 融資融券（MI_MARGN）────────────────────────────
    def _fetch_margin_day(self, date: str) -> pd.DataFrame | None:
        """
        爬取單日融資融券餘額
        """
        cache_file = os.path.join(CACHE_DIR, f"margin_{date}.json")

        if os.path.exists(cache_file):
            with open(cache_file) as f:
                raw = json.load(f)
        else:
            url = ("https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
                   f"?response=json&date={date}&selectType=ALL")
            try:
                r = requests.get(url, headers=HEADERS, timeout=8)
                raw = r.json()
                if raw.get('tables'):
                    with open(cache_file, 'w') as f:
                        json.dump(raw, f)
            except Exception as e:
                logger.warning(f"MI_MARGN {date} 請求失敗: {e}")
                return None
            time.sleep(SLEEP)

        if not raw.get('tables') or len(raw['tables']) < 2:
            return None

        # tables[1] 是融資融券彙總明細
        table = raw['tables'][1]
        if not table.get('data'):
            return None

        # 直接用位置索引，避免重複列名問題
        # fields: ['代號', '名稱', '買進', '賣出', '現金償還', '前日餘額', '今日餘額', ...]
        raw_data = table.get('data', [])
        if not raw_data or len(raw_data[0]) < 7:
            return None

        records = []
        for row in raw_data:
            sym = str(row[0]).strip()
            bal = str(row[6]).replace(',', '').strip()
            try:
                bal_val = float(bal)
            except ValueError:
                bal_val = 0.0
            records.append({'symbol': sym, 'margin_balance': bal_val})

        df2 = pd.DataFrame(records)
        df2.set_index('symbol', inplace=True)
        return df2

    # ─── 3. 整合單日法人特徵 ──────────────────────────────
    def _get_day_features(self, date_str: str, symbol: str) -> dict | None:
        """
        獲取指定日期、指定股票的法人特徵
        date_str: YYYYMMDD
        """
        result = {'date': date_str}

        # 三大法人
        t86 = self._fetch_t86_day(date_str)
        if t86 is not None and symbol in t86.index:
            row = t86.loc[symbol]
            result['foreign_net']    = float(row.get('foreign_net', 0))
            result['trust_net']      = float(row.get('trust_net', 0))
            result['dealer_net']     = float(row.get('dealer_net', 0))
            result['inst_net_total'] = float(row.get('inst_net_total', 0))
        else:
            result['foreign_net']    = 0.0
            result['trust_net']      = 0.0
            result['dealer_net']     = 0.0
            result['inst_net_total'] = 0.0

        # 融資餘額
        margin = self._fetch_margin_day(date_str)
        if margin is not None and symbol in margin.index:
            result['margin_balance'] = float(margin.loc[symbol, 'margin_balance'])
        else:
            result['margin_balance'] = 0.0

        return result

    # ─── 4. 批次爬取（日期區間）─────────────────────────────
    def fetch_date_range(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """
        爬取指定日期區間內的所有交易日法人特徵
        start/end: 'YYYY-MM-DD'
        """
        start_dt = datetime.strptime(start, '%Y-%m-%d')
        end_dt   = datetime.strptime(end,   '%Y-%m-%d')

        results = []
        current = start_dt
        total_days = (end_dt - start_dt).days
        processed = 0

        logger.info(f"開始爬取 {symbol} 法人數據：{start} ~ {end}")

        while current <= end_dt:
            # 跳過週末
            if current.weekday() < 5:  # 0=Mon, 4=Fri
                date_str = current.strftime('%Y%m%d')
                feats = self._get_day_features(date_str, symbol)
                if feats and any(v != 0 for k, v in feats.items() if k != 'date'):
                    feats['date'] = current.strftime('%Y-%m-%d')
                    results.append(feats)

                processed += 1
                if processed % 20 == 0:
                    pct = processed / (total_days * 5/7) * 100
                    logger.info(f"  進度: {processed}/{int(total_days*5/7)} ({min(pct,100):.0f}%) ~ {date_str}")

            current += timedelta(days=1)

        if not results:
            logger.warning(f"{symbol}: 未爬到任何法人數據")
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').set_index('date')
        logger.info(f"✅ {symbol} 法人數據爬取完成：{len(df)} 筆")
        return df

    # ─── 5. 計算衍生特徵 ──────────────────────────────────
    @staticmethod
    def compute_derived(df: pd.DataFrame) -> pd.DataFrame:
        """
        計算衍生法人特徵（累積、動能、方向一致性）
        """
        df = df.copy()

        # 累積法人買超（5日、10日、20日）
        for w in [5, 10, 20]:
            df[f'foreign_cum{w}']    = df['foreign_net'].rolling(w).sum()
            df[f'inst_total_cum{w}'] = df['inst_net_total'].rolling(w).sum()

        # 外資 5 日動能（最近5日是否持續淨買超）
        df['foreign_momentum'] = df['foreign_net'].rolling(5).mean()

        # 三大法人方向一致性（外資、投信、自營商同向買超 = 1）
        df['inst_consensus'] = (
            (df['foreign_net'] > 0).astype(int) +
            (df['trust_net']   > 0).astype(int) +
            (df['dealer_net']  > 0).astype(int)
        )  # 0~3，3 = 全部看多

        # 融資餘額變化（增加 = 散戶看多，反指標）
        df['margin_chg_5d'] = df['margin_balance'].diff(5)
        df['margin_ratio']  = df['margin_balance'] / (df['margin_balance'].rolling(20).mean() + 1)

        return df

    # ─── 6. 主入口 ────────────────────────────────────────
    def get_chip_features(self, symbol: str,
                          start: str = '2023-01-01',
                          end: str   = None) -> pd.DataFrame:
        """
        完整法人籌碼特徵（包含衍生指標）

        Args:
            symbol: 股票代號（如 '2330'）
            start:  開始日期 'YYYY-MM-DD'
            end:    結束日期（預設今日）

        Returns:
            DataFrame，index = 日期，欄位 = 法人特徵
        """
        if end is None:
            end = datetime.now().strftime('%Y-%m-%d')

        raw = self.fetch_date_range(symbol, start, end)
        if raw.empty:
            return pd.DataFrame()

        df = self.compute_derived(raw)
        # 只刪除核心特徵缺失的行（不強求衍生特徵全部有值）
        core_cols = ['foreign_net', 'trust_net', 'dealer_net', 'inst_net_total']
        df = df.dropna(subset=core_cols)
        return df


# ─── 快速測試 ──────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else '2881'
    print(f"\n🧪 測試：{symbol} 最近 3 個月法人籌碼")
    start = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    fetcher = ChipFeatureFetcher()
    df = fetcher.get_chip_features(symbol, start=start)

    if df.empty:
        print("❌ 無法獲取數據")
    else:
        print(f"\n✅ 成功！形狀: {df.shape}")
        print(df.tail(5).to_string())
        print(f"\n欄位: {list(df.columns)}")
