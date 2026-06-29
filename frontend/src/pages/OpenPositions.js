import React, { useEffect, useState } from 'react';
import { getMT5Positions, closeMT5Position } from '../services/api';
import Navbar from '../components/Navbar';
import './OpenPositions.css';

function OpenPositions() {
  const [positions, setPositions] = useState([]);
  const [isLoading, setIsLoading] = useState({});

  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const pos = await getMT5Positions();
        setPositions(pos);
      } catch (error) {
        console.error('Failed to fetch positions:', error);
      }
    };

    fetchPositions();
    const interval = setInterval(fetchPositions, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleClosePosition = async (ticket) => {
    setIsLoading(prev => ({ ...prev, [ticket]: true }));
    try {
      await closeMT5Position(ticket);
      const pos = await getMT5Positions();
      setPositions(pos);
    } catch (error) {
      console.error('Failed to close position:', error);
      alert('Failed to close position: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(prev => ({ ...prev, [ticket]: false }));
    }
  };

  return (
    <div className="open-positions">
      <Navbar />
      <h1>Open Positions</h1>
      
      {positions.length === 0 ? (
        <div className="no-positions">
          <p>No open positions</p>
        </div>
      ) : (
        <div className="positions-table-container">
          <table className="positions-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Type</th>
                <th>Symbol</th>
                <th>Volume</th>
                <th>Open Price</th>
                <th>Current Price</th>
                <th>SL</th>
                <th>TP</th>
                <th>Profit</th>
                <th>Swap</th>
                <th>Open Time</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => (
                <tr key={pos.ticket}>
                  <td className="ticket">#{pos.ticket}</td>
                  <td>
                    <span className={`position-type-badge ${pos.type === 0 ? 'buy' : 'sell'}`}>
                      {pos.type === 0 ? 'BUY' : 'SELL'}
                    </span>
                  </td>
                  <td>{pos.symbol}</td>
                  <td>{pos.volume}</td>
                  <td>{pos.price_open?.toFixed(2)}</td>
                  <td>{pos.price_current?.toFixed(2)}</td>
                  <td>{pos.sl ? pos.sl.toFixed(2) : '-'}</td>
                  <td>{pos.tp ? pos.tp.toFixed(2) : '-'}</td>
                  <td className={`profit-cell ${pos.profit >= 0 ? 'positive' : 'negative'}`}>
                    ${pos.profit?.toFixed(2)}
                  </td>
                  <td>${pos.swap?.toFixed(2)}</td>
                  <td>{new Date(pos.time * 1000).toLocaleString()}</td>
                  <td>
                    <button
                      className="close-btn"
                      onClick={() => handleClosePosition(pos.ticket)}
                      disabled={isLoading[pos.ticket]}
                    >
                      {isLoading[pos.ticket] ? 'Closing...' : 'Close'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default OpenPositions;
