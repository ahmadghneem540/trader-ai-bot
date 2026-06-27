import React from 'react';
import { Link } from 'react-router-dom';
import { useMT5 } from '../context/MT5Context';
import './Navbar.css';

function Navbar() {
  const { isConnected, accountInfo } = useMT5();

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">TraderAI</Link>
      </div>
      <div className="navbar-links">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/mt5-connection">MT5 Connection</Link>
        <Link to="/chart">Gold Chart</Link>
        <Link to="/positions">Open Positions</Link>
        <Link to="/history">Trade History</Link>
        <Link to="/strategy">Strategy Settings</Link>
        <Link to="/logs">Logs</Link>
        <Link to="/debug">Debug Console</Link>
      </div>
      <div className="mt5-status">
        {isConnected ? (
          <div className="status-connected">
            <span className="status-dot"></span>
            {accountInfo?.login ? `Connected: ${accountInfo.login}` : 'Connected'}
          </div>
        ) : (
          <div className="status-disconnected">
            <span className="status-dot"></span>
            Disconnected
          </div>
        )}
      </div>
    </nav>
  );
}

export default Navbar;
