import React, { useEffect, useState } from 'react';
import { getMT5Candles, getMT5Tick, getMT5Account } from '../services/api';
import TradingPanel from '../components/TradingPanel';
import './GoldChart.css';

function GoldChart() {
  const [timeframe, setTimeframe] = useState('H1');
  const [currentTick, setCurrentTick] = useState(null);
  const [accountInfo, setAccountInfo] = useState(null);

  const timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const tick = await getMT5Tick('XAUUSD');
        setCurrentTick(tick);

        const account = await getMT5Account();
        setAccountInfo(account);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="gold-chart">
      <div className="chart-header">
        <h1>Gold Chart</h1>
        <div className="timeframe-selector">
          {timeframes.map(tf => (
            <button
              key={tf}
              className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      
      <div className="chart-container">
        <div className="chart-main">
          <div>Chart temporarily disabled (missing lightweight-charts library)</div>
        </div>
        <div className="chart-sidebar">
          <TradingPanel 
            currentTick={currentTick} 
            accountInfo={accountInfo}
            onTradeSuccess={() => {}}
          />
        </div>
      </div>
    </div>
  );
}

export default GoldChart;
