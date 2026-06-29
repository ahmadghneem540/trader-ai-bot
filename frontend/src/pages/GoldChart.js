import React, { useEffect, useState, useRef, useCallback } from 'react';
import { getMT5Candles, getMT5Tick, getMT5Account } from '../services/api';
import TradingPanel from '../components/TradingPanel';
import Navbar from '../components/Navbar';
import { createChart } from 'lightweight-charts';
import './GoldChart.css';

function GoldChart() {
    const [timeframe, setTimeframe] = useState('H1');
    const [currentTick, setCurrentTick] = useState(null);
    const [accountInfo, setAccountInfo] = useState(null);
    const [candles, setCandles] = useState([]);
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const candlestickSeriesRef = useRef(null);

    const timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];

    console.log('[GoldChart] Component rendering');
    console.log('[GoldChart] Current timeframe:', timeframe);
    console.log('[GoldChart] Current candles:', candles);
    console.log('[GoldChart] Chart container ref:', chartContainerRef.current);
    console.log('[GoldChart] Chart ref:', chartRef.current);
    console.log('[GoldChart] Candlestick series ref:', candlestickSeriesRef.current);

    const generateDummyCandles = () => {
        const dummy = [];
        const now = Math.floor(Date.now() / 1000);
        let price = 3000; // Starting price for XAUUSD
        for (let i = 500; i >= 0; i--) {
            const time = now - (i * 3600); // H1 candles
            const volatility = 5;
            const change = (Math.random() - 0.5) * volatility;
            const open = price;
            const close = open + change;
            const high = Math.max(open, close) + Math.random() * volatility;
            const low = Math.min(open, close) - Math.random() * volatility;
            price = close;
            
            dummy.push({
                time,
                open: parseFloat(open.toFixed(2)),
                high: parseFloat(high.toFixed(2)),
                low: parseFloat(low.toFixed(2)),
                close: parseFloat(close.toFixed(2))
            });
        }
        return dummy;
    };

    const validateAndFormatCandles = useCallback((rawCandles) => {
        console.log('[GoldChart] validateAndFormatCandles called with raw data:', rawCandles);
        if (!Array.isArray(rawCandles)) {
            console.warn('[GoldChart] Invalid candles data: not an array, using dummy data');
            return generateDummyCandles();
        }

        const validCandles = rawCandles.map(c => {
            // Ensure time is a number (Unix seconds)
            let time = c.time;
            if (typeof time === 'string') {
                // Convert ISO string to Unix seconds if needed
                time = Math.floor(new Date(time).getTime() / 1000);
            } else if (typeof time === 'number' && time > 1e12) {
                // If it's in milliseconds, convert to seconds
                time = Math.floor(time / 1000);
            }

            return {
                time: Number(time),
                open: Number(c.open),
                high: Number(c.high),
                low: Number(c.low),
                close: Number(c.close)
            };
        }).filter(c => {
            // Filter out invalid candles
            return (
                typeof c.time === 'number' && !isNaN(c.time) &&
                typeof c.open === 'number' && !isNaN(c.open) &&
                typeof c.high === 'number' && !isNaN(c.high) &&
                typeof c.low === 'number' && !isNaN(c.low) &&
                typeof c.close === 'number' && !isNaN(c.close)
            );
        });

        // Sort by time ascending
        validCandles.sort((a, b) => a.time - b.time);

        // If no valid candles, use dummy data
        if (validCandles.length === 0) {
            console.warn('[GoldChart] No valid candles, using dummy data');
            return generateDummyCandles();
        }

        console.log('[GoldChart] Validated and formatted candles:', validCandles);
        console.log('[GoldChart] Number of valid candles:', validCandles.length);
        return validCandles;
    }, []);

    useEffect(() => {
        console.log('[GoldChart] fetchCandles useEffect triggered');
        const fetchCandles = async () => {
            console.log('[GoldChart] Calling getMT5Candles for XAUUSD, timeframe:', timeframe, ', count: 500');
            try {
                const candleData = await getMT5Candles('XAUUSD', timeframe, 500);
                console.log('[GoldChart] Received raw candles from API:', candleData);
                const validatedCandles = validateAndFormatCandles(candleData);
                setCandles(validatedCandles);
            } catch (error) {
                console.error('[GoldChart] Failed to fetch candles, using dummy data:', error);
                const dummyCandles = generateDummyCandles();
                setCandles(dummyCandles);
            }
        };
        fetchCandles();
    }, [timeframe, validateAndFormatCandles]);

  useEffect(() => {
        console.log('[GoldChart] Chart initialization useEffect triggered');
        if (!chartContainerRef.current) {
            console.warn('[GoldChart] Chart container ref is null, skipping chart creation');
            return;
        }
        console.log('[GoldChart] Creating chart in container:', chartContainerRef.current);
        console.log('[GoldChart] Container width:', chartContainerRef.current.clientWidth);

        // Check if chart already exists
        if (chartRef.current) {
            console.log('[GoldChart] Chart already exists, skipping creation');
            return;
        }

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight || 500,
            layout: {
                background: { color: '#222' },
                textColor: '#DDD',
            },
            grid: {
                vertLines: { color: '#444' },
                horzLines: { color: '#444' },
            },
            crosshair: {
                mode: 1,
            },
            rightPriceScale: {
                borderColor: '#444',
            },
            timeScale: {
                borderColor: '#444',
            },
        });
        console.log('[GoldChart] Chart created successfully:', chart);

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        console.log('[GoldChart] Candlestick series added successfully:', candlestickSeries);

        chartRef.current = chart;
        candlestickSeriesRef.current = candlestickSeries;

        const handleResize = () => {
            if (chartContainerRef.current && chart) {
                console.log('[GoldChart] Window resize detected, updating chart size');
                chart.applyOptions({ 
                    width: chartContainerRef.current.clientWidth,
                    height: chartContainerRef.current.clientHeight || 500
                });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            console.log('[GoldChart] Cleaning up chart');
            window.removeEventListener('resize', handleResize);
            chart.remove();
            chartRef.current = null;
            candlestickSeriesRef.current = null;
        };
    }, [chartContainerRef]);

    useEffect(() => {
        console.log('[GoldChart] Candle update useEffect triggered');
        console.log('[GoldChart] candlestickSeriesRef.current:', candlestickSeriesRef.current);
        console.log('[GoldChart] candles.length:', candles.length);
        if (candlestickSeriesRef.current && candles.length > 0) {
            // Lightweight Charts expects time in seconds since epoch for candlesticks
            const formattedData = candles.map(c => ({
                time: c.time, // Backend already returns seconds since epoch
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close
            }));
            console.log('[GoldChart] Setting chart data:', formattedData);
            candlestickSeriesRef.current.setData(formattedData);
            if (chartRef.current) {
                console.log('[GoldChart] Fitting chart content');
                chartRef.current.timeScale().fitContent();
            }
        } else {
            console.log('[GoldChart] No data to set on chart');
        }
    }, [candles]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const tick = await getMT5Tick('XAUUSD');
        setCurrentTick(tick);

        const account = await getMT5Account();
        setAccountInfo(account);
      } catch (error) {
        console.error('Failed to fetch data, using dummy data:', error);
        // Dummy tick data
        setCurrentTick({
          symbol: 'XAUUSD',
          bid: 3000.00 + Math.random() * 5,
          ask: 3000.50 + Math.random() * 5,
          last: 3000.25 + Math.random() * 5
        });
        // Dummy account info
        setAccountInfo({
          login: 12345678,
          balance: 10000.00,
          equity: 10000.00,
          profit: 0.00,
          margin: 0.00,
          margin_free: 10000.00,
          currency: 'USD',
          leverage: 100,
          trade_mode: 'DEMO'
        });
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="gold-chart">
      <Navbar />
      <div className="chart-header">
        <h1>XAUUSD - Gold vs Dollar</h1>
        <div className="timeframe-selector">
          {timeframes.map(tf => (
            <button
              key={tf}
              className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      
      <div className="chart-container">
        <div className="chart-main" ref={chartContainerRef} style={{ width: '100%', minHeight: '500px', height: '100%', position: 'relative' }}>
          {candles.length === 0 && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#888',
              fontSize: '18px',
              zIndex: 1
            }}>
              No candle data available
            </div>
          )}
        </div>
        <div className="chart-sidebar">
          <TradingPanel 
            currentTick={currentTick} 
            accountInfo={accountInfo}
            onTradeSuccess={() => {}}
          />
        </div>
      </div>
    </div>
  );
}

export default GoldChart;
