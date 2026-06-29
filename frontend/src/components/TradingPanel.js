import React, { useState } from 'react';
import { openMT5Buy, openMT5Sell, closeAllMT5Positions, aiAutoTrade } from '../services/api';
import './TradingPanel.css';

function TradingPanel({ currentTick, accountInfo, onTradeSuccess }) {
  const [volume, setVolume] = useState(0.01);
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);

  const handleBuy = async () => {
    setIsLoading(true);
    try {
      await openMT5Buy(
        volume,
        sl ? parseFloat(sl) : null,
        tp ? parseFloat(tp) : null
      );
      onTradeSuccess && onTradeSuccess();
    } catch (error) {
      console.error('Failed to open buy position:', error);
      alert('Failed to open buy position: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSell = async () => {
    setIsLoading(true);
    try {
      await openMT5Sell(
        volume,
        sl ? parseFloat(sl) : null,
        tp ? parseFloat(tp) : null
      );
      onTradeSuccess && onTradeSuccess();
    } catch (error) {
      console.error('Failed to open sell position:', error);
      alert('Failed to open sell position: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseAll = async () => {
    setIsLoading(true);
    try {
      await closeAllMT5Positions();
      onTradeSuccess && onTradeSuccess();
    } catch (error) {
      console.error('Failed to close all positions:', error);
      alert('Failed to close all positions: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  const handleAiAutoTrade = async () => {
    setIsAiLoading(true);
    try {
      const result = await aiAutoTrade(
        volume,
        sl ? parseFloat(sl) : null,
        tp ? parseFloat(tp) : null
      );
      setAiAnalysis(result.data);
      if (result.success) {
        alert(`AI Auto-Trade executed! Action: ${result.data?.action || 'None'}`);
      } else {
        alert('AI Auto-Trade failed: ' + result.message);
      }
      onTradeSuccess && onTradeSuccess();
    } catch (error) {
      console.error('AI Auto-Trade failed:', error);
      alert('AI Auto-Trade failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsAiLoading(false);
    }
  };

  return (
    <div className="trading-panel">
      <h3>Trading Panel</h3>
      
      {currentTick && (
        <div className="price-display">
          <div className="price-item">
            <span className="price-label">Bid</span>
            <span className="price-value bid">{currentTick.bid?.toFixed(2)}</span>
          </div>
          <div className="price-item">
            <span className="price-label">Ask</span>
            <span className="price-value ask">{currentTick.ask?.toFixed(2)}</span>
          </div>
          <div className="price-item">
            <span className="price-label">Spread</span>
            <span className="price-value spread">{((currentTick.ask || 0) - (currentTick.bid || 0)).toFixed(2)}</span>
          </div>
        </div>
      )}

      {accountInfo && (
        <div className="account-display">
          <div className="account-item">
            <span className="account-label">Balance</span>
            <span className="account-value">${accountInfo.balance?.toFixed(2)}</span>
          </div>
          <div className="account-item">
            <span className="account-label">Equity</span>
            <span className="account-value">${accountInfo.equity?.toFixed(2)}</span>
          </div>
        </div>
      )}

      <div className="trading-form">
        <div className="form-group">
          <label>Lot Size</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
          />
        </div>
        <div className="form-group">
          <label>Stop Loss</label>
          <input
            type="number"
            step="0.01"
            placeholder="Optional"
            value={sl}
            onChange={(e) => setSl(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Take Profit</label>
          <input
            type="number"
            step="0.01"
            placeholder="Optional"
            value={tp}
            onChange={(e) => setTp(e.target.value)}
          />
        </div>
        <div className="button-group">
          <button 
            className="btn-buy" 
            onClick={handleBuy} 
            disabled={isLoading}
          >
            Buy
          </button>
          <button 
            className="btn-sell" 
            onClick={handleSell} 
            disabled={isLoading}
          >
            Sell
          </button>
        </div>
        <button 
          className="btn-ai-trade" 
          onClick={handleAiAutoTrade} 
          disabled={isAiLoading || isLoading}
        >
          {isAiLoading ? 'AI Analyzing...' : 'AI Auto-Trade'}
        </button>
        <button 
          className="btn-close-all" 
          onClick={handleCloseAll} 
          disabled={isLoading}
        >
          Close All
        </button>
        {aiAnalysis && (
          <div className="ai-analysis">
            <h4>AI Analysis:</h4>
            <p><strong>Trend:</strong> {aiAnalysis.analysis?.trend}</p>
            <p><strong>Confidence:</strong> {aiAnalysis.analysis?.confidence}%</p>
            <p><strong>Reason:</strong> {aiAnalysis.analysis?.reason}</p>
            <p><strong>Action:</strong> {aiAnalysis.action || 'No trade'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default TradingPanel;
