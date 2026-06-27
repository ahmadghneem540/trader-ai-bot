import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getBacktestById, getBacktestTrades } from '../services/api';

const BacktestResults = () => {
  const { backtestId } = useParams();
  const navigate = useNavigate();
  const [backtest, setBacktest] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBacktest();
  }, [backtestId]);

  const loadBacktest = async () => {
    try {
      const [backtestData, tradesData] = await Promise.all([
        getBacktestById(backtestId),
        getBacktestTrades(backtestId)
      ]);
      setBacktest(backtestData);
      setTrades(tradesData);
    } catch (err) {
      console.error('Failed to load backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <h1 className="page-title">Loading...</h1>
      </div>
    );
  }

  if (!backtest) {
    return (
      <div className="container">
        <h1 className="page-title">Backtest Not Found</h1>
        <button className="btn btn-secondary" onClick={() => navigate('/strategy-tester')}>
          Back to Tester
        </button>
      </div>
    );
  }

  return (
    <div className="container">
      <button className="btn btn-secondary" onClick={() => navigate('/strategy-tester')} style={{ marginBottom: '20px' }}>
        ← Back to Strategy Tester
      </button>

      <h1 className="page-title">Backtest Results</h1>

      <div className="grid grid-4" style={{ marginBottom: '20px' }}>
        <div className="stat-card">
          <div className="stat-label">Initial Balance</div>
          <div className="stat-value">${backtest.initial_balance.toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Final Balance</div>
          <div className="stat-value">${backtest.final_balance.toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Net Profit</div>
          <div className={`stat-value ${backtest.net_profit >=0 ? 'positive' : 'negative'}`}>
            {backtest.net_profit >=0 ? '+' : ''}${backtest.net_profit.toFixed(2)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Trades</div>
          <div className="stat-value">{backtest.total_trades}</div>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: '20px' }}>
        <div className="stat-card">
          <div className="stat-label">Win Rate</div>
          <div className="stat-value">{backtest.win_rate.toFixed(2)}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Max Drawdown</div>
          <div className="stat-value">{backtest.max_drawdown.toFixed(2)}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Profit Factor</div>
          <div className="stat-value">{backtest.profit_factor.toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Sharpe Ratio</div>
          <div className="stat-value">{backtest.sharpe_ratio.toFixed(2)}</div>
        </div>
      </div>

      <div className="card">
        <h2 className="card-title">Trade History</h2>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Profit</th>
              <th>Profit %</th>
              <th>Duration (min)</th>
              <th>Exit Reason</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
            <tr key={trade.id}>
              <td>
                <span className={`status-badge status-${trade.trade_type}`}>
                  {trade.trade_type}
                </span>
              </td>
              <td>{trade.entry_price.toFixed(5)}</td>
              <td>{trade.exit_price.toFixed(5)}</td>
              <td className={trade.profit >= 0 ? 'positive' : 'negative'}>
                {trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}
              </td>
              <td className={trade.profit_pct >=0 ? 'positive' : 'negative'}>
                {trade.profit_pct.toFixed(2)}%
              </td>
              <td>{trade.duration.toFixed(2)}</td>
              <td>{trade.exit_reason}</td>
            </tr>
          ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BacktestResults;
