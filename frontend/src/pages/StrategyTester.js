import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { listStrategies, getSymbols, runBacktest, getBacktestResults } from '../services/api';

const StrategyTester = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState([]);
  const [symbols, setSymbols] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [timeframe, setTimeframe] = useState('H1');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [initialBalance, setInitialBalance] = useState(10000);
  const [backtests, setBacktests] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [strategiesData, symbolsData, backtestsData] = await Promise.all([
        listStrategies(),
        getSymbols(),
        getBacktestResults()
      ]);
      setStrategies(strategiesData.strategies || []);
      setSymbols(symbolsData || []);
      setBacktests(backtestsData || []);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  const handleRunBacktest = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = {
        strategy_name: selectedStrategy,
        symbol_name: selectedSymbol,
        timeframe: timeframe,
        start_date: new Date(startDate),
        end_date: new Date(endDate),
        initial_balance: parseFloat(initialBalance)
      };
      await runBacktest(data);
      loadData();
    } catch (err) {
      console.error('Failed to run backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1 className="page-title">Strategy Tester</h1>

      <div className="card" style={{ marginBottom: '20px' }}>
        <h2 className="card-title">Configure Backtest</h2>
        <form onSubmit={handleRunBacktest} className="form">
          <div className="form-group">
            <label>Strategy</label>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              required
            >
              <option value="">Select Strategy</option>
              {strategies.map((s, idx) => (
                <option key={idx} value={s.name}>{s.name} - {s.description}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Symbol</label>
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              required
            >
              <option value="">Select Symbol</option>
              {symbols.map((symbol) => (
                <option key={symbol.id} value={symbol.name}>{symbol.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Timeframe</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              required
            >
              <option value="M1">M1</option>
              <option value="M5">M5</option>
              <option value="M15">M15</option>
              <option value="M30">M30</option>
              <option value="H1">H1</option>
              <option value="H4">H4</option>
              <option value="D1">D1</option>
              <option value="W1">W1</option>
            </select>
          </div>

          <div className="form-group">
            <label>Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Initial Balance</label>
            <input
              type="number"
              value={initialBalance}
              onChange={(e) => setInitialBalance(e.target.value)}
              min="100"
              step="100"
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? 'Running Backtest...' : 'Run Backtest'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2 className="card-title">Backtest History</h2>
        <table>
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Symbol</th>
              <th>Timeframe</th>
              <th>Initial</th>
              <th>Final</th>
              <th>Profit</th>
              <th>Win Rate</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {backtests.map((bt) => (
              <tr key={bt.id}>
                <td>{bt.strategy_name}</td>
                <td>{bt.symbol_name}</td>
                <td>{bt.timeframe}</td>
                <td>${bt.initial_balance.toFixed(2)}</td>
                <td>${bt.final_balance ? bt.final_balance.toFixed(2) : '-'}</td>
                <td className={bt.net_profit >= 0 ? 'positive' : 'negative'}>
                  {bt.net_profit !== null ? `${bt.net_profit >= 0 ? '+' : ''}$${bt.net_profit.toFixed(2)}` : '-'}
                </td>
                <td>{bt.win_rate !== null ? `${bt.win_rate.toFixed(2)}%` : '-'}</td>
                <td>
                  <span className={`status-badge status-${bt.status}`}>
                    {bt.status}
                  </span>
                </td>
                <td>
                  {bt.status === 'completed' && (
                    <button
                      className="btn btn-small"
                      onClick={() => navigate(`/backtest/${bt.id}`)}
                    >
                      View
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StrategyTester;
