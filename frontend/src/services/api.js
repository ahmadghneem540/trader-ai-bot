import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to unwrap GenericResponse
const unwrapResponse = (response) => {
  const data = response.data;
  if (data.success) {
    return data.data;
  } else {
    const error = new Error(data.message || 'Request failed');
    error.response = { data: data.error || data };
    throw error;
  }
};

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Auth
export const login = async (username, password) => {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  const response = await api.post('/auth/login', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  return response.data;
};

export const register = async (userData) => {
  const response = await api.post('/auth/register', userData);
  return response.data;
};

export const getMe = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

// Market Data
export const getSymbols = async () => {
  const response = await api.get('/symbols');
  return response.data;
};

export const getCandles = async (symbolName, timeframe) => {
  const response = await api.get(`/market-data/candles/${symbolName}?timeframe=${timeframe}`);
  return response.data;
};

export const getCurrentTick = async (symbolName) => {
  const response = await api.get(`/market-data/tick/${symbolName}`);
  return response.data;
};

// Trading
export const openBuyOrder = async (data) => {
  const response = await api.post('/trading/buy', data);
  return response.data;
};

export const openSellOrder = async (data) => {
  const response = await api.post('/trading/sell', data);
  return response.data;
};

export const closePosition = async (data) => {
  const response = await api.post('/trading/close', data);
  return response.data;
};

export const modifySLTP = async (data) => {
  const response = await api.post('/trading/modify-sl-tp', data);
  return response.data;
};

export const getOpenPositions = async () => {
  const response = await api.get('/trading/positions/open');
  return response.data;
};

export const getOrders = async () => {
  const response = await api.get('/trading/orders');
  return response.data;
};

// Strategy
export const getAccountOverview = async (accountId) => {
  const response = await api.get(`/strategy/account-overview/${accountId}`);
  return response.data;
};

export const getStrategyConfig = async (accountId) => {
  const response = await api.get(`/strategy/config/${accountId}`);
  return response.data;
};

export const updateStrategyConfig = async (accountId, data) => {
  const response = await api.put(`/strategy/config/${accountId}`, data);
  return response.data;
};

export const botControl = async (action) => {
  const response = await api.post('/strategy/control', { action });
  return response.data;
};

export const getLogs = async (accountId, limit = 100) => {
  const response = await api.get(`/strategy/logs/${accountId}?limit=${limit}`);
  return response.data;
};

// Backtest
export const listStrategies = async () => {
  const response = await api.get('/backtest/strategies/list');
  return response.data;
};

export const runBacktest = async (data) => {
  const response = await api.post('/backtest/run', data);
  return response.data;
};

export const getBacktestResults = async (skip = 0, limit = 100) => {
  const response = await api.get(`/backtest/results?skip=${skip}&limit=${limit}`);
  return response.data;
};

export const getBacktestById = async (backtestId) => {
  const response = await api.get(`/backtest/${backtestId}`);
  return response.data;
};

export const getBacktestTrades = async (backtestId) => {
  const response = await api.get(`/backtest/${backtestId}/trades`);
  return response.data;
};

// Strategy - Accounts
export const getAccounts = async () => {
  const response = await api.get('/strategy/accounts');
  return response.data;
};

// Health
export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// MT5
export const connectMT5 = async (login, password, server) => {
  const response = await api.post('/mt5/connect', { login, password, server });
  return response.data; // connect returns debug info in data, no unwrap
};

export const disconnectMT5 = async () => {
  const response = await api.post('/mt5/disconnect');
  return unwrapResponse(response);
};

export const getMT5Status = async () => {
  const response = await api.get('/mt5/status');
  return unwrapResponse(response);
};

export const getMT5DetailedStatus = async () => {
  const response = await api.get('/mt5/detailed-status');
  return unwrapResponse(response);
};

export const getMT5Account = async () => {
  const response = await api.get('/mt5/account');
  return unwrapResponse(response);
};

export const getMT5Positions = async () => {
  const response = await api.get('/mt5/positions');
  return unwrapResponse(response);
};

export const getMT5History = async (days = 30) => {
  const response = await api.get(`/mt5/history?days=${days}`);
  return unwrapResponse(response);
};

export const getMT5Candles = async (symbol, timeframe, count = 500) => {
  const response = await api.get(`/mt5/candles/${symbol}/${timeframe}?count=${count}`);
  return unwrapResponse(response);
};

export const getMT5Tick = async (symbol) => {
  const response = await api.get(`/mt5/tick/${symbol}`);
  return unwrapResponse(response);
};

export const getMT5Symbols = async () => {
  const response = await api.get('/mt5/symbols');
  return unwrapResponse(response);
};

export const getMT5Orders = async () => {
  const response = await api.get('/mt5/orders');
  return unwrapResponse(response);
};

export const openMT5Buy = async (volume, sl, tp) => {
  const response = await api.post('/mt5/trade/buy', { volume, sl, tp });
  return unwrapResponse(response);
};

export const openMT5Sell = async (volume, sl, tp) => {
  const response = await api.post('/mt5/trade/sell', { volume, sl, tp });
  return unwrapResponse(response);
};

export const closeMT5Position = async (ticket) => {
  const response = await api.post(`/mt5/trade/close/${ticket}`);
  return unwrapResponse(response);
};

export const closeAllMT5Positions = async () => {
  const response = await api.post('/mt5/trade/close-all');
  return unwrapResponse(response);
};

export const getMT5Debug = async () => {
  const response = await api.get('/mt5/debug');
  return unwrapResponse(response);
};

export const getMT5DebugLogs = async () => {
    const response = await api.get('/mt5/debug/logs');
    return unwrapResponse(response);
};

// AI Auto Trade
export const aiAutoTrade = async (volume, sl, tp, symbol = "XAUUSD", timeframe = "H1") => {
    const response = await api.post('/ai/auto-trade', { volume, sl, tp }, { params: { symbol, timeframe } });
    return response.data;
};

export default api;
