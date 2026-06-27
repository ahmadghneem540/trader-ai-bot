import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useMT5 } from '../context/MT5Context';
import {
  getMT5Account, getMT5Positions, getMT5Orders, getMT5Symbols, getMT5Tick
} from '../services/api';
import Navbar from '../components/Navbar';
import './Dashboard.css';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { isConnected, accountInfo: mt5AccountInfo, checkConnection } = useMT5();
  const [activeTab, setActiveTab] = useState('overview');
  const [accountInfo, setAccountInfo] = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [symbols, setSymbols] = useState([]);
  const [currentTick, setCurrentTick] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [isConnected]);

  const fetchData = async () => {
    try {
      if (isConnected) {
        const account = await getMT5Account();
        setAccountInfo(account);

        const pos = await getMT5Positions();
        setPositions(pos);

        const ord = await getMT5Orders();
        setOrders(ord);

        const sym = await getMT5Symbols();
        setSymbols(sym);

        try {
          const tick = await getMT5Tick('XAUUSD');
          setCurrentTick(tick);
        } catch {}
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <Navbar />
      <div className="dashboard-content">
        <div className="dashboard-header">
          <h1>TraderAI Dashboard</h1>
        </div>

        <div className="dashboard-tabs">
          <button 
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`} 
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button 
            className={`tab-btn ${activeTab === 'positions' ? 'active' : ''}`} 
            onClick={() => setActiveTab('positions')}
          >
            Positions
          </button>
          <button 
            className={`tab-btn ${activeTab === 'orders' ? 'active' : ''}`} 
            onClick={() => setActiveTab('orders')}
          >
            Orders
          </button>
          <button 
            className={`tab-btn ${activeTab === 'market' ? 'active' : ''}`} 
            onClick={() => setActiveTab('market')}
          >
            Market Watch
          </button>
        </div>

        {activeTab === 'overview' && (
          <div className="overview-section">
            <div className="stats-grid">
              <div className="stat-card">
                <h3>MT5 Status</h3>
                <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
                  <span className="status-dot"></span>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </div>
                {isConnected && accountInfo && (
                  <div className="account-details">
                    <p>Login: {accountInfo.login}</p>
                    <p>Server: {accountInfo.server}</p>
                  </div>
                )}
              </div>

              <div className="stat-card">
                <h3>Balance</h3>
                <div className="stat-value">
                  ${accountInfo?.balance?.toFixed(2) || '0.00'}
                </div>
              </div>

              <div className="stat-card">
                <h3>Equity</h3>
                <div className="stat-value">
                  ${accountInfo?.equity?.toFixed(2) || '0.00'}
                </div>
              </div>

              <div className="stat-card">
                <h3>Profit</h3>
                <div className={`stat-value ${accountInfo?.profit >= 0 ? 'positive' : 'negative'}`}>
                  ${accountInfo?.profit?.toFixed(2) || '0.00'}
                </div>
              </div>

              <div className="stat-card">
                <h3>Margin</h3>
                <div className="stat-value">
                  ${accountInfo?.margin?.toFixed(2) || '0.00'}
                </div>
              </div>

              <div className="stat-card">
                <h3>Free Margin</h3>
                <div className="stat-value">
                  ${accountInfo?.margin_free?.toFixed(2) || '0.00'}
                </div>
              </div>

              <div className="stat-card">
                <h3>Open Positions</h3>
                <div className="stat-value">{positions.length}</div>
              </div>

              <div className="stat-card">
                <h3>Pending Orders</h3>
                <div className="stat-value">{orders.length}</div>
              </div>

              {currentTick && (
                <div className="stat-card">
                  <h3>XAUUSD</h3>
                  <div className="tick-info">
                    <p>Bid: {currentTick.bid.toFixed(2)}</p>
                    <p>Ask: {currentTick.ask.toFixed(2)}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'positions' && (
          <div className="positions-section">
            <h2>Open Positions</h2>
            {positions.length > 0 ? (
              <div className="positions-table-container">
                <table className="positions-table">
                  <thead>
                    <tr>
                      <th>Ticket</th>
                      <th>Symbol</th>
                      <th>Type</th>
                      <th>Volume</th>
                      <th>Entry</th>
                      <th>Current Price</th>
                      <th>Profit</th>
                      <th>SL</th>
                      <th>TP</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos) => (
                      <tr key={pos.ticket}>
                        <td>{pos.ticket}</td>
                        <td>{pos.symbol}</td>
                        <td>
                          <span className={`position-type ${pos.type === 0 ? 'buy' : 'sell'}`}>
                            {pos.type === 0 ? 'BUY' : 'SELL'}
                          </span>
                        </td>
                        <td>{pos.volume}</td>
                        <td>{pos.price_open.toFixed(2)}</td>
                        <td>{pos.price_current.toFixed(2)}</td>
                        <td className={`profit ${pos.profit >= 0 ? 'positive' : 'negative'}`}>
                          ${pos.profit.toFixed(2)}
                        </td>
                        <td>{pos.sl !== 0 ? pos.sl.toFixed(2) : '-'}</td>
                        <td>{pos.tp !== 0 ? pos.tp.toFixed(2) : '-'}</td>
                        <td>{new Date(pos.time * 1000).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="no-data">No open positions</div>
            )}
          </div>
        )}

        {activeTab === 'orders' && (
          <div className="orders-section">
            <h2>Pending Orders</h2>
            {orders.length > 0 ? (
              <div className="orders-table-container">
                <table className="orders-table">
                  <thead>
                    <tr>
                      <th>Ticket</th>
                      <th>Symbol</th>
                      <th>Type</th>
                      <th>Volume</th>
                      <th>Price</th>
                      <th>SL</th>
                      <th>TP</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => (
                      <tr key={order.ticket}>
                        <td>{order.ticket}</td>
                        <td>{order.symbol}</td>
                        <td>{order.type}</td>
                        <td>{order.volume_initial}</td>
                        <td>{order.price_open.toFixed(2)}</td>
                        <td>{order.sl !== 0 ? order.sl.toFixed(2) : '-'}</td>
                        <td>{order.tp !== 0 ? order.tp.toFixed(2) : '-'}</td>
                        <td>{new Date(order.time_setup * 1000).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="no-data">No pending orders</div>
            )}
          </div>
        )}

        {activeTab === 'market' && (
          <div className="market-section">
            <h2>Market Watch</h2>
            {symbols.length > 0 ? (
              <div className="market-table-container">
                <table className="market-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Description</th>
                      <th>Spread</th>
                      <th>Digits</th>
                      <th>Visible</th>
                      <th>Trade Mode</th>
                    </tr>
                  </thead>
                  <tbody>
                    {symbols.map((symbol) => (
                      <tr key={symbol.symbol}>
                        <td>{symbol.symbol}</td>
                        <td>{symbol.description}</td>
                        <td>{symbol.spread}</td>
                        <td>{symbol.digits}</td>
                        <td>{symbol.visible ? 'Yes' : 'No'}</td>
                        <td>{symbol.trade_mode}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="no-data">No symbols available</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
