'use client';

import React, { useState, useEffect } from 'react';
import { Target, Activity, DollarSign, ShieldAlert, Cpu, Zap, Box, TrendingUp, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

// API Url Helper
const API_BASE_URL = 'http://localhost:8000';

export default function TradingExecutorPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<any>(null);

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/trading-executor/status`);
      setData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async () => {
    setScanning(true);
    setScanResult(null);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/trading-executor/scan`);
      setScanResult(res.data);
      // Refresh status after scan
      await fetchStatus();
    } catch (err: any) {
      setScanResult({ success: false, error: err.message });
    } finally {
      setScanning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  const isSimulation = data?.mode?.includes('Simulation');

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 z-10 relative">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Target className="w-8 h-8 text-blue-400" />
            AI 實盤執行官
          </h1>
          <p className="text-gray-400 mt-2">LSTM PyTorch 神經網路的自動決策樞紐</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-gray-800/80 border border-gray-700 px-4 py-2 rounded-xl backdrop-blur-md">
            {isSimulation ? (
              <ShieldAlert className="w-5 h-5 text-yellow-500" />
            ) : (
              <Zap className="w-5 h-5 text-red-500" />
            )}
            <div className="text-sm font-medium">
              <span className="text-gray-400 block text-xs">運作模式</span>
              <span className={isSimulation ? "text-yellow-400" : "text-red-400"}>
                {data?.mode || '未知'}
              </span>
            </div>
          </div>
          <button 
            onClick={handleScan}
            disabled={scanning}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold transition-all shadow-lg
              ${scanning 
                ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-900/30'
              }`}
          >
            {scanning ? (
              <div className="w-5 h-5 border-2 border-gray-400/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Cpu className="w-5 h-5" />
            )}
            {scanning ? '神經網絡掃描中...' : '強制執行手動掃描'}
          </button>
        </div>
      </div>

      {scanResult && (
        <div className={`p-4 rounded-xl border ${scanResult.success ? 'bg-green-900/20 border-green-500/30 text-green-400' : 'bg-red-900/20 border-red-500/30 text-red-400'} backdrop-blur-sm animate-in fade-in slide-in-from-top-4`}>
          <div className="flex items-center gap-2 font-bold mb-1">
            <CheckCircle2 className="w-5 h-5" /> {scanResult.success ? '掃描完畢' : '掃描失敗'}
          </div>
          <p className="text-sm opacity-90">{scanResult.message || scanResult.error}</p>
        </div>
      )}

      {/* Financial Status Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 bg-gray-900/80 border border-gray-800 p-4 rounded-2xl backdrop-blur-md shadow-2xl">
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">總投資本金</p>
          <p className="text-lg font-black text-white">$ {data?.financials?.total_capital?.toLocaleString()}</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">可用本金餘額</p>
          <p className="text-lg font-black text-emerald-400">$ {data?.financials?.available_capital?.toLocaleString()}</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">總權益數 (淨值)</p>
          <p className="text-lg font-black text-blue-400">$ {data?.financials?.equity?.toLocaleString()}</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">總勝率</p>
          <p className="text-lg font-black text-white">{data?.financials?.win_rate || '0.0'}%</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">目前持股成本</p>
          <p className="text-lg font-black text-white">$ {data?.financials?.current_holding_cost?.toLocaleString()}</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">持倉數量</p>
          <p className="text-lg font-black text-white">{data?.financials?.total_positions || 0}</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">未實現損益</p>
          <p className="text-lg font-black text-emerald-400">+ $ {data?.financials?.unrealized_pnl || 0}</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">已實現損益</p>
          <p className={`text-lg font-black ${data?.financials?.realized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {data?.financials?.realized_pnl >= 0 ? "+" : ""}$ {data?.financials?.realized_pnl?.toLocaleString()}
          </p>
        </div>
      </div>

      {/* Targets */}
      <div className="bg-gray-800/60 border border-gray-700 p-5 rounded-2xl backdrop-blur-md">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-gray-400 font-medium">嚴選白名單 (PyTorch 模型對接中)</h3>
          <Box className="w-5 h-5 text-indigo-400" />
        </div>
        <div className="flex flex-wrap gap-3">
          {data?.target_stocks?.map((sym: string) => (
            <span key={sym} className="px-4 py-2 bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 rounded-xl text-md font-black shadow-inner">
              {sym}
            </span>
          ))}
        </div>
      </div>

      {/* Portfolio Table */}
      <div className="bg-gray-800/60 border border-gray-700 rounded-2xl backdrop-blur-md overflow-hidden relative">
        {/* Glow effect */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4 pointer-events-none" />
        
        <div className="p-5 border-b border-gray-700 flex justify-between items-center z-10 relative">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-blue-400" />
            {isSimulation ? "虛擬模擬資產庫 (Virtual Portfolio)" : "真實證券持倉"}
          </h2>
        </div>

        <div className="overflow-x-auto z-10 relative">
          <table className="w-full text-left">
            <thead className="bg-gray-900/50">
              <tr>
                <th className="px-6 py-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">代號 / 名稱</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">持股數</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">成本 / 現價</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">停損 / 目標</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">未實現損益%</th>
                <th className="px-6 py-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">買入時間</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {(!data?.portfolio || data.portfolio.length === 0) ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500 font-medium">
                    目前資料庫無 AI 持倉紀錄，空倉待命。
                  </td>
                </tr>
              ) : (
                data.portfolio.map((item: any, idx: number) => (
                  <tr key={item.symbol + idx} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="font-bold text-blue-400 text-lg">{item.symbol}</span>
                        <span className="text-xs text-gray-500">{item.stock_name || '台股標的'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-white font-medium">
                      {item.quantity?.toLocaleString()} 股
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-white font-bold">$ {item.entry_price?.toLocaleString()}</span>
                        <span className="text-xs text-gray-400">$ {item.current_price?.toLocaleString() || '---'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col text-xs">
                        <span className="text-red-400 font-medium">L: {item.stop_loss || '---'}</span>
                        <span className="text-emerald-400 font-medium">T: {item.target || '---'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-lg text-sm font-black ${item.pnl_percent >= 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                        {item.pnl_percent >= 0 ? "+" : ""}{item.pnl_percent?.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400 text-xs">
                      {item.entry_date ? new Date(item.entry_date).toLocaleString() : 'N/A'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
    </div>
  );
}
