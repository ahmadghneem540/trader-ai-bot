import React, { useEffect, useState } from 'react';
import { getStrategyConfig, updateStrategyConfig, botControl } from '../services/api';
import Navbar from '../components/Navbar';
import './StrategySettings.css';

function StrategySettings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const configData = await getStrategyConfig(1); // Assume account ID 1
      setConfig(configData);
    } catch (error) {
      console.error('Failed to fetch strategy config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await updateStrategyConfig(1, config);
      alert('Strategy settings updated successfully!');
    } catch (error) {
      console.error('Failed to update config:', error);
      alert('Failed to update settings');
    }
  };

  const handleBotControl = async (action) => {
    try {
      const newConfig = await botControl(action);
      setConfig(newConfig);
      alert(`Bot ${action}ed successfully!`);
    } catch (error) {
      console.error('Failed to control bot:', error);
      alert(`Failed to ${action} bot`);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (type === 'number' ? parseFloat(value) : value)
    }));
  };

  if (loading) {
    return <div className="strategy-settings"><h1>Loading...</h1></div>;
  }

  return (
    <div className="strategy-settings">
      <Navbar />
      <h1>Strategy Settings</h1>
      
      {/* Bot Control Section */}
      <div className="settings-container">
        <div className="settings-card">
          <h2>Bot Control</h2>
          <div className="bot-controls">
            <button 
              onClick={() => handleBotControl('start')}
              disabled={config?.is_bot_active && !config?.is_paused}
              className="btn-primary"
            >
              Start Bot
            </button>
            <button 
              onClick={() => handleBotControl('stop')}
              disabled={!config?.is_bot_active}
              className="btn-danger"
            >
              Stop Bot
            </button>
            <button 
              onClick={() => handleBotControl('pause')}
              disabled={!config?.is_bot_active || config?.is_paused}
              className="btn-warning"
            >
              Pause
            </button>
            <button 
              onClick={() => handleBotControl('resume')}
              disabled={!config?.is_paused}
              className="btn-success"
            >
              Resume
            </button>
          </div>
          <div className="bot-status">
            Status: {config?.is_bot_active ? (config?.is_paused ? 'Paused' : 'Active') : 'Stopped'}
          </div>
        </div>
      </div>

      <form onSubmit={handleUpdate} className="settings-container">
        {/* Strategy Selection */}
        <div className="settings-card">
          <h2>Strategy Configuration</h2>
          
          <div className="form-group">
            <label>Selected Strategy</label>
            <select
              name="selected_strategy"
              value={config?.selected_strategy || ''}
              onChange={handleChange}
            >
              <option value="EMATrendStrategy">EMA Trend Strategy</option>
              <option value="AIStrategy">AI Powered Strategy (Gemini)</option>
              <option value="GoldAutonomousStrategy">Gold Autonomous Strategy</option>
            </select>
          </div>

          <div className="form-group">
            <label>Lot Size</label>
            <input
              type="number"
              step="0.01"
              name="lot_size"
              value={config?.lot_size || 0}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label>Max Daily Loss ($)</label>
            <input
              type="number"
              name="max_daily_loss"
              value={config?.max_daily_loss || 0}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label>Max Weekly Loss ($)</label>
            <input
              type="number"
              name="max_weekly_loss"
              value={config?.max_weekly_loss || 0}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label>Max Open Trades</label>
            <input
              type="number"
              name="max_open_trades"
              value={config?.max_open_trades || 0}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label>Timeframe</label>
            <select
              name="schedule_timeframe"
              value={config?.schedule_timeframe || ''}
              onChange={handleChange}
            >
              <option value="M1">M1</option>
              <option value="M5">M5</option>
              <option value="M15">M15</option>
              <option value="M30">M30</option>
              <option value="H1">H1</option>
              <option value="H4">H4</option>
              <option value="D1">D1</option>
            </select>
          </div>
        </div>

        {/* Risk Management */}
        <div className="settings-card">
          <h2>Risk Management</h2>
          
          <div className="form-group">
            <label>
              <input
                type="checkbox"
                name="safety_mode"
                checked={config?.safety_mode || false}
                onChange={handleChange}
              />
              Safety Mode (Demo Only)
            </label>
          </div>
        </div>

        {/* Trailing Stop & Breakeven */}
        <div className="settings-card">
          <h2>Trade Management</h2>
          
          <div className="form-group">
            <label>
              <input
                type="checkbox"
                name="trailing_stop_enabled"
                checked={config?.trailing_stop_enabled || false}
                onChange={handleChange}
              />
              Enable Trailing Stop
            </label>
            {config?.trailing_stop_enabled && (
              <input
                type="number"
                name="trailing_stop_pips"
                placeholder="Trailing Stop Pips"
                value={config?.trailing_stop_pips || 0}
                onChange={handleChange}
                style={{ marginTop: '8px' }}
              />
            )}
          </div>

          <div className="form-group">
            <label>
              <input
                type="checkbox"
                name="breakeven_enabled"
                checked={config?.breakeven_enabled || false}
                onChange={handleChange}
              />
              Enable Breakeven
            </label>
            {config?.breakeven_enabled && (
              <input
                type="number"
                name="breakeven_pips"
                placeholder="Breakeven Pips"
                value={config?.breakeven_pips || 0}
                onChange={handleChange}
                style={{ marginTop: '8px' }}
              />
            )}
          </div>
        </div>

        <div className="settings-card">
          <button type="submit" className="btn-primary">Save Settings</button>
        </div>
      </form>
    </div>
  );
}

export default StrategySettings;
