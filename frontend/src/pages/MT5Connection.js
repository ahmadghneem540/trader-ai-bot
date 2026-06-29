import React, { useState, useEffect } from 'react';
import { connectMT5, disconnectMT5, getMT5DebugLogs } from '../services/api';
import { useMT5 } from '../context/MT5Context';
import Navbar from '../components/Navbar';
import './MT5Connection.css';

function MT5Connection() {
  const {
    isConnected,
    accountInfo,
    setIsConnected,
    setAccountInfo,
    isAutoTrading,
    autoTradeVolume,
    setAutoTradeVolume,
    toggleAutoTrade,
  } = useMT5();
  const [login, setLogin] = useState('108894781');
  const [password, setPassword] = useState('Hf_4lkls');
  const [server, setServer] = useState('MetaQuotes-Demo');
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState([]);

  const fetchLogs = async () => {
    try {
      const logsData = await getMT5DebugLogs();
      setLogs(logsData);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleConnect = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const result = await connectMT5(parseInt(login), password, server);
      if (result.success) {
        setIsConnected(true);
        setAccountInfo(result.debug_info?.account_info);
        alert('Connected successfully!');
      }
      fetchLogs(); // Fetch logs right after connect attempt
    } catch (error) {
      console.error('Connection failed:', error);
      const errorDetail = error.response?.data?.detail || error.message;
      alert('Connection failed: ' + errorDetail);
      fetchLogs(); // Fetch logs even if connection failed
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      await disconnectMT5();
      setIsConnected(false);
      setAccountInfo(null);
      alert('Disconnected successfully!');
      fetchLogs(); // Fetch logs after disconnect
    } catch (error) {
      console.error('Disconnect failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const result = await connectMT5(parseInt(login), password, server);
      if (result.success) {
        alert('Test connection successful!');
        await disconnectMT5();
        setIsConnected(false);
        setAccountInfo(null);
      }
      fetchLogs(); // Fetch logs after test connection
    } catch (error) {
      console.error('Test connection failed:', error);
      const errorDetail = error.response?.data?.detail || error.message;
      alert('Test connection failed: ' + errorDetail);
      fetchLogs(); // Fetch logs even if test connection failed
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mt5-connection">
      <Navbar />
      <h1>MT5 Connection</h1>
      
      <div className="connection-container">
        {!isConnected ? (
          <form onSubmit={handleConnect} className="connection-form">
            <div className="form-group">
              <label>Account Login</label>
              <input
                type="number"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                placeholder="Account Login"
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
              />
            </div>
            <div className="form-group">
              <label>Broker Server</label>
              <input
                type="text"
                value={server}
                onChange={(e) => setServer(e.target.value)}
                placeholder="Broker Server"
                required
              />
            </div>
            <div className="button-group">
              <button type="submit" disabled={isLoading} className="btn-primary">
                {isLoading ? 'Connecting...' : 'Connect'}
              </button>
              <button 
                type="button" 
                onClick={handleTestConnection} 
                disabled={isLoading}
                className="btn-secondary"
              >
                Test Connection
              </button>
            </div>
          </form>
        ) : (
          <div className="account-info">
            <div className="status-badge connected">
              ● Connected
            </div>
            
            {accountInfo && (
              <div className="account-details">
                <div className="detail-row">
                  <span className="detail-label">Account Number:</span>
                  <span className="detail-value">{accountInfo.login}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Account Name:</span>
                  <span className="detail-value">{accountInfo.name}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Server:</span>
                  <span className="detail-value">{accountInfo.server}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Balance:</span>
                  <span className="detail-value">${accountInfo.balance?.toFixed(2)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Equity:</span>
                  <span className="detail-value">${accountInfo.equity?.toFixed(2)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Margin:</span>
                  <span className="detail-value">${accountInfo.margin?.toFixed(2)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Connection Status:</span>
                  <span className="detail-value status-online">Online</span>
                </div>
              </div>
            )}

            <div className="auto-trade-section">
              <h3>AI Auto-Trading</h3>
              <div className="form-group">
                <label>Auto-Trade Volume</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={autoTradeVolume}
                  onChange={(e) => setAutoTradeVolume(parseFloat(e.target.value))}
                  disabled={isAutoTrading}
                />
              </div>
              <button 
                onClick={toggleAutoTrade}
                className={`btn-auto-trade ${isAutoTrading ? 'active' : ''}`}
              >
                {isAutoTrading ? 'Stop Auto-Trading' : 'Start Auto-Trading'}
              </button>
              {isAutoTrading && (
                <div className="auto-trade-status">
                  <span className="status-dot"></span>
                  Auto-Trading Active (every 5 minutes)
                </div>
              )}
            </div>
            
            <button 
              onClick={handleDisconnect} 
              disabled={isLoading}
              className="btn-danger"
            >
              {isLoading ? 'Disconnecting...' : 'Disconnect'}
            </button>
          </div>
        )}
      </div>

      <div className="logs-section">
        <h3>Connection Logs</h3>
        <div className="logs-container">
          {logs.length === 0 ? (
            <p className="no-logs">No logs available yet</p>
          ) : (
            logs.map((log, index) => (
              <div key={index} className={`log-entry log-${log.level.toLowerCase()}`}>
                <span className="log-timestamp">{new Date(log.timestamp).toLocaleTimeString()}</span>
                <span className="log-step">[Step {log.step}]</span>
                <span className="log-function">{log.function}</span>
                <span className="log-message">{log.description}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default MT5Connection;
