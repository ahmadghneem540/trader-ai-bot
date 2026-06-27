import React, { createContext, useState, useEffect, useContext } from 'react';
import { getMT5Status } from '../services/api';

const MT5Context = createContext();

export const MT5Provider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [accountInfo, setAccountInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkConnection();
  }, []);

  const checkConnection = async () => {
    try {
      const status = await getMT5Status();
      setIsConnected(status.connected);
      if (status.connected) {
        setAccountInfo(status.account_info);
      }
    } catch (error) {
      console.error('Failed to check MT5 connection:', error);
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
    setAccountInfo(null);
  };

  return (
    <MT5Context.Provider
      value={{
        isConnected,
        accountInfo,
        loading,
        checkConnection,
        connectMT5,
        disconnectMT5,
        setIsConnected,
        setAccountInfo,
      }}
    >
      {children}
    </MT5Context.Provider>
  );
};

export const useMT5 = () => useContext(MT5Context);
