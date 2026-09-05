import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TrendingDown, TrendingUp, Activity, Shield, Crosshair, AlertTriangle, ArrowDown, ArrowUp, DollarSign, BarChart2, Target, Layers, RefreshCw, Loader2, Wifi, WifiOff, Search, HelpCircle, X, BookOpen, Play, Square, Zap } from 'lucide-react';
import MarketDecision from './MarketDecision';

const API_BASE = 'http://localhost:8000';

const DayTradePro = () => {
    // --- 核心狀態 ---
    const [symbol, setSymbol] = useState('');
    const [inputSymbol, setInputSymbol] = useState(''); // 輸入框的代碼
    const [loading, setLoading] = useState(false);
    const [stockName, setStockName] = useState('');
    const [showGuide, setShowGuide] = useState(false); // 預設隱藏操作說明
    const [isMonitoring, setIsMonitoring] = useState(false); // 是否在監控中
    const [monitorStartTime, setMonitorStartTime] = useState(null); // 監控開始時間
    const intervalRefs = useRef([]); // 保存 interval 引用

    // 即時價格數據
    const [price, setPrice] = useState(0);
    const [prevClose, setPrevClose] = useState(0);
    const [open, setOpen] = useState(0);
    const [high, setHigh] = useState(0);
    const [low, setLow] = useState(0);
    const [change, setChange] = useState(0);
    const [volume, setVolume] = useState(0);

    // VWAP 相關
    const [vwap, setVwap] = useState(0);
    const [vwapDeviation, setVwapDeviation] = useState(0);

    // 量價分析
    const [volumePriceData, setVolumePriceData] = useState(null);

    // 籌碼/大戶數據
    const [institutionalData, setInstitutionalData] = useState(null);
    const [bigMoneyFlow, setBigMoneyFlow] = useState(0);

    // 支撐壓力位
    const [supportLevel, setSupportLevel] = useState(0);
    const [resistanceLevel, setResistanceLevel] = useState(0);

    // ATR (波動率)
    const [atr, setAtr] = useState(0);

    // 連線狀態
    const [connected, setConnected] = useState(false);
    const [backendOnline, setBackendOnline] = useState(false);

    // 五檔報價 (Order Book)
    const [orderBook, setOrderBook] = useState({ bids: [], asks: [] });
    const [totalBidVolume, setTotalBidVolume] = useState(0);
    const [totalAskVolume, setTotalAskVolume] = useState(0);

    // 成交明細 (Time & Sales)
    const [tickData, setTickData] = useState([]);

    // 數據來源標示
    const [quoteSource, setQuoteSource] = useState('等待連線');  // 報價來源

    // 數據來源
    const [orderBookSource, setOrderBookSource] = useState('等待連線');

    // 出場訊號分析
    const [positionSide, setPositionSide] = useState('long');  // 'long' 或 'short'
    const [entryPrice, setEntryPrice] = useState(0);  // 進場價
    const [exitSignal, setExitSignal] = useState(null);  // 出場訊號結果

    // 進場訊號分析
    const [entrySignal, setEntrySignal] = useState(null);  // 進場訊號結果

    // 🆕 止跌分析 (Buy on Dip)
    const [dipResult, setDipResult] = useState(null);

    // 區塊展開/收合狀態
    const [expandPowerDepth, setExpandPowerDepth] = useState(true);  // 買賣力道深度
    const [expandEntrySignal, setExpandEntrySignal] = useState(true);  // 進場訊號
    const [expandExitSignal, setExpandExitSignal] = useState(true);  // 出場訊號

    // --- 獲取五檔報價 (優先富邦 API) ---
    const fetchOrderBook = useCallback(async (stockCode) => {
        if (!stockCode || stockCode.length < 4) return;
        try {
            // 優先使用富邦 API，添加 5 秒超時
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const res = await fetch(`${API_BASE}/api/fubon/orderbook/${stockCode}`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await res.json();

            if (data.success) {
                setOrderBook({ bids: data.bids || [], asks: data.asks || [] });
                setTotalBidVolume(data.totalBidVolume || 0);
                setTotalAskVolume(data.totalAskVolume || 0);

                // 更完整的來源標識
                const source = data.source || 'unknown';
                setOrderBookSource(
                    source === 'fubon' || source === 'fubon_ws' ? '富邦API (真實)' :
                        source === 'fubon_quote' ? '富邦報價 (部分真實)' :
                            source === 'yahoo' ? 'Yahoo Finance' :
                                source === 'mock' ? '模擬數據 (非交易時段)' :
                                    source
                );
            } else {
                // API 返回成功但 success=false
                setOrderBookSource('數據暫無');
            }
        } catch (err) {
            // 只有在真正失敗時才顯示連線失敗
            if (err.name === 'AbortError') {
                console.warn('五檔獲取超時');
                setOrderBookSource('連線超時');
            } else {
                console.warn('五檔獲取失敗:', err.message);
                setOrderBookSource('連線失敗');
            }
        }
    }, [price]);

    // --- 獲取成交明細 (富邦 API) ---
    const fetchTrades = useCallback(async (stockCode) => {
        if (!stockCode || stockCode.length < 4) return;
        try {
            // 添加 5 秒超時
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const res = await fetch(`${API_BASE}/api/fubon/trades/${stockCode}?count=20`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await res.json();

            if (data.success && data.trades && data.trades.length > 0) {
                // 轉換成交明細格式
                const newTrades = data.trades.map(t => ({
                    time: t.time || new Date().toLocaleTimeString('zh-TW', { hour12: false }),
                    price: t.price,
                    volume: t.volume,
                    side: t.side || (t.tick_type === 1 ? 'buy' : 'sell'),
                    isBigOrder: t.volume >= 50  // 大於 50 張視為大單
                }));
                setTickData(newTrades);
                // 注意：不再覆蓋 orderBookSource，讓五檔來源狀態獨立顯示
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.warn('成交明細獲取失敗:', err.message);
            }
        }
    }, []);

    // --- 獲取出場訊號 ---
    const fetchExitSignal = useCallback(async (stockCode) => {
        if (!stockCode || stockCode.length < 4 || entryPrice <= 0) return;
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const params = new URLSearchParams({
                position_side: positionSide,
                entry_price: entryPrice.toString(),
                bid_volume: totalBidVolume.toString(),
                ask_volume: totalAskVolume.toString(),
                current_price: price.toString()
            });

            const res = await fetch(`${API_BASE}/api/orderbook/exit-signal?symbol=${stockCode}&${params}`, {
                method: 'POST',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await res.json();
            if (data.success) {
                setExitSignal(data);
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.warn('出場訊號獲取失敗:', err.message);
            }
        }
    }, [positionSide, entryPrice, totalBidVolume, totalAskVolume, price]);

    // --- 獲取進場訊號 ---
    const fetchEntrySignal = useCallback(async (stockCode) => {
        if (!stockCode || stockCode.length < 4) return;
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const res = await fetch(`${API_BASE}/api/orderbook/entry-signal/${stockCode}`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await res.json();
            if (data.success) {
                setEntrySignal(data);
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.warn('進場訊號獲取失敗:', err.message);
            }
        }
    }, []);

    // --- 獲取止跌分析 (Buy on Dip) ---
    const fetchDipAnalysis = useCallback(async (stockCode) => {
        if (!stockCode || stockCode.length < 4) return;
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);

            const res = await fetch(`${API_BASE}/api/entry-check/quick/${stockCode}`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await res.json();
            // 修正：從 checks.dip_analysis 中提取數據
            if (data && data.checks && data.checks.dip_analysis) {
                setDipResult(data.checks.dip_analysis);
                console.log('✅ 止跌分析:', data.checks.dip_analysis);
            }
        } catch (err) {
            console.warn('⚠️ 止跌分析失敗:', err.message);
        }
    }, []);

    // 核心資料更新：五檔、成交、價格（每 1 秒）
    useEffect(() => {
        if (!symbol || symbol.length < 4) return;
        const interval = setInterval(() => {
            fetchOrderBook(symbol);
            fetchTrades(symbol);
            if (entryPrice > 0) {
                fetchExitSignal(symbol);
            }
        }, 1000);
        return () => clearInterval(interval);
    }, [symbol, fetchOrderBook, fetchTrades, fetchExitSignal, entryPrice]);

    // 分析資料更新：進場訊號、止跌分析（每 3 秒，降低負載）
    useEffect(() => {
        if (!symbol || symbol.length < 4) return;
        const interval = setInterval(() => {
            fetchEntrySignal(symbol);
            fetchDipAnalysis(symbol);
        }, 3000);
        return () => clearInterval(interval);
    }, [symbol, fetchEntrySignal, fetchDipAnalysis]);

    // --- 檢查後端連線狀態 ---
    useEffect(() => {
        const checkBackendStatus = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/big-order/status`);
                const data = await res.json();
                setBackendOnline(data.status === 'online');
            } catch {
                setBackendOnline(false);
            }
        };
        checkBackendStatus();
        // 每30秒檢查一次後端狀態
        const interval = setInterval(checkBackendStatus, 30000);
        return () => clearInterval(interval);
    }, []);

    // --- 獲取股票數據 ---
    const fetchStockData = useCallback(async (stockCode) => {
        if (!stockCode || stockCode.length < 4) return;

        setLoading(true);
        console.log('🚀 開始獲取數據:', stockCode);

        try {
            let quoteData = null;
            let quoteSource = 'unknown';

            // 同時獲取富邦和 Yahoo Finance 數據，選擇更準確的
            let fubonData = null;
            let yahooData = null;

            // 獲取富邦 API 報價
            console.log('📡 獲取富邦 API 報價...');
            try {
                const fubonRes = await fetch(`${API_BASE}/api/fubon/quote/${stockCode}`);
                fubonData = await fubonRes.json();
                if (fubonData && fubonData.price && fubonData.source === 'fubon') {
                    console.log('✅ 富邦報價:', fubonData.price);
                }
            } catch (fubonErr) {
                console.warn('⚠️ 富邦報價失敗:', fubonErr.message);
            }

            // 獲取 Yahoo Finance 報價
            console.log('📡 獲取 Yahoo Finance 報價...');
            try {
                const yahooRes = await fetch(`${API_BASE}/api/big-order/quote/${stockCode}`);
                yahooData = await yahooRes.json();
                if (yahooData && yahooData.price) {
                    console.log('✅ Yahoo 報價:', yahooData.price);
                }
            } catch (yahooErr) {
                console.warn('⚠️ Yahoo 報價失敗:', yahooErr.message);
            }

            // 選擇數據源邏輯：
            // 1. 如果兩個都有數據，優先使用 Yahoo（因為非交易時段 Yahoo 更新較準確）
            // 2. 交易時段富邦 API 會有 volume > 0，此時優先使用富邦
            if (yahooData && yahooData.price && fubonData && fubonData.price) {
                // 如果富邦有成交量（交易時段），使用富邦
                if (fubonData.volume > 0) {
                    quoteData = fubonData;
                    quoteSource = '富邦API (真實)';
                    console.log('🏦 選擇富邦 (有成交量)');
                } else {
                    // 非交易時段，使用 Yahoo（更準確的收盤價）
                    quoteData = yahooData;
                    quoteSource = yahooData.source === 'yahoo' ? 'Yahoo Finance' : yahooData.source;
                    console.log('📈 選擇 Yahoo (非交易時段)');
                }
            } else if (fubonData && fubonData.price) {
                quoteData = fubonData;
                quoteSource = '富邦API (真實)';
            } else if (yahooData && yahooData.price) {
                quoteData = yahooData;
                quoteSource = yahooData.source === 'yahoo' ? 'Yahoo Finance' :
                    yahooData.source === 'mock' ? '模擬數據' : yahooData.source;
            }

            // 如果報價成功，立即更新界面
            if (quoteData && quoteData.price) {
                setPrice(quoteData.price);
                setPrevClose(quoteData.prev_close || 0);
                setOpen(quoteData.open || 0);
                setHigh(quoteData.high || 0);
                setLow(quoteData.low || 0);
                setChange(quoteData.change || 0);
                setVolume(quoteData.volume || 0);
                setConnected(true);
                setStockName(stockCode);
                setQuoteSource(quoteSource);

                // 設定預設支撐壓力
                setSupportLevel(quoteData.low || 0);
                setResistanceLevel(quoteData.high || 0);

                // 估算 ATR
                const dailyRange = (quoteData.high || 0) - (quoteData.low || 0);
                setAtr(dailyRange * 0.8);
            }

            // 嘗試獲取更詳細的分析數據（可能較慢）
            try {
                console.log('📡 請求綜合分析 API...');
                const analysisRes = await fetch(`${API_BASE}/api/stock-analysis/comprehensive/${stockCode}`);
                const analysisData = await analysisRes.json();
                console.log('✅ 分析數據:', analysisData?.status);

                if (analysisData?.status === 'success') {
                    // API 直接返回數據，不需要 .data 嵌套
                    setStockName(analysisData.stock_name || stockCode);

                    // VWAP 數據
                    if (analysisData.volume_price_analysis) {
                        setVwap(analysisData.volume_price_analysis.vwap || 0);
                        setVwapDeviation(analysisData.volume_price_analysis.vwap_deviation || 0);
                        setVolumePriceData(analysisData.volume_price_analysis);
                    }

                    // 籌碼數據
                    if (analysisData.institutional_trading) {
                        setInstitutionalData(analysisData.institutional_trading);
                        const netFlow = (analysisData.institutional_trading.foreign_net || 0) +
                            (analysisData.institutional_trading.trust_net || 0) +
                            (analysisData.institutional_trading.dealer_net || 0);
                        setBigMoneyFlow(netFlow);
                    }
                }
            } catch (analysisErr) {
                console.warn('⚠️ 綜合分析 API 失敗:', analysisErr.message);
            }

            // 嘗試獲取支撐壓力位
            try {
                console.log('📡 請求支撐壓力 API...');
                const srRes = await fetch(`${API_BASE}/api/smart-entry/support-resistance/${stockCode}`);
                const srData = await srRes.json();
                console.log('✅ 支撐壓力數據:', srData?.success);

                if (srData?.success && srData?.levels) {
                    const supports = srData.levels.filter(l => l.type === 'support');
                    const resistances = srData.levels.filter(l => l.type === 'resistance');

                    if (supports.length > 0) setSupportLevel(supports[0].price);
                    if (resistances.length > 0) setResistanceLevel(resistances[0].price);
                }
            } catch (srErr) {
                console.warn('⚠️ 支撐壓力 API 失敗:', srErr.message);
            }

            console.log('✅ 數據獲取完成');

        } catch (err) {
            console.error('❌ 獲取數據失敗:', err);
            setConnected(false);
        } finally {
            setLoading(false);
        }
    }, []);

    // 搜尋觸發
    useEffect(() => {
        const timer = setTimeout(() => {
            if (symbol.length >= 4) {
                console.log('🔍 觸發搜尋:', symbol);
                fetchStockData(symbol);
            }
        }, 500);
        return () => clearTimeout(timer);
    }, [symbol, fetchStockData]);

    // 即時更新（每2秒）- 只有在監控中才更新
    useEffect(() => {
        if (!symbol || symbol.length < 4 || !isMonitoring) return;
        const interval = setInterval(() => fetchStockData(symbol), 2000);
        intervalRefs.current.push(interval);
        return () => clearInterval(interval);
    }, [symbol, fetchStockData, isMonitoring]);

    // --- 開始監控 ---
    const startMonitoring = () => {
        if (!inputSymbol || inputSymbol.length < 4) {
            alert('請輸入 4 位數股票代碼');
            return;
        }
        // 重置所有數據
        resetAllData();
        // 開始監控
        setSymbol(inputSymbol);
        setIsMonitoring(true);
        setMonitorStartTime(new Date());
        console.log('🚀 開始監控:', inputSymbol);
    };

    // --- 停止監控 ---
    const stopMonitoring = () => {
        setIsMonitoring(false);
        // 清除所有 interval
        intervalRefs.current.forEach(interval => clearInterval(interval));
        intervalRefs.current = [];
        console.log('🛑 停止監控');
    };

    // --- 重置所有數據 ---
    const resetAllData = () => {
        setPrice(0);
        setPrevClose(0);
        setOpen(0);
        setHigh(0);
        setLow(0);
        setChange(0);
        setVolume(0);
        setVwap(0);
        setVwapDeviation(0);
        setVolumePriceData(null);
        setInstitutionalData(null);
        setBigMoneyFlow(0);
        setSupportLevel(0);
        setResistanceLevel(0);
        setAtr(0);
        setOrderBook({ bids: [], asks: [] });
        setTotalBidVolume(0);
        setTotalAskVolume(0);
        setTickData([]);
        setStockName('');
        setConnected(false);
    };

    // --- 發送進出場信號通知 ---
    const sendSignalNotification = async (signalType, strategy, reason) => {
        if (!symbol || price === 0) {
            alert('請先監控股票');
            return;
        }

        try {
            const params = new URLSearchParams({
                symbol: symbol,
                stock_name: stockName || symbol,
                signal_type: signalType,  // ENTRY 或 EXIT
                price: price.toFixed(2),
                vwap: vwap.toFixed(2),
                reason: reason,
                strategy: strategy,
                stop_loss: signalType === 'ENTRY' ? (price - atr * 1.5).toFixed(2) : 0,
                take_profit: signalType === 'ENTRY' ? resistanceLevel.toFixed(2) : 0
            });

            const res = await fetch(`${API_BASE}/api/day-trading/signal?${params}`, {
                method: 'POST'
            });
            const data = await res.json();

            if (data.success) {
                alert(`✅ 已發送${signalType === 'ENTRY' ? '進場' : '出場'}信號通知！\n收件人: ${data.recipients?.join(', ')}`);
            } else {
                alert(`⚠️ ${data.message}`);
            }
        } catch (err) {
            alert(`❌ 發送失敗: ${err.message}`);
        }
    };

    // --- 計算邏輯 ---
    const isBelowVwap = vwap > 0 && price < vwap;
    const isAboveVwap = vwap > 0 && price > vwap;

    // 決策演算法
    const getDecision = () => {
        // 🔒 核心數據有效性檢查 - 防止誤判
        // 檢查所有關鍵數據是否有效（非 0、非 null、非 undefined）
        if (!price || price === 0 ||
            !vwap || vwap === 0 ||
            !supportLevel || supportLevel === 0 ||
            !resistanceLevel || resistanceLevel === 0) {
            return {
                action: "⏳ 等待市場數據...",
                color: "text-gray-500",
                bg: "bg-gray-100",
                confidence: 0
            };
        }

        // 接近支撐且大戶在買
        if (price <= supportLevel * 1.005 && bigMoneyFlow > 5) {
            return { action: "準備進場 (試單)", color: "text-amber-700", bg: "bg-yellow-50", confidence: 60 };
        }

        // 接近支撐但大戶還在賣
        if (price <= supportLevel * 1.005 && bigMoneyFlow <= 0) {
            return { action: "支撐測試中 (勿接刀)", color: "text-red-600", bg: "bg-red-50", confidence: 20 };
        }

        // 在區間內，低於 VWAP
        if (price > supportLevel && price < resistanceLevel && isBelowVwap) {
            return { action: "空方反彈 (偏空操作)", color: "text-green-600", bg: "bg-green-50", confidence: 75 };
        }

        // 在區間內，高於 VWAP
        if (price > supportLevel && price < resistanceLevel && isAboveVwap) {
            return { action: "多方回測 (偏多操作)", color: "text-red-600", bg: "bg-red-50", confidence: 70 };
        }

        // 突破壓力位
        if (price > resistanceLevel && isAboveVwap) {
            return { action: "突破做多 (追漲)", color: "text-red-700", bg: "bg-red-900/40", confidence: 80 };
        }

        // 跌破支撐位
        if (price < supportLevel && isBelowVwap) {
            return { action: "跌破做空 (追跌)", color: "text-green-700", bg: "bg-green-900/40", confidence: 80 };
        }

        return { action: "觀望 (等待出量)", color: "text-gray-700", bg: "bg-gray-800", confidence: 0 };
    };

    const decision = getDecision();

    // 動態停損計算
    const stopLossShort = price > 0 && atr > 0 ? (price + atr * 1.5).toFixed(1) : '--';
    const stopLossLong = price > 0 && atr > 0 ? (price - atr * 1.5).toFixed(1) : '--';
    const targetShort = supportLevel > 0 ? supportLevel.toFixed(1) : '--';
    const targetLong = resistanceLevel > 0 ? resistanceLevel.toFixed(1) : '--';

    // 風險報酬比（做空）
    const riskRewardRatioShort = price > 0 && supportLevel > 0 && atr > 0
        ? Math.abs((price - supportLevel) / (atr * 1.5)).toFixed(2)
        : 0;

    // 風險報酬比（做多）
    const riskRewardRatioLong = price > 0 && resistanceLevel > 0 && atr > 0
        ? Math.abs((resistanceLevel - price) / (atr * 1.5)).toFixed(2)
        : 0;

    // 買賣力道視覺化
    const buyPressure = volumePriceData
        ? (volumePriceData.confirmation_signal === 'bullish_confirmation' ? 70 :
            volumePriceData.confirmation_signal === 'bearish_confirmation' ? 30 : 50)
        : 50;

    return (
        <div className="bg-gradient-to-br from-slate-50 to-blue-50 text-gray-800 p-4 min-h-screen font-sans">

            {/* 頂部導航欄 */}
            <div className="flex bg-white/80 backdrop-blur-md sticky top-0 z-50 px-4 py-2 border-b border-slate-200 justify-between items-center gap-4 mb-4 rounded-xl shadow-sm">
                <div className="flex items-center gap-4">
                    <h1 className="text-xl font-black flex items-center gap-2 tracking-tighter">
                        <Crosshair className="text-red-600" size={20} />
                        <span className="hidden sm:inline">當沖狙擊手 <span className="text-red-600">Pro</span></span>
                        <span className="text-[10px] bg-red-600 px-1.5 py-0.5 rounded text-white font-black">LIVE</span>
                    </h1>
                    <div className="flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 focus-within:ring-2 focus-within:ring-red-500/20 transition-all">
                        <Search size={14} className="text-slate-400" />
                        <input
                            type="text"
                            value={inputSymbol}
                            onChange={(e) => setInputSymbol(e.target.value.toUpperCase())}
                            onKeyDown={(e) => e.key === 'Enter' && startMonitoring()}
                            className="w-20 bg-transparent text-sm font-mono font-bold text-slate-700 focus:outline-none uppercase"
                            placeholder="代碼"
                        />
                        <button
                            onClick={isMonitoring ? stopMonitoring : startMonitoring}
                            className={`px-3 py-1 rounded-md text-[10px] font-black transition-all ${isMonitoring ? 'bg-red-100 text-red-600 hover:bg-red-200' : 'bg-red-600 text-white hover:bg-red-700'}`}
                        >
                            {isMonitoring ? '停止' : '監控'}
                        </button>
                    </div>
                </div>

                {symbol && (
                    <div className="flex-1 max-w-2xl px-4 border-x border-slate-100">
                        <MarketDecision symbol={symbol} API_BASE={API_BASE} variant="compact" />
                    </div>
                )}

                <div className="flex items-center gap-6">
                    {symbol && (
                        <div className="flex flex-col items-end">
                            <div className="text-[10px] text-slate-400 font-black tracking-widest uppercase mb-1">{stockName || symbol}</div>
                            <div className="flex items-center gap-2">
                                <span className={`text-2xl font-mono font-black tracking-tighter ${change > 0 ? 'text-rose-600' : change < 0 ? 'text-emerald-600' : 'text-slate-500'}`}>
                                    {price.toFixed(2)}
                                </span>
                                <span className={`text-xs font-bold ${change > 0 ? 'text-rose-600' : change < 0 ? 'text-emerald-600' : 'text-slate-500'}`}>
                                    {change > 0 ? '▲' : change < 0 ? '▼' : '－'}{Math.abs(change).toFixed(2)}%
                                </span>
                            </div>
                        </div>
                    )}
                    <button onClick={() => setShowGuide(!showGuide)} className="text-slate-400 hover:text-slate-600">
                        <HelpCircle size={18} />
                    </button>
                </div>
            </div>

            {/* Landing Page or Main Content */}
            {!symbol ? (
                <div className="flex flex-col items-center justify-center min-h-[70vh] text-center">
                    <div className="w-24 h-24 bg-red-50 rounded-full flex items-center justify-center mb-8 border border-red-100 shadow-inner">
                        <Crosshair className="text-red-600 animate-pulse" size={48} />
                    </div>
                    <h2 className="text-4xl font-black text-slate-900 mb-4 tracking-tighter">當沖分時狙擊系統 <span className="text-red-600 text-lg align-top ml-1">Pro</span></h2>
                    <p className="text-slate-500 text-lg mb-8 max-w-md font-medium leading-relaxed">
                        實時連線富邦五檔報價與 VWAP 智慧演算法，<br />
                        鎖定強勢股突破與弱勢股跌破時機。
                    </p>
                    <div className="flex flex-col items-center gap-6">
                        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.3em]">熱門監測標的</div>
                        <div className="flex gap-3">
                            {['3037', '2330', '2317', '2454', '2603'].map(s => (
                                <button
                                    key={s}
                                    onClick={() => { setInputSymbol(s); setSymbol(s); setIsMonitoring(true); fetchStockData(s); }}
                                    className="px-6 py-3 bg-white border border-slate-200 rounded-2xl text-sm font-black text-slate-600 hover:border-red-500/50 hover:text-red-600 transition-all shadow-sm hover:shadow-md"
                                >
                                    {s} {s === '3037' ? '欣興' : s === '2330' ? '台積電' : ''}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    {/* 操作說明面板 */}
                    {showGuide && (
                        <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 relative shadow-sm">
                            <button
                                onClick={() => setShowGuide(false)}
                                className="absolute top-3 right-3 text-slate-400 hover:text-slate-600"
                            >
                                <X size={18} />
                            </button>

                            <h3 className="text-lg font-bold text-blue-600 mb-4 flex items-center gap-2">
                                <HelpCircle size={20} /> 操作說明
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                                {/* 操作步驟 */}
                                <div className="space-y-3">
                                    <h4 className="font-bold text-gray-800 border-b border-blue-200 pb-1">📋 操作步驟</h4>
                                    <div className="space-y-2 text-gray-700">
                                        <div className="flex gap-2">
                                            <span className="bg-blue-600 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0">1</span>
                                            <span>輸入 <strong className="text-blue-600">股票代碼</strong> 並點擊 <strong className="text-red-600">監控</strong></span>
                                        </div>
                                        <div className="flex gap-2">
                                            <span className="bg-blue-600 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0">2</span>
                                            <span>等待數據載入，查看 <strong className="text-amber-700">AI 判讀</strong> 核心建議</span>
                                        </div>
                                        <div className="flex gap-2">
                                            <span className="bg-blue-600 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0">3</span>
                                            <span>結合 <strong className="text-indigo-600">聯決策矩陣</strong> 判斷市場多空基調</span>
                                        </div>
                                    </div>
                                </div>

                                {/* VWAP 規則 */}
                                <div className="space-y-3">
                                    <h4 className="font-bold text-gray-800 border-b border-blue-200 pb-1">📐 VWAP 交易規則</h4>
                                    <div className="space-y-2 text-gray-700">
                                        <div className="flex items-start gap-2">
                                            <span className="text-red-600">📈</span>
                                            <span>價格 <strong className="text-red-600">&gt; VWAP</strong> → 偏多，線上不空</span>
                                        </div>
                                        <div className="flex items-start gap-2">
                                            <span className="text-green-600">📉</span>
                                            <span>價格 <strong className="text-green-600">&lt; VWAP</strong> → 偏空，線下不多</span>
                                        </div>
                                    </div>
                                </div>

                                {/* 訊號說明 */}
                                <div className="space-y-3">
                                    <h4 className="font-bold text-gray-800 border-b border-blue-200 pb-1">🎯 訊號核心</h4>
                                    <div className="text-xs text-gray-500 leading-relaxed italic">
                                        系統綜合「成交密集區」、「五檔壓力撐托」與「技術面共振」自動給出進出場點。
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 🆕 全域市場動態區 */}
                    <div className="mb-4">
                        <MarketDecision symbol={symbol} API_BASE={API_BASE} variant="full" />
                    </div>

                    <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
                        {/* Column 1: AI Analysis & Strategy (XL:3) */}
                        <div className="xl:col-span-3 space-y-4">
                            {/* Primary Signal Card - Premium Intelligence View */}
                            <div className={`p-5 rounded-2xl border ${decision.action.includes("空") ? 'border-emerald-500/30 bg-emerald-50/10' : decision.action.includes("多") ? 'border-rose-500/30 bg-rose-50/10' : 'border-slate-200 bg-white'} shadow-xl relative overflow-hidden`}>
                                <div className="absolute -top-10 -right-10 opacity-[0.03]">
                                    <Target size={200} />
                                </div>

                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h2 className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">AI 智慧核心分析系統</h2>
                                        <div className={`text-3xl font-black tracking-tighter ${decision.color}`}>
                                            {decision.action || '掃描中...'}
                                        </div>
                                    </div>
                                    {dipResult && dipResult.score >= 50 && (
                                        <div className="bg-blue-600 text-white text-[9px] font-black px-2 py-1 rounded-full animate-pulse">
                                            底部止跌確認
                                        </div>
                                    )}
                                </div>

                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="bg-white/60 backdrop-blur-sm p-3 rounded-xl border border-slate-100">
                                            <div className="text-[9px] text-slate-400 font-bold uppercase mb-1">預測信心度</div>
                                            <div className="text-lg font-black text-slate-700">{decision.confidence}%</div>
                                            <div className="w-full bg-slate-100 h-1 rounded-full mt-1 overflow-hidden">
                                                <div className="h-full bg-blue-500" style={{ width: `${decision.confidence}%` }}></div>
                                            </div>
                                        </div>
                                        <div className="bg-white/60 backdrop-blur-sm p-3 rounded-xl border border-slate-100">
                                            <div className="text-[9px] text-slate-400 font-bold uppercase mb-1">趨勢環境濾網</div>
                                            <div className={`text-lg font-black ${isBelowVwap ? 'text-emerald-600' : 'text-rose-600'}`}>
                                                {isBelowVwap ? '空方環境' : '多方環境'}
                                            </div>
                                            <div className="text-[9px] text-slate-400 font-mono">VWAP @ {vwap.toFixed(1)}</div>
                                        </div>
                                    </div>

                                    {/* Signal Intel List */}
                                    <div className="bg-slate-900/5 rounded-xl p-3 space-y-2 border border-slate-200/50">
                                        <div className="flex justify-between items-center text-[11px]">
                                            <span className="text-slate-500 font-bold">三大法人實時買賣超 (張)</span>
                                            <span className={`font-black ${bigMoneyFlow > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                                {bigMoneyFlow > 0 ? '買超' : '賣超'} {bigMoneyFlow !== undefined ? `${Math.abs(bigMoneyFlow).toLocaleString()} 張` : '0'}
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center text-[11px]">
                                            <span className="text-slate-500 font-bold">量價過濾分析</span>
                                            <span className="text-slate-700 font-black truncate max-w-[120px]">
                                                {volumePriceData?.volume_price_confirmation || '等待數據擷取中...'}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Signal Trigger Buttons */}
                                <div className="mt-5 pt-5 border-t border-slate-100 grid grid-cols-2 gap-2">
                                    <button
                                        onClick={() => sendSignalNotification('ENTRY', isBelowVwap ? '發送做空' : '發送做多', `於 $${price.toFixed(1)} 偵測到訊號`)}
                                        className={`py-2.5 rounded-xl font-black text-[11px] uppercase tracking-wider transition-all shadow-lg active:scale-95 ${isBelowVwap ? 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-200/50' : 'bg-rose-600 hover:bg-rose-700 shadow-rose-200/50'} text-white`}
                                    >
                                        發送進場訊號
                                    </button>
                                    <button
                                        onClick={() => sendSignalNotification('EXIT', '發送出場', `於 $${price.toFixed(1)} 觸發出場訊號`)}
                                        className="bg-slate-800 hover:bg-slate-900 text-white py-2.5 rounded-xl font-black text-[11px] uppercase tracking-wider transition-all shadow-lg shadow-slate-200/50 active:scale-95"
                                    >
                                        發送出場訊號
                                    </button>
                                </div>
                            </div>

                            {/* Strategic Roadmap - Data Dense */}
                            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                                <h3 className="flex items-center gap-2 text-slate-400 text-[10px] font-black mb-4 uppercase tracking-widest">
                                    <BookOpen size={14} className="text-blue-500" /> AI 戰術執行導航板
                                </h3>
                                <div className="space-y-4">
                                    <div className="relative pl-4 border-l-2 border-slate-100 group hover:border-blue-500 transition-colors">
                                        <span className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-slate-300 group-hover:bg-blue-500"></span>
                                        <div className="text-[11px] font-black text-slate-700 mb-1">主要交易劇本 (回測/修正)</div>
                                        <p className="text-[11px] text-slate-500 leading-relaxed">
                                            {isBelowVwap
                                                ? `等待價格反彈至 VWAP 區域 ($${(vwap * 0.995).toFixed(1)} ~ $${vwap.toFixed(1)})，若遇壓無法突破則執行「做空」。`
                                                : `等待價格拉回至 VWAP 區域 ($${vwap.toFixed(1)} ~ $${(vwap * 1.005).toFixed(1)})，若獲得守穩支撐則執行「做多」。`}
                                        </p>
                                    </div>
                                    <div className="relative pl-4 border-l-2 border-slate-100 group hover:border-amber-500 transition-colors">
                                        <span className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-slate-300 group-hover:bg-amber-500"></span>
                                        <div className="text-[11px] font-black text-slate-700 mb-1">進階交易劇本 (強勢突破/跌破)</div>
                                        <p className="text-[11px] text-slate-500 leading-relaxed">
                                            {isBelowVwap
                                                ? `若價格帶量跌破強支撐 $${supportLevel.toFixed(1)}，可考慮積極「追空」操作。`
                                                : `若價格強勢帶量突破壓力 $${resistanceLevel.toFixed(1)}，可考慮積極「追多」操作。`}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Execution Alert */}
                            <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex gap-3 items-start">
                                <AlertTriangle className="text-amber-500 shrink-0" size={18} />
                                <div>
                                    <div className="text-[11px] font-black text-amber-900 mb-1">交易執行警戒區</div>
                                    <p className="text-[10px] text-amber-700 font-medium">
                                        進場前請務必確認第二欄的即時掛單動能。切勿僅依賴 AI 而忽略實際價格走勢。
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Column 2: THE HEAT - Live Action (XL:6) */}
                        <div className="xl:col-span-6 space-y-4">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                {/* Order Book Side */}
                                <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm h-fit">
                                    <h3 className="flex items-center gap-2 text-slate-700 text-[10px] font-black mb-3 uppercase tracking-widest border-b border-slate-50 pb-2">
                                        <Layers size={14} className="text-blue-600" /> 即時五檔戰情
                                        <span className="ml-auto text-[10px] font-bold text-slate-400">{orderBookSource}</span>
                                    </h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        {/* 賣盤 */}
                                        <div className="space-y-1">
                                            {orderBook.asks.slice(0, 5).reverse().map((ask, i) => (
                                                <div key={`ask-${i}`} className="flex items-center gap-2 text-[11px]">
                                                    <span className="w-6 text-slate-400">S{5 - i}</span>
                                                    <span className="w-12 font-mono font-black text-emerald-600 text-right">{ask.price?.toFixed(1)}</span>
                                                    <div className="flex-1 bg-slate-50 h-5 rounded relative overflow-hidden">
                                                        <div className="absolute right-0 h-full bg-emerald-100" style={{ width: `${Math.min((ask.volume / 500) * 100, 100)}%` }}></div>
                                                        <span className="absolute right-1 z-10 font-mono font-bold text-[10px] text-emerald-800 leading-5">{ask.volume}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        {/* 買盤 */}
                                        <div className="space-y-1">
                                            {orderBook.bids.slice(0, 5).map((bid, i) => (
                                                <div key={`bid-${i}`} className="flex items-center gap-2 text-[11px]">
                                                    <span className="w-6 text-slate-400">B{i + 1}</span>
                                                    <span className="w-12 font-mono font-black text-rose-600 text-right">{bid.price?.toFixed(1)}</span>
                                                    <div className="flex-1 bg-slate-50 h-5 rounded relative overflow-hidden">
                                                        <div className="absolute left-0 h-full bg-rose-100" style={{ width: `${Math.min((bid.volume / 500) * 100, 100)}%` }}></div>
                                                        <span className="absolute left-1 z-10 font-mono font-bold text-[10px] text-rose-800 leading-5">{bid.volume}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Recent Trades Side */}
                                <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm flex flex-col h-[280px]">
                                    <h3 className="flex items-center gap-2 text-slate-700 text-[10px] font-black mb-3 uppercase tracking-widest border-b border-slate-50 pb-2">
                                        <Activity size={14} className="text-orange-500" /> 盤中逐筆成交流水
                                    </h3>
                                    <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                                        {tickData.length === 0 ? (
                                            <div className="flex items-center justify-center h-full text-[11px] text-slate-400 italic">等待最新成交資料擷取中...</div>
                                        ) : (
                                            tickData.map((tick, i) => (
                                                <div key={`tick-${i}`} className={`flex items-center justify-between text-[10px] px-2 py-1 rounded ${tick.side === 'buy' ? 'bg-rose-50' : 'bg-emerald-50'} ${tick.isBigOrder ? 'ring-1 ring-amber-400 font-bold bg-amber-50' : ''}`}>
                                                    <span className="font-mono text-slate-400 w-12">{tick.time}</span>
                                                    <span className={`font-black w-10 ${tick.side === 'buy' ? 'text-rose-600' : 'text-emerald-600'}`}>{tick.price?.toFixed(1)}</span>
                                                    <span className="font-mono w-8 text-right">{tick.volume}</span>
                                                    <span className={`text-[8px] font-black px-1 rounded ${tick.side === 'buy' ? 'text-rose-500' : 'text-emerald-500'}`}>{tick.side === 'buy' ? '外' : '內'}</span>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Entry/Exit Analysis Summary Panels */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 flex justify-between">
                                        進場訊號解析 {entrySignal && <span className="text-emerald-600">{entrySignal.score}分</span>}
                                    </h4>
                                    <div className="text-[11px] font-bold text-slate-700 leading-snug min-h-[40px]">
                                        {entrySignal ? entrySignal.signal_text : '等待數據收集中...'}
                                    </div>
                                </div>
                                <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 flex justify-between">
                                        出場/風控監控 {exitSignal && <span className="text-rose-600">{exitSignal.urgency_text}</span>}
                                    </h4>
                                    <div className="text-[11px] font-bold text-slate-700 leading-snug min-h-[40px]">
                                        {exitSignal ? exitSignal.reason : '未持倉或訊號正常。'}
                                    </div>
                                </div>
                            </div>
                        </div>
                        {/* Column 3: Risk & Flow (XL:3) */}
                        <div className="xl:col-span-3 space-y-4 text-gray-800">
                            {/* 🛡️ 動態風控面板 - Premium Dark Style */}
                            <div className="bg-slate-900 text-white p-5 rounded-2xl shadow-2xl border border-slate-800 relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-4 opacity-5">
                                    <Shield size={120} />
                                </div>
                                <h3 className="flex items-center gap-2 text-slate-400 text-[10px] font-black mb-6 uppercase tracking-widest">
                                    <Shield size={14} className="text-blue-500" /> 全自動交易風險管控系統
                                </h3>
                                <div className="space-y-5 relative z-10">
                                    <div className="flex justify-between items-center bg-white/5 p-3 rounded-xl border border-white/5">
                                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">動態停損位</span>
                                        <span className="text-2xl font-black text-rose-500 font-mono tracking-tighter">
                                            ${isBelowVwap ? stopLossShort : stopLossLong}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center bg-white/5 p-3 rounded-xl border border-white/5">
                                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">預定停利點</span>
                                        <span className="text-2xl font-black text-emerald-500 font-mono tracking-tighter">
                                            ${isBelowVwap ? targetShort : targetLong}
                                        </span>
                                    </div>
                                    <div className="pt-2 border-t border-white/10">
                                        <div className="flex justify-between items-center mb-1">
                                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">盈虧風報比</span>
                                            <span className="text-base font-black text-blue-400">1 : {isBelowVwap ? riskRewardRatioShort : riskRewardRatioLong}</span>
                                        </div>
                                        <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500 transition-all duration-1000" style={{ width: `${Math.min(Number(isBelowVwap ? riskRewardRatioShort : riskRewardRatioLong) * 20, 100)}%` }}></div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* 買賣力道 Bar */}
                            <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">盤中即時買賣力道</h4>
                                <div className="flex items-center gap-3">
                                    <span className="text-[11px] font-black text-rose-600">{buyPressure}%</span>
                                    <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
                                        <div className="h-full bg-rose-500 transition-all duration-500" style={{ width: `${buyPressure}%` }}></div>
                                        <div className="h-full bg-emerald-500 transition-all duration-500" style={{ width: `${100 - buyPressure}%` }}></div>
                                    </div>
                                    <span className="text-[11px] font-black text-emerald-600">{100 - buyPressure}%</span>
                                </div>
                                <div className="flex justify-between mt-2 text-[9px] font-bold text-slate-400 uppercase tracking-tighter">
                                    <span>買盤(內盤) / 賣壓</span>
                                    <span>賣盤(外盤) / 承接</span>
                                </div>
                            </div>

                            {/* 法人動態 */}
                            <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
                                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4 border-b border-slate-50 pb-2">法人機構籌碼指標</h4>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-center">
                                        <span className="text-[11px] text-slate-500 font-bold">外資買賣</span>
                                        <span className={`text-[11px] font-black ${institutionalData?.foreign_net > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                            {institutionalData?.foreign_net !== undefined ? `${institutionalData.foreign_net.toLocaleString()} 張` : '讀取中...'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[11px] text-slate-500 font-bold">投信買賣</span>
                                        <span className={`text-[11px] font-black ${institutionalData?.trust_net > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                            {institutionalData?.trust_net !== undefined ? `${institutionalData.trust_net.toLocaleString()} 張` : '讀取中...'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[11px] text-slate-500 font-bold">自營商買賣</span>
                                        <span className={`text-[11px] font-black ${institutionalData?.dealer_net > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                            {institutionalData?.dealer_net !== undefined ? `${institutionalData.dealer_net.toLocaleString()} 張` : '讀取中...'}
                                        </span>
                                    </div>
                                    <div className="pt-2 border-t border-slate-100 flex justify-between items-center">
                                        <span className="text-[10px] font-black text-slate-400 uppercase">三大法人合計</span>
                                        <span className={`text-[12px] font-black ${bigMoneyFlow > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                            {bigMoneyFlow !== undefined ? `${bigMoneyFlow.toLocaleString()} 張` : '0'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 底部提示 - 數據來源總覽 */}
                    <div className="mt-6 bg-slate-900/5 backdrop-blur-sm rounded-xl p-4 border border-slate-200/50">
                        <div className="flex flex-wrap justify-center gap-6 text-[10px] font-bold tracking-wider uppercase text-slate-400">
                            <span className="flex items-center gap-2">
                                <Activity size={12} /> 系統時間: <span className="text-slate-600 font-mono">{new Date().toLocaleTimeString()}</span>
                            </span>
                            <span className="flex items-center gap-2">
                                <Zap size={12} className={isMonitoring ? 'text-amber-500' : 'text-slate-300'} />
                                連線狀態: <span className={isMonitoring ? 'text-emerald-600' : 'text-slate-400'}>{isMonitoring ? '即時監控開啟' : '待機掛線中'}</span>
                            </span>
                            <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-100">
                                行情來源: {quoteSource}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-100">
                                五檔掛單來源: {orderBookSource}
                            </span>
                        </div>
                        <div className="text-center text-[9px] text-slate-400 mt-3 font-medium">
                            ⚠️ AI 數據僅供參考。綠色標籤: 真實數據 | 黃色標籤: 推算數據 | 藍色標籤: Yahoo Finance
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default DayTradePro;
