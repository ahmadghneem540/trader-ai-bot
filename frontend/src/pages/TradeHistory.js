import React, { useEffect, useState } from 'react';
import { getMT5History } from '../services/api';
import './TradeHistory.css';

function TradeHistory() {
  const [historyData, setHistoryData] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await getMT5History(days);
        setHistoryData(data);
      } catch (error) {
        console.error('Failed to fetch trade history:', error);
      }
    };

    fetchHistory();
  }, [days]);

  return (
    <div className="trade-history">
      <div className="history-header">
        <h1>Trade History</h1>
        <div className="days-selector">
          <label>Show Last: </label>
          <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
            <option value={365}>1 year</option>
          </select>
        </div>
      </div>

      {historyData && (
        <>
          <div className="summary-cards">
            <div className="summary-card">
              <h4>Total Trades</h4>
              <p className="summary-value">{historyData.total_trades}</p>
            </div>
            <div className="summary-card">
              <h4>Winning Trades</h4>
              <p className="summary-value">{historyData.winning_trades}</p>
            </div>
            <div className="summary-card">
              <h4>Losing Trades</h4>
              <p className="summary-value">{historyData.losing_trades}</p>
            </div>
            <div className="summary-card">
              <h4>Win Rate</h4>
              <p className="summary-value">{historyData.win_rate?.toFixed(2)}%</p>
            </div>
            <div className="summary-card">
              <h4>Total Profit</h4>
              <p className={`summary-value ${historyData.total_profit >= 0 ? 'positive' : 'negative'}`}>
                ${historyData.total_profit?.toFixed(2)}
              </p>
            </div>
          </div>

          <div className="history-table-container">
            {historyData.trades.length === 0 ? (
              <div className="no-trades">
                <p>No trades</p>
              </div>
            ) : (
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Type</th>
                    <th>Symbol</th>
                    <th>Volume</th>
                    <th>Open Price</th>
                    <th>Close Price</th>
                    <th>Profit</th>
                    <th>Close Time</th>
                  </tr>
                </thead>
                <tbody>
                  {historyData.trades.map((trade) => (
                    <tr key={trade.ticket}>
                      <td className="ticket">#{trade.ticket}</td>
                      <td>
                        <span className={`trade-type-badge ${trade.type}`}>
                          {trade.type === 'buy' ? 'BUY' : 'SELL'}
                        </span>
                      </td>
                      <td>{trade.symbol}</td>
                      <td>{trade.volume}</td>
                      <td>{trade.open_price?.toFixed(2)}</td>
                      <td>{trade.close_price?.toFixed(2)}</td>
                      <td className={`profit-cell ${trade.profit >= 0 ? 'positive' : 'negative'}`}>
                        ${trade.profit?.toFixed(2)}
                      </td>
                      <td>{new Date(trade.close_time).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default TradeHistory;
