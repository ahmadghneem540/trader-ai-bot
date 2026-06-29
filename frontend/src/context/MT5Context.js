import React, { createContext, useState, useEffect, useContext, useRef } from 'react';
import { getMT5Status, aiAutoTrade } from '../services/api';

const MT5Context = createContext();

export const MT5Provider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [accountInfo, setAccountInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAutoTrading, setIsAutoTrading] = useState(false);
  const [autoTradeVolume, setAutoTradeVolume] = useState(0.01);
  const [connectionStatus, setConnectionStatus] = useState({
    connected: false,
    terminal: null,
    account: null,
    server: null,
    balance: 0.0,
    equity: 0.0,
    symbol_ready: false,
    candles_ready: false,
    last_error: null,
    checks: {
      terminal_running: false,
      mt5_initialized: false,
      login_success: false,
      account_info: false,
      terminal_info: false,
      symbol_exists: false,
      candles_retrievable: false
    }
  });
  const autoTradeIntervalRef = useRef(null);

  useEffect(() => {
    checkConnection();
    // Start periodic status checking
    const intervalId = setInterval(checkConnection, 5000);
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    // If auto trading is on and not connected, turn auto trading off
    if (isAutoTrading && !isConnected) {
      setIsAutoTrading(false);
    }
    // If auto trading is on and connected, start the interval
    if (isAutoTrading && isConnected) {
      startAutoTradeInterval();
    }
    // Cleanup interval when auto trading is off
    return () => {
      if (autoTradeIntervalRef.current) {
        clearInterval(autoTradeIntervalRef.current);
      }
    };
  }, [isAutoTrading, isConnected]);

  const startAutoTradeInterval = () => {
    if (autoTradeIntervalRef.current) {
      clearInterval(autoTradeIntervalRef.current);
    }
    // Auto-trade every 5 minutes (300000 ms)
    autoTradeIntervalRef.current = setInterval(() => {
      performAutoTrade();
    }, 300000);
    // Also run immediately
    performAutoTrade();
  };

  const performAutoTrade = async () => {
    try {
      console.log('[Auto Trade] Performing auto trade');
      const result = await aiAutoTrade(autoTradeVolume, null, null, 'XAUUSD', 'H1');
      console.log('[Auto Trade] Result:', result);
    } catch (error) {
      console.error('[Auto Trade] Failed:', error);
    }
  };

  const toggleAutoTrade = () => {
    setIsAutoTrading(prev => !prev);
  };

  const checkConnection = async () => {
    try {
      const status = await getMT5Status();
      setConnectionStatus(status);
      setIsConnected(status.connected);
      
      if (status.connected && status.account_info) {
        setAccountInfo(status.account_info);
      } else {
        setAccountInfo(null);
      }
    } catch (error) {
      console.error('Failed to check MT5 connection:', error);
      setConnectionStatus(prev => ({
        ...prev,
        connected: false,
        last_error: error.message
      }));
      setIsConnected(false);
      setAccountInfo(null);
    } finally {
      setLoading(false);
    }
  };

  const connectMT5 = (login, password, server) => {
    // Actual connection is done via api, then we check status
    setTimeout(checkConnection, 1000);
  };

  const disconnectMT5 = () => {
    setIsConnected(false);
    setIsAutoTrading(false);
    setAccountInfo(null);
    setConnectionStatus(prev => ({
      ...prev,
      connected: false,
      symbol_ready: false,
      candles_ready: false
    }));
  };

  const isFullyConnected = () => {
    return connectionStatus.connected && 
           connectionStatus.symbol_ready && 
           connectionStatus.candles_ready;
  };

  return (
    <MT5Context.Provider
      value={{
        isConnected,
        accountInfo,
        loading,
        connectionStatus,
        isAutoTrading,
        autoTradeVolume,
        setAutoTradeVolume,
        toggleAutoTrade,
        checkConnection,
        connectMT5,
        disconnectMT5,
        setIsConnected,
        setAccountInfo,
        isFullyConnected
      }}
    >
      {children}
    </MT5Context.Provider>
  );
};

export const useMT5 = () => useContext(MT5Context);
