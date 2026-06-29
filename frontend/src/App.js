import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import StrategyTester from './pages/StrategyTester';
import BacktestResults from './pages/BacktestResults';
import MT5Connection from './pages/MT5Connection';
import GoldChart from './pages/GoldChart';
import OpenPositions from './pages/OpenPositions';
import TradeHistory from './pages/TradeHistory';
import StrategySettings from './pages/StrategySettings';
import Logs from './pages/Logs';
import DebugConsole from './pages/DebugConsole';
import './App.css';

function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/mt5-connection" element={<MT5Connection />} />
        <Route path="/chart" element={<GoldChart />} />
        <Route path="/positions" element={<OpenPositions />} />
        <Route path="/history" element={<TradeHistory />} />
        <Route path="/strategy" element={<StrategySettings />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/debug" element={<DebugConsole />} />
        <Route path="/strategy-tester" element={<StrategyTester />} />
        <Route path="/backtest/:backtestId" element={<BacktestResults />} />
      </Routes>
    </div>
  );
}

export default App;
