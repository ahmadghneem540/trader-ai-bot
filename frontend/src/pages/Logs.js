import React from 'react';
import Navbar from '../components/Navbar';
import './Logs.css';

function Logs() {
  return (
    <div className="logs">
      <Navbar />
      <h1>Logs</h1>
      <div className="logs-container">
        <div className="logs-card">
          <h2>System Logs</h2>
          <p className="coming-soon">Logs coming soon!</p>
        </div>
      </div>
    </div>
  );
}

export default Logs;
