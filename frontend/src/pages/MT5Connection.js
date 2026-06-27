import React, { useState } from 'react';
import { connectMT5, disconnectMT5 } from '../services/api';
import { useMT5 } from '../context/MT5Context';
import './MT5Connection.css';

function MT5Connection() {
  const {
    isConnected,
    accountInfo,
    setIsConnected,
    setAccountInfo,
  } = useMT5();
  const [login, setLogin] = useState('108891758');
  const [password, setPassword] = useState('TcM!5aVt');
  const [server, setServer] = useState('MetaQuotes-Demo');
  const [isLoading, setIsLoading] = useState(false);

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
    } catch (error) {
      console.error('Connection failed:', error);
      const errorDetail = error.response?.data?.detail || error.message;
      alert('Connection failed: ' + errorDetail);
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
    } catch (error) {
      console.error('Test connection failed:', error);
      const errorDetail = error.response?.data?.detail || error.message;
      alert('Test connection failed: ' + errorDetail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mt5-connection">
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
    </div>
  );
}

export default MT5Connection;
