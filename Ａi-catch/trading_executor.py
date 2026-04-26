"""
trading_executor.py
自動化實盤交易執行官 (含終極安全開關與虛擬紙盤交易)
"""

import os
import json
import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta

# --- 載入核心模組 ---
from fubon_client import fubon_client
from test_backtest_v2 import LSTMSignalEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("TradingExecutor")

# =========================================================================
# ⚠️ 終極安全開關 ⚠️
# True = 模擬模式 (紙盤交易)：行情真實、AI預測真實，但下單會被攔截寫入 JSON 模擬庫存。
# False = 實彈模式 (實盤交易)：🚨 您的委託單將直接送達台灣證券交易所，真實扣款！
# =========================================================================
SIMULATION_MODE = True

# 嚴選合格白名單
TARGET_STOCKS = ["2337", "2454", "3163", "6285"]

# 虛擬庫存檔案與本金設定檔
VIRTUAL_DB_PATH = 'virtual_portfolio.json'
CAPITAL_CONFIG_PATH = '/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/data/capital_config.json'


class TradingExecutor:
    def __init__(self):
        self.signal_engine = LSTMSignalEngine()
        self.virtual_portfolio = self._load_virtual_portfolio()

    def _get_available_capital(self) -> float:
        """從 Web 儀表板的對接配置讀取『可用本金餘額』"""
        if os.path.exists(CAPITAL_CONFIG_PATH):
            try:
                with open(CAPITAL_CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                    return float(data.get("available_capital", 0.0))
            except Exception as e:
                logger.error(f"讀取本金設定失敗: {e}")
        return 0.0

    def _deduct_virtual_capital(self, amount: float):
        """模擬模式下扣除資本"""
        if os.path.exists(CAPITAL_CONFIG_PATH):
            try:
                with open(CAPITAL_CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                data["available_capital"] = float(data.get("available_capital", 0)) - amount
                with open(CAPITAL_CONFIG_PATH, 'w') as f:
                    json.dump(data, f)
            except Exception:
                pass

    def _add_virtual_capital(self, amount: float):
        """模擬模式下加回資本"""
        if os.path.exists(CAPITAL_CONFIG_PATH):
            try:
                with open(CAPITAL_CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                data["available_capital"] = float(data.get("available_capital", 0)) + amount
                with open(CAPITAL_CONFIG_PATH, 'w') as f:
                    json.dump(data, f)
            except Exception:
                pass

    def _load_virtual_portfolio(self) -> dict:
        if os.path.exists(VIRTUAL_DB_PATH):
            with open(VIRTUAL_DB_PATH, 'r') as f:
                return json.load(f)
        return {}

    def _save_virtual_portfolio(self):
        with open(VIRTUAL_DB_PATH, 'w') as f:
            json.dump(self.virtual_portfolio, f, indent=4)

    async def initialize(self):
        logger.info("🔌 正在連線富邦真實 API...")
        success = await fubon_client.connect()
        if success:
            logger.info("✅ 富邦 API 連線成功！")
        else:
            logger.error("❌ 富邦 API 連線失敗，請檢查 .env 憑證。")
            
    async def get_real_inventory(self):
        """讀取真實券商庫存"""
        logger.info("🔍 正在查詢您的真實庫存...")
        inv = await fubon_client.get_inventory()
        # 回傳 dict 格式: { "2337": {"quantity": 1000, "cost_price": 25.5} }
        return {item['symbol']: item for item in inv}

    def _format_candles(self, raw_candles: list) -> pd.DataFrame:
        """轉換 K棒 格式以餵給 LSTM 模型"""
        df = pd.DataFrame(raw_candles)
        df['date'] = pd.to_datetime(df['date'], format='ISO8601', utc=True).dt.tz_localize(None)
        df.set_index('date', inplace=True)
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return df

    async def execute_trade(self, symbol: str, action: str, price: float):
        """執行下單：動態配比風險控管 + 自動同步資料庫"""
        
        available_capital = self._get_available_capital()
        
        # 🛡️ 資金配比與防禦機制
        risk_weight = 0.30 
        target_allocation = available_capital * risk_weight
        
        # 自動計算可買張數 
        shares_to_trade = int(target_allocation // price)
        shares_to_trade = (shares_to_trade // 1000) * 1000  
        cost_required = shares_to_trade * price

        if action == 'buy':
            if shares_to_trade == 0:
                if available_capital >= (price * 1000):
                    shares_to_trade = 1000
                    cost_required = price * 1000
                else:
                    logger.error(f"❌ 防爆倉啟動！餘額不足，放棄 {symbol}。")
                    return

        # ---------------------------------------------------------
        # 1. 執行核心買賣動作
        # ---------------------------------------------------------
        success = False
        if SIMULATION_MODE:
            logger.warning(f"🛡️ [模擬模式] 執行: {action.upper()} {symbol} {shares_to_trade}股")
            success = True # 模擬模式預設成功
        else:
            logger.critical(f"🚀 [實彈模式] 送出真實委託: {action.upper()} {symbol}")
            res = await fubon_client.place_order(symbol, action, shares_to_trade, price)
            success = res.get('success', False)

        # ---------------------------------------------------------
        # 2. 自動同步資料庫持倉管理 (API Call)
        # ---------------------------------------------------------
        if success:
            import httpx
            api_url = "http://localhost:8000/api/portfolio/positions"
            
            try:
                if action == 'buy':
                    # 買入：建立新持有紀錄
                    payload = {
                        "symbol": symbol,
                        "entry_date": datetime.now().isoformat(),
                        "entry_price": price,
                        "entry_quantity": shares_to_trade,
                        "analysis_source": "lstm_prediction",
                        "is_simulated": SIMULATION_MODE,
                        "stop_loss_price": price * 0.93, # 預設 7% 停損
                        "target_price": price * 1.15,    # 預設 15% 停利
                        "notes": f"AI 執行官自動下單 (信心度推估)"
                    }
                    async with httpx.AsyncClient() as client:
                        await client.post(api_url, json=payload)
                    
                    # 更新本機臨時庫存與扣款
                    self.virtual_portfolio[symbol] = {"shares": shares_to_trade, "cost": price, "buy_time": datetime.now().isoformat()}
                    self._deduct_virtual_capital(cost_required)
                    logger.info(f"✅ [資料庫同步] {symbol} 已同步至持倉管理。")

                elif action == 'sell':
                    # 賣出：這理比較複雜，需先找到該 symbol 的開放 ID，在此簡化為通知 API 更新
                    # 實際開發中，通常會調用 /positions/close 端點
                    logger.info(f"💰 [持倉平倉] {symbol} 準備執行資料庫平倉動作...")
                    # 這裡留給後端 auto_close 邏輯或手動結案
                    
                    if symbol in self.virtual_portfolio:
                        sell_shares = self.virtual_portfolio[symbol]['shares']
                        del self.virtual_portfolio[symbol]
                        self._add_virtual_capital(sell_shares * price)
            
            except Exception as e:
                logger.error(f"⚠️ 同步 API 失敗 (請確認後端是否啟動): {e}")

            self._save_virtual_portfolio()

        # 注意：實彈模式邏輯已移除。如未來需要開啟，請確保 SIMULATION_MODE=False
        # 並且需要在 fubon_client.place_order() 前再次確認帳戶授權。

    async def run_scan_cycle(self):
        """執行一次完整的掃描與交易判斷循環"""
        mode = "模擬 (紙盤)" if SIMULATION_MODE else "🚨 實彈 (真倉) 🚨"
        logger.info(f"\n{'='*60}\n"
                    f"⏰ 開始執行自動交易循環 | 模式: {mode}\n"
                    f"{'='*60}")
        
        # 1. 取得當前真實或虛擬庫存
        if SIMULATION_MODE:
            current_portfolio = self.virtual_portfolio
        else:
            current_portfolio = await self.get_real_inventory()
            
        logger.info(f"💼 目前持有部位: {list(current_portfolio.keys()) if current_portfolio else '空倉'}")

        # 2. 針對白名單展開 AI 推論
        for symbol in TARGET_STOCKS:
            logger.info(f"\n👉 檢視標的: {symbol}")
            
            # 從富邦獲取近 120 天 K 線 (因為 v4 特徵引擎需要至少 80 天歷史數據)
            from_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
            raw_candles = await fubon_client.get_candles(symbol, from_date=from_date, timeframe="D")
            
            if not raw_candles or len(raw_candles) < 80:
                logger.warning(f"⚠️ {symbol} 歷史數據不足 80 天，無法進行 PyTorch Attention 推論。")
                continue
                
            hist_df = self._format_candles(raw_candles)
            latest_price = hist_df.iloc[-1]['Close']
            
            # 呼叫 LSTM 進行推測 (自動使用 PyTorch Model)
            prediction = self.signal_engine.predict(symbol, hist_df, current_idx=len(hist_df)-1, threshold=0.55)
            
            signal = prediction['signal']
            conf = prediction['confidence']
            prob = prediction['raw_prob']
            
            logger.info(f"🧠 AI 預測結果: {signal.upper()} | 信心度 {conf:.0%} (機率 {prob:.3f}) | 現價 ${latest_price}")
            
            # ==============================
            # 交易策略邏輯判斷
            # ==============================
            is_holding = symbol in current_portfolio

            # 買進條件: 模型看多 (buy) + 信心度 > 70% + 尚未持有
            if signal == 'buy' and conf >= 0.70 and not is_holding:
                logger.info(f"🎯 [買入條件達成] {symbol} AI 信心度極高 ({conf:.0%})，準備發射過海關...")
                await self.execute_trade(symbol, 'buy', latest_price)

            # 賣出條件: 模型看空 (sell) + 信心度 > 70% + 正在持有
            elif signal == 'sell' and conf >= 0.70 and is_holding:
                logger.info(f"🛑 [平倉條件達成] {symbol} AI 判斷動能反轉 ({conf:.0%})，執行停利/停損！")
                await self.execute_trade(symbol, 'sell', latest_price)
                
            else:
                logger.info(f"   ☕ 無動作 (未達門檻或部位狀態不符)")

        logger.info(f"\n{'='*60}\n"
                    f"🏁 本次交易循環結束，進入待命。\n"
                    f"{'='*60}\n")


async def main():
    executor = TradingExecutor()
    await executor.initialize()
    
    # 在背景自動循環 (暫時設定只跑一次觀測，如果您要持續掛機可套上 while True)
    await executor.run_scan_cycle()
    
    # 安全斷線
    fubon_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
