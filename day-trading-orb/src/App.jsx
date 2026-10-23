import React, { useState, useEffect, useCallback } from 'react';
import { Target, TrendingUp, TrendingDown, Layers, BarChart2, Zap, AlertTriangle, CheckCircle, Activity, Calculator, Search, RefreshCw, Loader2, Wifi, WifiOff, HelpCircle, X, Eye, Bell, Plus, Trash2, Play, Crosshair, ToggleLeft, ToggleRight } from 'lucide-react';
import DayTradePro from './DayTradePro.jsx';
import ExpertSniper from './ExpertSniper.jsx';
import StrategySummary from './components/StrategySummary.jsx';

const API_BASE = 'http://localhost:8000';

// 主應用包裝器 - 支援頁面切換
const App = () => {
  const [currentView, setCurrentView] = useState('expert'); // 'classic', 'pro', 或 'expert'

  return (
    <div className="relative">
      {/* 頁面切換按鈕 - 移到左上角避免遮蓋 */}
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 bg-slate-800/90 px-3 py-2 rounded-lg shadow-lg border border-slate-600 backdrop-blur-sm transition-opacity opacity-70 hover:opacity-100">
        <span className="text-xs text-slate-400 mr-1">模式:</span>
        <button
          onClick={() => setCurrentView('classic')}
          className={`px-3 py-1 rounded text-sm font-medium transition-all ${currentView === 'classic'
            ? 'bg-blue-600 text-white'
            : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
        >
          經典版
        </button>
        <button
          onClick={() => setCurrentView('pro')}
          className={`px-3 py-1 rounded text-sm font-medium transition-all flex items-center gap-1 ${currentView === 'pro'
            ? 'bg-gradient-to-r from-red-600 to-orange-600 text-white'
            : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
        >
          <Crosshair size={14} />
          狙擊手 Pro
        </button>
        <button
          onClick={() => setCurrentView('expert')}
          className={`px-3 py-1 rounded text-sm font-medium transition-all flex items-center gap-1 ${currentView === 'expert'
            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
            : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
        >
          <Zap size={14} />
          專家版
        </button>
      </div>

      {/* 根據選擇顯示不同頁面 */}
      {currentView === 'expert' ? <ExpertSniper /> : currentView === 'pro' ? <DayTradePro /> : <DayTradingWarRoom />}
    </div>
  );
};


const DayTradingWarRoom = () => {
  // --- 狀態管理 ---
  const [symbol, setSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiData, setApiData] = useState(null);
  const [bollingerData, setBollingerData] = useState(null);
  const [fubonQuote, setFubonQuote] = useState(null);
  const [fubonConnected, setFubonConnected] = useState(false);
  const [showGuide, setShowGuide] = useState(true);

  // 觀察清單
  const [watchlist, setWatchlist] = useState([]);
  const [showWatchlist, setShowWatchlist] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [lastScanTime, setLastScanTime] = useState(null);

  // 1. 市場基礎數據
  const [marketData, setMarketData] = useState({
    prevHigh: 0,
    prevLow: 0,
    prevClose: 0,
    open: 0,
    current: 0,
  });

  // 2. ORB (開盤區間) 設定
  const [orbData, setOrbData] = useState({
    high: 0,
    low: 0,
    timeframe: '5min',
  });

  // 3. 五分鐘量能分析
  const [volumeAnalysis, setVolumeAnalysis] = useState({
    buyVol: 500,
    sellVol: 300,
    status: 'neutral',
  });

  // 4. 九宮格撐壓點位列表
  const [levels, setLevels] = useState([]);
  const [newLevelPrice, setNewLevelPrice] = useState('');
  const [newLevelType, setNewLevelType] = useState('resistance');

  // 九大判斷條件
  const nineMethods = [
    { id: 'prev_hl', label: '1. 前高/前低' },
    { id: 'key_price', label: '2. 關鍵價/整數關卡' },
    { id: 'ma', label: '3. 移動平均線(MA)' },
    { id: 'trend_ch', label: '4. 趨勢線/通道線' },
    { id: 'pattern', label: '5. 型態滿足點' },
    { id: 'fib', label: '6. 斐波那契' },
    { id: 'gap', label: '7. 跳空缺口' },
    { id: 'volume_area', label: '8. 大量成交區' },
    { id: 'bollinger', label: '9. 布林通道' },
  ];

  const [selectedMethods, setSelectedMethods] = useState([]);


  // --- 檢查富邦連線狀態 ---
  useEffect(() => {
    const checkFubonStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/big-order/status`);
        const data = await res.json();
        setFubonConnected(data.fubon_connected || false);
      } catch {
        setFubonConnected(false);
      }
    };
    checkFubonStatus();
    const interval = setInterval(checkFubonStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // --- API 整合 ---
  const fetchStockData = useCallback(async (stockCode) => {
    if (!stockCode || stockCode.length < 4) return;

    setLoading(true);
    setError(null);
    setShowGuide(false);

    try {
      // 同時獲取所有 API 數據（包含九宮格撐壓分析）
      const [scoreRes, bollingerRes, fubonRes, srRes] = await Promise.all([
        fetch(`${API_BASE}/api/smart-entry/score/${stockCode}`),
        fetch(`${API_BASE}/api/smart-entry/bollinger/${stockCode}`),
        fetch(`${API_BASE}/api/big-order/quote/${stockCode}`),
        fetch(`${API_BASE}/api/smart-entry/support-resistance/${stockCode}`)
      ]);

      const scoreData = await scoreRes.json();
      const bollingerResult = await bollingerRes.json();
      const fubonData = await fubonRes.json();
      const srData = await srRes.json();

      if (scoreData.success) {
        setApiData(scoreData);
        if (scoreData.prev_high && scoreData.prev_low) {
          setMarketData(prev => ({
            ...prev,
            prevHigh: scoreData.prev_high,
            prevLow: scoreData.prev_low,
            prevClose: scoreData.prev_close || 0,
          }));
        }
      }

      if (fubonData && fubonData.price) {
        setFubonQuote(fubonData);
        setMarketData(prev => ({
          ...prev,
          current: fubonData.price,
          open: fubonData.open || prev.open,
        }));
        setOrbData(prev => ({
          ...prev,
          high: fubonData.high || prev.high,
          low: fubonData.low || prev.low,
        }));
        const changePct = fubonData.change || 0;
        setVolumeAnalysis({
          buyVol: changePct > 0 ? 550 + changePct * 80 : 400,
          sellVol: changePct < 0 ? 550 + Math.abs(changePct) * 80 : 400,
          status: changePct > 1 ? 'accumulation' : changePct < -1 ? 'distribution' : 'neutral'
        });
      } else {
        const orb = scoreData?.factors?.orb;
        if (orb) {
          setOrbData(prev => ({ ...prev, high: orb.range_high || 0, low: orb.range_low || 0 }));
          setMarketData(prev => ({ ...prev, current: orb.current || scoreData.current_price || 0 }));
        }
        setError('無法取得富邦即時報價，使用延遲數據');
      }

      // 載入九宮格撐壓自動分析結果
      if (srData.success && srData.levels) {
        const autoLevels = srData.levels.map((level, idx) => ({
          id: Date.now() + idx,
          price: level.price,
          type: level.type,
          conditions: level.conditions,
          score: level.score,
          resonance: level.resonance,
          labels: level.labels,
          auto: true,
        }));
        setLevels(autoLevels);
      } else if (bollingerResult.success) {
        // 回退使用布林通道
        setBollingerData(bollingerResult);
        const bb = bollingerResult.bollinger;
        if (bb) {
          setLevels([
            { id: Date.now(), price: bb.upper, type: 'resistance', conditions: ['bollinger'], score: 1, auto: true },
            { id: Date.now() + 1, price: bb.lower, type: 'support', conditions: ['bollinger'], score: 1, auto: true }
          ].sort((a, b) => b.price - a.price));
        }
      }

      if (bollingerResult.success) {
        setBollingerData(bollingerResult);
      }
    } catch (err) {
      setError('API 連線失敗: ' + err.message);
    } finally {
      setLoading(false);

    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (symbol.length >= 4) fetchStockData(symbol);
    }, 500);
    return () => clearTimeout(timer);
  }, [symbol, fetchStockData]);

  // 現價即時更新（每10秒）
  useEffect(() => {
    if (!symbol || symbol.length < 4) return;
    const refreshQuote = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/big-order/quote/${symbol}`);
        const data = await res.json();
        if (data && data.price) {
          setFubonQuote(data);
          setMarketData(prev => ({ ...prev, current: data.price }));
          // 同時更新 ORB 區間（今日高低）
          if (data.high && data.low) {
            setOrbData(prev => ({ ...prev, high: data.high, low: data.low }));
          }
        }
      } catch { }
    };
    const interval = setInterval(refreshQuote, 10000);
    return () => clearInterval(interval);
  }, [symbol]);

  // 撐壓分析自動更新（每60秒）
  useEffect(() => {
    if (!symbol || symbol.length < 4) return;

    const refreshAnalysis = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/smart-entry/support-resistance/${symbol}`);
        const data = await res.json();
        if (data.success && data.levels) {
          const autoLevels = data.levels.map((level, idx) => ({
            id: Date.now() + idx,
            price: level.price,
            type: level.type,
            conditions: level.conditions,
            score: level.score,
            resonance: level.resonance,
            labels: level.labels,
            auto: true,
          }));
          setLevels(autoLevels);
        }
      } catch { }
    };

    // 每60秒更新一次撐壓位
    const interval = setInterval(refreshAnalysis, 60000);
    return () => clearInterval(interval);
  }, [symbol]);


  // 載入觀察清單
  const fetchWatchlist = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/smart-entry/watchlist`);
      const data = await res.json();
      if (data.success) {
        setWatchlist(data.items || []);
      }
    } catch (err) {
      console.error('載入觀察清單失敗:', err);
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  // 加入觀察清單
  const addToWatchlist = async () => {
    if (!symbol || !orbData.high || !orbData.low) {
      alert('請先輸入股票代碼並確認 ORB 區間');
      return;
    }
    try {
      const nearestSup = levels.filter(l => l.type === 'support' && l.price < marketData.current)
        .sort((a, b) => b.price - a.price)[0];
      const nearestRes = levels.filter(l => l.type === 'resistance' && l.price > marketData.current)
        .sort((a, b) => a.price - b.price)[0];

      const res = await fetch(`${API_BASE}/api/smart-entry/watchlist/add?` + new URLSearchParams({
        symbol,
        orb_high: orbData.high,
        orb_low: orbData.low,
        stop_loss: nearestSup?.price || orbData.low * 0.98,
        target_price: nearestRes?.price || orbData.high * 1.02,
        quantity: 1000,
        notes: `ORB ${orbData.high}/${orbData.low}`
      }), { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert(`✅ ${symbol} 已加入觀察清單`);
        fetchWatchlist();
      }
    } catch (err) {
      alert('加入失敗: ' + err.message);
    }
  };

  // 從觀察清單移除
  const removeFromWatchlist = async (sym) => {
    try {
      await fetch(`${API_BASE}/api/smart-entry/watchlist/remove/${sym}`, { method: 'DELETE' });
      fetchWatchlist();
    } catch (err) {
      console.error('移除失敗:', err);
    }
  };

  // 掃描觀察清單（靜默模式，不彈出 alert）
  const scanWatchlist = async (silent = false) => {
    try {
      const res = await fetch(`${API_BASE}/api/smart-entry/watchlist/scan?send_email=true`, { method: 'POST' });
      const data = await res.json();
      setScanResult(data);
      setLastScanTime(new Date().toLocaleTimeString());
      if (!silent && data.signals_count > 0) {
        alert(`📊 掃描完成！\n發現 ${data.signals_count} 檔股票觸發訊號\n${data.email_sent ? '✉️ 已發送郵件通知' : ''}`);
      }
      fetchWatchlist();
      return data;
    } catch (err) {
      if (!silent) alert('掃描失敗: ' + err.message);
      return null;
    }
  };

  // 持續監控 - 每10秒掃描一次
  useEffect(() => {
    let interval = null;
    if (isMonitoring && watchlist.length > 0) {
      // 立即執行一次
      scanWatchlist(true);

      // 每10秒執行一次（加快監控頻率）
      interval = setInterval(() => {
        scanWatchlist(true);
      }, 10000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isMonitoring, watchlist.length]);

  // 觀察清單即時價格更新 - 每5秒更新一次
  useEffect(() => {
    if (watchlist.length === 0) return;

    const updateWatchlistPrices = async () => {
      const updatedWatchlist = await Promise.all(
        watchlist.map(async (item) => {
          try {
            const res = await fetch(`${API_BASE}/api/big-order/quote/${item.symbol}`);
            const data = await res.json();
            if (data && data.price) {
              return {
                ...item,
                current_price: data.price,
                // 檢查是否觸發訊號
                signal: data.price > item.orb_high ? `✅ 突破買進訊號！現價 ${data.price.toFixed(2)} > 突破價 ${item.orb_high}` :
                  data.price < item.orb_low ? `⚠️ 跌破賣出訊號！現價 ${data.price.toFixed(2)} < 跌破價 ${item.orb_low}` :
                    null
              };
            }
          } catch (e) {
            console.warn(`更新 ${item.symbol} 價格失敗:`, e);
          }
          return item;
        })
      );
      setWatchlist(updatedWatchlist);
      setLastScanTime(new Date().toLocaleTimeString());
    };

    // 每5秒更新一次價格
    const priceInterval = setInterval(updateWatchlistPrices, 5000);
    return () => clearInterval(priceInterval);
  }, [watchlist.length]);

  // 切換監控狀態
  const toggleMonitoring = () => {
    if (watchlist.length === 0) {
      alert('請先加入觀察股票');
      return;
    }
    setIsMonitoring(!isMonitoring);
    if (!isMonitoring) {
      // 開始監控時立即掃描一次
      scanWatchlist(true);
    }
  };

  // 自動交易
  const autoTrade = async (sym, action) => {
    try {
      const res = await fetch(`${API_BASE}/api/smart-entry/watchlist/auto-trade?symbol=${sym}&action=${action}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert(`✅ ${action === 'buy' ? '買進' : '賣出'} ${sym} 成功！`);
        fetchWatchlist();
      }
    } catch (err) {
      alert('交易失敗: ' + err.message);
    }
  };


  const calculateAutoFibs = () => {
    if (!marketData.prevHigh || !marketData.prevLow) return;
    const diff = marketData.prevHigh - marketData.prevLow;
    return { fib0382: marketData.prevLow + diff * 0.382, fib0618: marketData.prevLow + diff * 0.618 };
  };

  const autoFibs = calculateAutoFibs();

  const addLevel = () => {
    if (!newLevelPrice) return;
    let score = 0;
    selectedMethods.forEach(method => {
      score += ['prev_hl', 'volume_area', 'key_price'].includes(method) ? 2 : 1;
    });
    const newLevel = { id: Date.now(), price: parseFloat(newLevelPrice), type: newLevelType, conditions: [...selectedMethods], score };
    setLevels([...levels, newLevel].sort((a, b) => b.price - a.price));
    setNewLevelPrice('');
    setSelectedMethods([]);
  };


  const removeLevel = (id) => setLevels(levels.filter(l => l.id !== id));
  const toggleMethod = (methodId) => {
    setSelectedMethods(prev => prev.includes(methodId) ? prev.filter(m => m !== methodId) : [...prev, methodId]);
  };

  const getStrategyAdvice = () => {
    const { current } = marketData;
    const { high: orbHigh, low: orbLow } = orbData;
    if (!current || !orbHigh || !orbLow) return { status: '等待數據', color: 'text-gray-500', icon: <Activity /> };

    const resistances = levels.filter(l => l.type === 'resistance' && l.price > current).sort((a, b) => a.price - b.price);
    const supports = levels.filter(l => l.type === 'support' && l.price < current).sort((a, b) => b.price - a.price);
    const nearestRes = resistances[0];
    const nearestSup = supports[0];

    let status = '', color = '', icon = null;
    if (current > orbHigh) {
      status = 'ORB 突破多方強勢';
      color = 'text-red-600';
      icon = <TrendingUp />;
      if (nearestRes && (nearestRes.price - current) / current < 0.005) {
        status += ` (留意 ${nearestRes.price.toFixed(1)} 強壓)`;
        color = 'text-orange-600';
        icon = <AlertTriangle />;
      }
    } else if (current < orbLow) {
      status = 'ORB 跌破空方弱勢';
      color = 'text-green-600';
      icon = <TrendingDown />;
      if (nearestSup && (current - nearestSup.price) / current < 0.005) {
        status += ` (留意 ${nearestSup.price.toFixed(1)} 支撐)`;
        color = 'text-teal-600';
        icon = <AlertTriangle />;
      }
    } else {
      status = 'ORB 區間震盪整理';
      color = 'text-amber-600';
      icon = <Activity />;
    }
    return { status, color, icon, nearestRes, nearestSup };
  };

  const advice = getStrategyAdvice();
  const volumePressure = volumeAnalysis.buyVol / (volumeAnalysis.buyVol + volumeAnalysis.sellVol + 0.1) * 100;

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 to-blue-50 text-gray-800 font-sans overflow-hidden">

      {/* 頂部導航 */}
      <header className="bg-white border-b border-gray-200 p-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Layers className="text-white" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">當沖戰情室</h1>
            <p className="text-xs text-gray-500">撐壓九宮格決策系統</p>
          </div>

          <div className={`ml-4 flex items-center gap-1 text-xs px-2 py-1 rounded-full ${fubonConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
            {fubonConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {fubonConnected ? '即時連線' : '離線'}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-gray-100 px-3 py-2 rounded-lg border border-gray-200">
            <Search size={16} className="text-gray-400" />
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-24 bg-transparent text-lg font-mono font-bold text-blue-600 focus:outline-none uppercase"
              placeholder="股票代碼"
            />
            {loading && <Loader2 size={16} className="animate-spin text-blue-500" />}
            <button onClick={() => fetchStockData(symbol)} className="p-1 hover:bg-gray-200 rounded">
              <RefreshCw size={14} className="text-gray-500" />
            </button>
          </div>

          {marketData.current > 0 && (
            <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-lg border border-gray-200 shadow-sm">
              <span className="text-sm text-gray-500">現價</span>
              <span className="text-2xl font-mono font-bold text-gray-900">{marketData.current}</span>
              {fubonQuote && (
                <span className={`text-sm font-mono ${fubonQuote.change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {fubonQuote.change >= 0 ? '▲' : '▼'}{Math.abs(fubonQuote.change)?.toFixed(2)}%
                </span>
              )}
            </div>
          )}

          {/* 觀察清單按鈕 */}
          <button
            onClick={addToWatchlist}
            disabled={!symbol || !orbData.high}
            className="flex items-center gap-1 px-3 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg font-medium hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            title="加入觀察清單"
          >
            <Plus size={16} />
            觀察
          </button>

          <button
            onClick={() => setShowWatchlist(!showWatchlist)}
            className={`flex items-center gap-1 px-3 py-2 rounded-lg font-medium text-sm border ${showWatchlist ? 'bg-purple-100 text-purple-700 border-purple-300' : 'bg-gray-100 text-gray-600 border-gray-200 hover:bg-gray-200'
              }`}
          >
            <Eye size={16} />
            清單 ({watchlist.length})
          </button>

          <button
            onClick={toggleMonitoring}
            disabled={watchlist.length === 0}
            className={`flex items-center gap-1 px-3 py-2 rounded-lg font-medium text-sm ${isMonitoring
              ? 'bg-gradient-to-r from-red-500 to-rose-500 text-white animate-pulse'
              : 'bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={isMonitoring ? '停止監控' : '開始持續監控（每30秒）'}
          >
            {isMonitoring ? (
              <>
                <Bell size={16} className="animate-bounce" />
                監控中...
              </>
            ) : (
              <>
                <Bell size={16} />
                開始監控
              </>
            )}
          </button>

          {lastScanTime && (
            <span className="text-xs text-gray-400">
              最後掃描: {lastScanTime}
            </span>
          )}


          <button
            onClick={() => setShowGuide(true)}
            className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 hover:text-blue-600"
            title="使用說明"
          >
            <HelpCircle size={20} />
          </button>
        </div>
      </header>

      {/* 觀察清單面板 */}
      {showWatchlist && (
        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-purple-200 px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-bold text-purple-800 flex items-center gap-2">
              <Eye size={16} /> 觀察清單 ({watchlist.length} 檔)
            </h3>
            <button onClick={() => setShowWatchlist(false)} className="text-gray-400 hover:text-gray-600">
              <X size={16} />
            </button>
          </div>
          {watchlist.length === 0 ? (
            <p className="text-sm text-gray-500">尚無觀察股票，請先分析後點擊「觀察」加入</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {watchlist.map(item => (
                <div key={item.symbol} className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${item.signal ? 'bg-red-100 border-red-300' : 'bg-white border-gray-200'
                  }`}>
                  <span className="font-bold text-gray-800">{item.stock_name || item.symbol}</span>
                  <span className="text-gray-400 text-xs">({item.symbol})</span>
                  <span className="text-gray-500">現價: {item.current_price?.toFixed(1) || '--'}</span>
                  <span className="text-red-500 text-xs">突破 {item.orb_high}</span>
                  <span className="text-green-500 text-xs">跌破 {item.orb_low}</span>

                  {item.signal && (
                    <span className="px-2 py-0.5 bg-red-500 text-white rounded text-xs animate-pulse">訊號!</span>
                  )}
                  {item.signal && item.signal.includes('買進') && (
                    <button
                      onClick={() => autoTrade(item.symbol, 'buy')}
                      className="px-2 py-0.5 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
                    >
                      <Play size={12} className="inline" /> 買進
                    </button>
                  )}
                  <button
                    onClick={() => removeFromWatchlist(item.symbol)}
                    className="text-gray-400 hover:text-red-500"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}


      {error && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-700">
          ⚠️ {error}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">

        {/* 左側面板 */}
        <aside className="w-96 bg-white border-r border-gray-200 p-4 overflow-y-auto flex-shrink-0">
          <div className="space-y-5">

            {/* 使用說明卡片 */}
            {showGuide && !symbol && (
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 relative">
                <button onClick={() => setShowGuide(false)} className="absolute top-2 right-2 text-gray-400 hover:text-gray-600">
                  <X size={16} />
                </button>
                <h3 className="font-bold text-blue-800 mb-3 flex items-center gap-2">
                  <HelpCircle size={18} /> 使用說明
                </h3>
                <div className="space-y-3 text-sm text-gray-700">
                  <div className="flex gap-2">
                    <span className="bg-blue-600 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0">1</span>
                    <span><b>輸入股票代碼</b>（如 2330），系統自動載入昨日高低、今日 ORB、布林通道等數據</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="bg-blue-600 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0">2</span>
                    <span><b>觀察戰略地圖</b>，布林上下軌會自動加入為撐壓參考</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="bg-blue-600 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0">3</span>
                    <span><b>手動新增關鍵位</b>：輸入價格 → 選擇撐壓類型 → 勾選九大條件 → 加入戰情板</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="bg-blue-600 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0">4</span>
                    <span><b>參考 AI 建議</b>：根據 ORB 突破/跌破狀態和撐壓位置給出操作建議</span>
                  </div>
                </div>
                <div className="mt-4 p-3 bg-white/70 rounded-lg border border-blue-100">
                  <p className="text-xs text-gray-600">
                    <b>九宮格共振原理：</b>當某價位符合越多條件（如同時是前高、整數關卡、布林上軌），該撐壓越強，突破或跌破的意義越大。
                  </p>
                </div>
              </div>
            )}

            {/* 富邦即時報價 */}
            {fubonQuote && (
              <section className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-sm font-bold text-emerald-700 flex items-center gap-1">
                    <Wifi size={14} /> 富邦即時報價
                  </span>
                  <span className="text-xs bg-emerald-100 text-emerald-600 px-2 py-0.5 rounded">即時</span>
                </div>
                <div className="grid grid-cols-4 gap-2 text-center">
                  {[
                    { label: '開盤', value: fubonQuote.open ? Number(fubonQuote.open).toFixed(2) : '--', color: 'text-amber-600' },
                    { label: '最高', value: fubonQuote.high ? Number(fubonQuote.high).toFixed(2) : '--', color: 'text-red-600' },
                    { label: '最低', value: fubonQuote.low ? Number(fubonQuote.low).toFixed(2) : '--', color: 'text-green-600' },
                    { label: '成交量', value: fubonQuote.volume ? `${(fubonQuote.volume / 1000).toFixed(0)}K` : '--', color: 'text-gray-700' },
                  ].map(item => (
                    <div key={item.label} className="bg-white/80 rounded-lg p-2">
                      <div className="text-xs text-gray-500">{item.label}</div>
                      <div className={`font-mono font-bold ${item.color}`}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* AI 評分 */}
            {apiData && (
              <section className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-sm font-bold text-blue-700">📊 AI 智慧評分</span>
                  <span className={`text-2xl font-black ${apiData.score >= 70 ? 'text-red-600' : apiData.score >= 50 ? 'text-amber-600' : 'text-green-600'
                    }`}>{apiData.score}分</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  {[
                    { label: '建議', value: apiData.recommendation },
                    { label: '動能', value: apiData.factors?.momentum?.status },
                    { label: '技術', value: apiData.factors?.technical?.status },
                  ].map(item => (
                    <div key={item.label} className="bg-white/80 rounded-lg p-2">
                      <div className="text-xs text-gray-500">{item.label}</div>
                      <div className="font-bold text-gray-800">{item.value}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 🎯 專業交易建議 - 新增區塊 */}
            {marketData.current > 0 && orbData.high > 0 && (
              <section className="bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-400 rounded-xl p-4 shadow-lg">
                <h3 className="text-sm font-bold text-amber-800 mb-3 flex items-center gap-2">
                  🎯 今日當沖建議
                  <span className="text-xs bg-amber-200 text-amber-700 px-2 py-0.5 rounded">即時</span>
                </h3>

                {/* 今日關鍵三價位 */}
                <div className="grid grid-cols-3 gap-2 mb-4">
                  <div className="bg-green-100 border border-green-300 rounded-lg p-2 text-center">
                    <div className="text-xs text-green-600 font-medium">🟢 今日買點</div>
                    <div className="text-lg font-mono font-bold text-green-700">
                      {orbData.low ? Number(orbData.low).toFixed(2) : '--'}
                    </div>
                    <div className="text-xs text-green-500">今低/回測進場</div>
                  </div>
                  <div className="bg-red-100 border border-red-300 rounded-lg p-2 text-center">
                    <div className="text-xs text-red-600 font-medium">🔴 今日賣點</div>
                    <div className="text-lg font-mono font-bold text-red-700">{orbData.high ? Number(orbData.high).toFixed(2) : '--'}</div>
                    <div className="text-xs text-red-500">今高/獲利出場</div>
                  </div>
                  <div className="bg-gray-100 border border-gray-300 rounded-lg p-2 text-center">
                    <div className="text-xs text-gray-600 font-medium">⚠️ 停損點</div>
                    <div className="text-lg font-mono font-bold text-gray-700">
                      {orbData.low ? (orbData.low * 0.98).toFixed(2) : '--'}
                    </div>
                    <div className="text-xs text-gray-500">今低-2%</div>
                  </div>
                </div>

                {/* 當沖操作策略 */}
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2 bg-white/70 rounded-lg p-2">
                    <span className="text-blue-500 font-bold">💼</span>
                    <div>
                      <span className="font-bold text-blue-700">已持有：</span>
                      <span className="text-gray-700">
                        停利 <span className="font-mono text-red-600">{orbData.high.toFixed(1)}</span>，
                        停損 <span className="font-mono text-green-600">{orbData.low.toFixed(1)}</span>
                      </span>
                    </div>
                  </div>
                  <div className="flex items-start gap-2 bg-white/70 rounded-lg p-2">
                    <span className="text-amber-500 font-bold">👀</span>
                    <div>
                      <span className="font-bold text-amber-700">等回測：</span>
                      <span className="text-gray-700">
                        股價回到 <span className="font-mono text-blue-600">{orbData.low.toFixed(1)}~{(orbData.low * 1.01).toFixed(1)}</span> 區間再買進
                      </span>
                    </div>
                  </div>
                  <div className="flex items-start gap-2 bg-white/70 rounded-lg p-2">
                    <span className="text-red-500 font-bold">🚀</span>
                    <div>
                      <span className="font-bold text-red-700">追突破：</span>
                      <span className="text-gray-700">
                        突破 <span className="font-mono text-red-600">{orbData.high.toFixed(1)}</span> 追進，
                        停損 <span className="font-mono text-green-600">{(orbData.high * 0.98).toFixed(1)}</span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* 今日 vs 昨日對比 */}
                {marketData.prevHigh > 0 && (
                  <div className="mt-3 pt-3 border-t border-amber-200 text-xs text-gray-500">
                    📊 昨日高低參考：{marketData.prevHigh.toFixed(1)} ~ {marketData.prevLow.toFixed(1)}
                    {marketData.current > marketData.prevHigh && (
                      <span className="ml-2 text-red-500 font-medium">↑ 今日創新高</span>
                    )}
                    {marketData.current < marketData.prevLow && (
                      <span className="ml-2 text-green-500 font-medium">↓ 今日創新低</span>
                    )}
                  </div>
                )}
              </section>
            )}

            {/* 總結操作建議移至右側面板 */}

            {/* 布林通道 */}
            {bollingerData && (
              <section className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-4">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-sm font-bold text-purple-700">📈 布林通道</span>
                  <span className={`text-sm font-bold px-2 py-0.5 rounded ${bollingerData.signal === '買入' ? 'bg-red-100 text-red-600' :
                    bollingerData.signal === '賣出' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'
                    }`}>{bollingerData.signal}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-white/80 rounded-lg p-2">
                    <div className="text-xs text-green-600">下軌</div>
                    <div className="font-mono font-bold">{bollingerData.bollinger?.lower}</div>
                  </div>
                  <div className="bg-white/80 rounded-lg p-2">
                    <div className="text-xs text-gray-500">中軌</div>
                    <div className="font-mono font-bold">{bollingerData.bollinger?.middle}</div>
                  </div>
                  <div className="bg-white/80 rounded-lg p-2">
                    <div className="text-xs text-red-600">上軌</div>
                    <div className="font-mono font-bold">{bollingerData.bollinger?.upper}</div>
                  </div>
                </div>
                <div className="text-xs text-center text-gray-500 mt-2">
                  {bollingerData.position_text} | %B: {bollingerData.bollinger?.percent_b}%
                </div>
              </section>
            )}

            {/* 盤前定位 */}
            {(marketData.prevHigh > 0 || marketData.prevLow > 0) && (
              <section className="bg-white border border-gray-200 rounded-xl p-4">
                <h3 className="text-sm font-bold text-amber-600 mb-3 flex items-center gap-1">
                  <Target size={14} /> 盤前定位（昨日數據）
                </h3>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-red-50 rounded-lg p-2">
                    <div className="text-xs text-gray-500">昨高</div>
                    <div className="font-mono font-bold text-red-600">{marketData.prevHigh}</div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-2">
                    <div className="text-xs text-gray-500">昨低</div>
                    <div className="font-mono font-bold text-green-600">{marketData.prevLow}</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2">
                    <div className="text-xs text-gray-500">昨收</div>
                    <div className="font-mono font-bold text-gray-700">{marketData.prevClose}</div>
                  </div>
                </div>
                {autoFibs && (
                  <div className="text-xs text-gray-500 mt-2 text-center">
                    斐波那契: 0.382={autoFibs.fib0382.toFixed(1)} | 0.618={autoFibs.fib0618.toFixed(1)}
                  </div>
                )}
              </section>
            )}

            {/* 九宮格撐壓分析器 */}
            <section className="bg-white border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-bold text-purple-600 mb-3 flex items-center gap-1">
                <CheckCircle size={14} /> 新增撐壓關鍵位
              </h3>

              <div className="flex gap-2 mb-3">
                <input
                  type="number"
                  placeholder="輸入價格..."
                  value={newLevelPrice}
                  onChange={e => setNewLevelPrice(e.target.value)}
                  className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:ring-1 focus:ring-purple-200 outline-none"
                />
                <select
                  value={newLevelType}
                  onChange={e => setNewLevelType(e.target.value)}
                  className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="resistance">壓力</option>
                  <option value="support">支撐</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-1 mb-3">
                {nineMethods.map(method => (
                  <button
                    key={method.id}
                    onClick={() => toggleMethod(method.id)}
                    className={`text-xs text-left px-2 py-1.5 rounded-lg border transition-all ${selectedMethods.includes(method.id)
                      ? 'bg-purple-100 border-purple-400 text-purple-700'
                      : 'bg-gray-50 border-gray-200 text-gray-600 hover:border-gray-300'
                      }`}
                  >
                    {method.label}
                  </button>
                ))}
              </div>

              <button
                onClick={addLevel}
                disabled={!newLevelPrice || selectedMethods.length === 0}
                className="w-full bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 disabled:from-gray-300 disabled:to-gray-300 text-white text-sm py-2.5 rounded-lg flex items-center justify-center gap-2 transition-all shadow-sm"
              >
                <Calculator size={14} /> 計算共振強度並加入
              </button>
            </section>

            {/* 量能判斷 */}
            <section className="bg-white border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-bold text-orange-600 mb-3 flex items-center gap-1">
                <BarChart2 size={14} /> 買賣力道
              </h3>
              <div className="h-4 w-full bg-gray-200 rounded-full overflow-hidden flex">
                <div className="bg-gradient-to-r from-red-400 to-red-500 h-full transition-all duration-500" style={{ width: `${volumePressure}%` }} />
                <div className="bg-gradient-to-r from-green-400 to-green-500 h-full transition-all duration-500 flex-1" />
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>買方 {volumePressure.toFixed(0)}%</span>
                <span>賣方 {(100 - volumePressure).toFixed(0)}%</span>
              </div>
            </section>

          </div>
        </aside>

        {/* 右側戰情板 */}
        <main className="flex-1 flex flex-col p-4 overflow-hidden">

          {/* 頂部策略總結區 - 水平排列 */}
          <div className="flex gap-3 mb-3 flex-shrink-0">
            {/* ORB 區間 */}
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-2 shadow-sm flex items-center gap-4">
              <span className="text-xs font-bold text-gray-500 flex items-center gap-1">
                <Zap size={12} className="text-blue-500" /> ORB
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-red-500">突破</span>
                <span className="font-mono font-bold text-red-600">{orbData.high ? Number(orbData.high).toFixed(2) : '--'}</span>
              </div>
              <div className="w-px h-4 bg-gray-300" />
              <div className="flex items-center gap-2">
                <span className="text-xs text-green-500">跌破</span>
                <span className="font-mono font-bold text-green-600">{orbData.low ? Number(orbData.low).toFixed(2) : '--'}</span>
              </div>
            </div>

            {/* AI 戰術建議 */}
            {advice.nearestRes && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex items-center gap-2">
                <span className="text-xs text-red-500">近壓</span>
                <span className="font-mono font-bold text-red-600">{advice.nearestRes.price.toFixed(1)}</span>
                <span className="text-xs bg-red-100 text-red-500 px-1 rounded">強度{advice.nearestRes.score}</span>
              </div>
            )}
            {advice.nearestSup && (
              <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 flex items-center gap-2">
                <span className="text-xs text-green-500">近撐</span>
                <span className="font-mono font-bold text-green-600">{advice.nearestSup.price.toFixed(1)}</span>
                <span className="text-xs bg-green-100 text-green-500 px-1 rounded">強度{advice.nearestSup.score}</span>
              </div>
            )}

            {/* 狀態 */}
            {advice.status !== '等待數據' && (
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg font-bold text-sm ${advice.color} bg-white border border-gray-200 shadow-sm ml-auto`}>
                {advice.icon}
                <span>{advice.status}</span>
              </div>
            )}
          </div>

          {/* 總結操作建議 - 移至此處 */}
          <div className="mb-3 flex-shrink-0">
            <StrategySummary marketData={marketData} levels={levels} orbData={orbData} />
          </div>

          {/* 戰略地圖標題 */}
          <div className="flex items-center justify-between mb-2 flex-shrink-0">
            <h2 className="text-base font-bold text-gray-800 flex items-center gap-2">
              <Layers size={18} className="text-blue-500" />
              戰略地圖 {symbol && <span className="text-blue-600">{symbol}</span>}
              {levels.length > 0 && <span className="text-xs text-gray-400 font-normal">({levels.length} 個撐壓位)</span>}
            </h2>
          </div>

          {/* 戰略地圖 - 可滾動 */}
          <div className="flex-1 bg-white rounded-xl border border-gray-200 shadow-sm overflow-y-auto">
            {levels.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-gray-400 p-8">
                <Layers size={48} className="mb-4 opacity-50" />
                <p className="text-lg font-medium">輸入股票代碼開始分析</p>
                <p className="text-sm mt-1">系統將自動分析九大撐壓條件</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {levels.map(level => (
                  <div key={level.id} className={`flex items-center px-4 py-3 hover:bg-gray-50 transition-colors ${level.type === 'resistance' ? 'border-l-4 border-l-red-400' : 'border-l-4 border-l-green-400'
                    }`}>
                    {/* 類型標籤 */}
                    <div className="w-12 flex-shrink-0">
                      <span className={`text-xs font-bold ${level.type === 'resistance' ? 'text-red-600' : 'text-green-600'}`}>
                        {level.type === 'resistance' ? '壓力' : '支撐'}
                      </span>
                      <div className="flex mt-0.5 gap-0.5">
                        {[...Array(Math.min(level.score, 5))].map((_, i) => (
                          <div key={i} className={`w-1.5 h-1.5 rounded-full ${level.type === 'resistance' ? 'bg-red-400' : 'bg-green-400'}`} />
                        ))}
                      </div>
                    </div>

                    {/* 價格 */}
                    <div className="w-24 flex-shrink-0">
                      <span className="text-xl font-mono font-bold text-gray-900">{level.price.toFixed(1)}</span>
                    </div>

                    {/* 共振信息 */}
                    <div className="flex-1 mr-4">
                      <div className="flex flex-wrap gap-1">
                        {level.labels?.slice(0, 4).map((label, idx) => (
                          <span key={idx} className="text-xs px-1.5 py-0.5 bg-blue-50 rounded text-blue-600 border border-blue-100">
                            {label}
                          </span>
                        ))}
                        {level.labels?.length > 4 && (
                          <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">
                            +{level.labels.length - 4}
                          </span>
                        )}
                        {!level.labels && level.conditions?.map(c => (
                          <span key={c} className="text-xs px-1.5 py-0.5 bg-gray-50 rounded text-gray-500 border border-gray-200">
                            {nineMethods.find(m => m.id === c)?.label.split(' ')[1]}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* 距離現價 */}
                    {marketData.current > 0 && (
                      <div className="text-right w-24 flex-shrink-0">
                        <div className={`font-mono text-sm ${(marketData.current - level.price) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {(marketData.current - level.price) > 0 ? '-' : '+'}{Math.abs(marketData.current - level.price).toFixed(1)}
                        </div>
                        <div className="text-xs text-gray-400">
                          {Math.abs((marketData.current - level.price) / marketData.current * 100).toFixed(2)}%
                        </div>
                      </div>
                    )}

                    {/* 共振強度 */}
                    <div className="w-16 text-center flex-shrink-0">
                      <div className="text-xs text-gray-400">共振</div>
                      <div className="font-bold text-purple-600">{level.resonance || level.conditions?.length || 1}</div>
                    </div>

                    <button onClick={() => removeLevel(level.id)} className="text-gray-300 hover:text-red-500 ml-2">×</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>

      </div>
    </div>
  );
};

export default App;
