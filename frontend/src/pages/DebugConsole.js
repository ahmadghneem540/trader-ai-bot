import React, { useState, useEffect, useRef } from 'react';
import { getMT5Debug, getMT5DebugLogs } from '../services/api';
import './DebugConsole.css';

function DebugConsole() {
  const [debugInfo, setDebugInfo] = useState(null);
  const [logs, setLogs] = useState([]);
  const logsContainerRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const debugData = await getMT5Debug();
        setDebugInfo(debugData.debug_info);
        const logsData = await getMT5DebugLogs();
        setLogs(logsData.data);
      } catch (error) {
        console.error('Failed to fetch debug data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000); // Update every 2 seconds

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const getLogColor = (level) => {
    switch (level.toUpperCase()) {
      case 'SUCCESS':
        return { primary: '#4ade80', bg: 'rgba(74, 222, 128, 0.1)' };
      case 'ERROR':
        return { primary: '#f87171', bg: 'rgba(248, 113, 113, 0.1)' };
      case 'WARNING':
        return { primary: '#fbbf24', bg: 'rgba(251, 191, 36, 0.1)' };
      case 'INFO':
      default:
        return { primary: '#60a5fa', bg: 'rgba(96, 165, 250, 0.1)' };
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 });
  };

  const handleExportLogs = () => {
    const logContent = JSON.stringify(logs, null, 2);
    const blob = new Blob([logContent], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mt5-debug-logs-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="debug-console">
      <h1>Debug Console</h1>

      {debugInfo && (
        <div className="debug-info-section">
          <h2>Debug Information</h2>
          <div className="debug-info-grid">
            <div className="debug-item">
              <span className="debug-label">Initialize Result:</span>
              <span className="debug-value" style={{ color: debugInfo.initialize_result ? '#4ade80' : '#f87171' }}>
                {debugInfo.initialize_result ? 'Success' : 'Failed'}
              </span>
            </div>
            <div className="debug-item">
              <span className="debug-label">Login Result:</span>
              <span className="debug-value" style={{ color: debugInfo.login_result ? '#4ade80' : '#f87171' }}>
                {debugInfo.login_result ? 'Success' : 'Failed'}
              </span>
            </div>
            <div className="debug-item">
              <span className="debug-label">Connection Time:</span>
              <span className="debug-value">{debugInfo.connection_time}s</span>
            </div>
            <div className="debug-item">
              <span className="debug-label">Account Number:</span>
              <span className="debug-value">{debugInfo.account_info?.login}</span>
            </div>
            <div className="debug-item">
              <span className="debug-label">Server:</span>
              <span className="debug-value">{debugInfo.account_info?.server}</span>
            </div>
            <div className="debug-item">
              <span className="debug-label">MT5 Version:</span>
              <span className="debug-value">{JSON.stringify(debugInfo.version)}</span>
            </div>
            <div className="debug-item">
              <span className="debug-label">XAUUSD Selected:</span>
              <span className="debug-value" style={{ color: debugInfo.xauusd_status?.selected ? '#4ade80' : '#f87171' }}>
                {debugInfo.xauusd_status?.selected ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="logs-section">
        <div className="logs-header">
          <h2>Logs</h2>
          <div className="logs-controls">
            <label className="auto-scroll-label">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
            <button className="export-btn" onClick={handleExportLogs}>
              Export Logs
            </button>
          </div>
        </div>
        <div className="logs-container" ref={logsContainerRef}>
          {logs.map((log, index) => {
            const colors = getLogColor(log.level);
            return (
              <div key={index} className="log-item" style={{ borderLeftColor: colors.primary, backgroundColor: colors.bg }}>
                <div className="log-header">
                  <span className="log-step">[Step {log.step}]</span>
                  <span className="log-component">{log.component}</span>
                  <span className="log-function">{log.function}</span>
                  <span className="log-timestamp">{formatTimestamp(log.timestamp)}</span>
                </div>
                <div className="log-message" style={{ color: colors.primary }}>
                  {log.description}
                </div>
                {log.execution_time_ms && (
                  <div className="log-exec-time">
                    Execution time: {log.execution_time_ms.toFixed(2)} ms
                  </div>
                )}
                {log.result !== undefined && log.result !== null && (
                  <div className="log-data">
                    <pre>{JSON.stringify(log.result, null, 2)}</pre>
                  </div>
                )}
                {log.mt5_last_error && (
                  <div className="log-error">
                    <span className="error-label">MT5 Last Error:</span>
                    <pre>{JSON.stringify(log.mt5_last_error, null, 2)}</pre>
                  </div>
                )}
                {log.exception && (
                  <div className="log-exception">
                    <span className="exception-label">Exception:</span>
                    <pre>{log.exception}</pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default DebugConsole;
