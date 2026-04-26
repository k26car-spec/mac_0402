"""
批量法人籌碼服務 - 負責批次抓取及存入數據庫
"""
import asyncio
import httpx
import logging
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import select, insert, update, func, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import text

from app.database.connection import async_session
from app.models.institutional import InstitutionalTrading, InstitutionalContinuous

logger = logging.getLogger(__name__)

class BatchInstitutionalService:
    """處理全市場法人買賣超批次抓取"""
    
    TWSE_RWD_T86 = "https://www.twse.com.tw/rwd/zh/fund/T86"
    TPEX_RWD_INST = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.twse.com.tw/zh/page/trading/fund/T86.html',
        'Accept': 'application/json, text/plain, */*'
    }

    async def crawl_and_save_t86(self, date_str: str = None) -> Dict:
        """
        抓取特定日期的 TWSE (上市) 全市場法人買賣超並存入 DB
        date_str: YYYYMMDD
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")
            
        logger.info(f"💾 開始批次抓取並儲存 {date_str} 的上市法人買賣超...")
        
        params = {
            'date': date_str,
            'selectType': 'ALLBUT0999', # 全部不含權證
            'response': 'json'
        }
        
        try:
            async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
                r = await client.get(self.TWSE_RWD_T86, params=params)
                if r.status_code != 200:
                    return {"status": "error", "message": f"TWSE API 失敗 (Status: {r.status_code})"}
                
                data = r.json()
                if data.get("stat") != "OK":
                    return {"status": "error", "message": f"該日期查無資料: {data.get('stat')}"}
                
                rows = data.get("data", [])
                if not rows:
                    return {"status": "error", "message": "無資料列"}

                # 解析並批次儲存
                count = await self._save_to_db(rows, date_str, "TWSE")
                return {"status": "success", "count": count, "date": date_str}
                
        except Exception as e:
            logger.error(f"❌ 批次抓取法人失敗: {e}")
            return {"status": "error", "message": str(e)}

    async def crawl_and_save_tpex(self, date_str: str = None) -> Dict:
        """
        抓取特定日期的 TPEx (上櫃) 全市場法人買賣超並存入 DB
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")
            
        # 轉換為民國日期格式 (112/03/31)
        dt = datetime.strptime(date_str, "%Y%m%d")
        roc_date = f"{dt.year - 1911}/{dt.strftime('%m/%d')}"
        
        logger.info(f"💾 開始批次抓取並儲存 {date_str} 的上櫃法人買賣超...")
        
        params = {
            'l': 'zh-tw',
            'd': roc_date,
            'se': 'EW', # 全部
            't': 'D'
        }
        
        try:
            async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
                r = await client.get(self.TPEX_RWD_INST, params=params)
                if r.status_code != 200:
                    return {"status": "error", "message": f"TPEx API 失敗 (Status: {r.status_code})"}
                
                data = r.json()
                # TPEx 格式有些微不同
                rows = []
                if "tables" in data and len(data["tables"]) > 0:
                    rows = data["tables"][0].get("data", [])
                elif "aaData" in data:
                    rows = data.get("aaData", [])
                
                if not rows:
                    return {"status": "error", "message": "上櫃無資料列"}

                count = await self._save_to_db(rows, date_str, "TPEX")
                return {"status": "success", "count": count, "date": date_str}
                
        except Exception as e:
            logger.error(f"❌ 批次抓取上櫃法人失敗: {e}")
            return {"status": "error", "message": str(e)}

    async def _save_to_db(self, rows: List[List], date_str: str, market: str) -> int:
        """
        將解析後的原始列資料存入資料庫
        """
        trade_date = datetime.strptime(date_str, "%Y%m%d").date()
        save_count = 0
        
        async with async_session() as session:
            # 首先刪除該日期同市場的所有舊資料，避免重複
            # 注意：這裡由於可能同時包含上市櫃，我們只依賴 trade_date + symbol UniqueConstraint
            for row in rows:
                try:
                    # TWSE 欄位: 
                    # 0:代碼, 1:名稱, 2:外資買, 3:外資賣, 4:外資淨, ... 10:投信淨, 11:自營商淨, ... 18:合計
                    # TPEX 欄位: 
                    # 0:代碼, 1:名稱, ... 10:外資淨, 13:投信淨, 22:自營商淨, 23:合計
                    
                    symbol = str(row[0]).strip()
                    name = str(row[1]).strip()
                    
                    def _p(v):
                        try: return int(str(v).replace(',', ''))
                        except: return 0
                    
                    if market == "TWSE":
                        f_net = _p(row[4])
                        i_net = _p(row[10]) # 投信
                        d_net = _p(row[11]) # 自營商
                        total = _p(row[18])
                    else:
                        f_net = _p(row[10])
                        i_net = _p(row[13])
                        d_net = _p(row[22])
                        total = _p(row[23])
                    
                    # 準備並存入 (Upsert)
                    # 這裡使用 sqlalchemy 的 insert 加上 on_conflict_do_update
                    # 簡單點可以先 delete 再 insert 或者 try-except check
                    
                    # 先查是否有同日期同代碼
                    query = select(InstitutionalTrading).where(
                        InstitutionalTrading.trade_date == trade_date,
                        InstitutionalTrading.symbol == symbol
                    )
                    existing = await session.execute(query)
                    record = existing.scalar_one_or_none()
                    
                    if record:
                        record.foreign_net = f_net
                        record.investment_net = i_net
                        record.dealer_net = d_net
                        record.total_net = total
                    else:
                        new_record = InstitutionalTrading(
                            trade_date=trade_date,
                            symbol=symbol,
                            stock_name=name,
                            foreign_net=f_net,
                            investment_net=i_net,
                            dealer_net=d_net,
                            total_net=total
                        )
                        session.add(new_record)
                    
                    save_count += 1
                    
                    # 每 100 筆 commit 一次或統一最後 commit
                    if save_count % 100 == 0:
                        await session.flush()
                except Exception as row_error:
                    logger.debug(f"Row parse error for {row[0]}: {row_error}")
                    continue
            
            await session.commit()
            logger.info(f"✅ 已儲存 {save_count} 筆 {market} 法人交易紀錄到資料庫")
            
        return save_count

    async def get_stock_institutional_history(self, symbol: str, limit: int = 30) -> List[Dict]:
        """從資料庫讀取特定股票的法人買賣超歷史"""
        async with async_session() as session:
            query = select(InstitutionalTrading).where(
                InstitutionalTrading.symbol == symbol
            ).order_by(InstitutionalTrading.trade_date.desc()).limit(limit)
            
            result = await session.execute(query)
            records = result.scalars().all()
            
            return [
                {
                    "date": r.trade_date.strftime("%Y-%m-%d"),
                    "foreign_net": int(r.foreign_net),
                    "investment_net": int(r.investment_net),
                    "dealer_net": int(r.dealer_net),
                    "total_net": int(r.total_net)
                }
                for r in records
            ]

    async def get_batch_latest_institutional(self, symbols: List[str]) -> Dict[str, int]:
        """批次獲取多個股票代碼的「最新一天」合計買賣超"""
        if not symbols:
            return {}
            
        async with async_session() as session:
            latest_date_query = select(func.max(InstitutionalTrading.trade_date))
            latest_date_results = await session.execute(latest_date_query)
            latest_date = latest_date_results.scalar()
            
            if not latest_date:
                return {}
                
            query = select(
                InstitutionalTrading.symbol, 
                InstitutionalTrading.total_net
            ).where(
                InstitutionalTrading.trade_date == latest_date,
                InstitutionalTrading.symbol.in_(symbols)
            )
            
            result = await session.execute(query)
            rows = result.all()
            
            return {r.symbol: int(r.total_net) for r in rows}

    async def sync_missing_dates(self, requested_days: int = 30) -> List[str]:
        """
        比對資料庫，找出最近 N 個交易日中缺少的日期，並執行補抓。
        返回補抓成功的日期列表。
        """
        missing_dates = []
        today = datetime.now()
        
        # 1. 產生最近 N 個可能的交易日 (排除週末)
        potential_dates = []
        check_date = today
        while len(potential_dates) < requested_days:
            if check_date.weekday() < 5: # 0-4 是週一至週五
                potential_dates.append(check_date.date())
            check_date -= timedelta(days=1)
            # 安全閥，不要找超過 60 天
            if (today.date() - check_date.date()).days > 60:
                break
        
        async with async_session() as session:
            # 2. 查詢資料庫中已存在的交易日期 (不重複)
            query = select(InstitutionalTrading.trade_date).distinct().where(
                InstitutionalTrading.trade_date.in_(potential_dates)
            )
            result = await session.execute(query)
            existing_dates = {r.trade_date for r in result.all()}
            
            # 3. 找出缺失的日期
            missing_dates = [d for d in potential_dates if d not in existing_dates]
            # 排序：由新到舊
            missing_dates.sort(reverse=True)
            
            if not missing_dates:
                logger.info("✅ 所有的歷史法人籌碼日期皆已存在，無需補抓。")
                return []
            
            logger.info(f"🔍 發現缺失日期: {missing_dates}，準備開始補抓...")
            
            success_dates = []
            # 限制單次補抓數量，避免被 TWSE 封鎖 (例如一次最多補 10 天)
            for d in missing_dates[:10]:
                d_str = d.strftime("%Y%m%d")
                
                # 抓取上市
                res_t86 = await self.crawl_and_save_t86(d_str)
                # 抓取上櫃
                res_tpex = await self.crawl_and_save_tpex(d_str)
                
                if res_t86["status"] == "success" or res_tpex["status"] == "success":
                    success_dates.append(d_str)
                
                # 每次抓取間隔一下，降低風險
                await asyncio.sleep(1.5)
                
            return success_dates

batch_institutional_service = BatchInstitutionalService()
