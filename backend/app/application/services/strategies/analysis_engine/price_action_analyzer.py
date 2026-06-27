from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class AnalysisResult:
    decision: str  # 'buy', 'sell', 'wait'
    confidence: float  # 0-100
    metadata: Dict[str, Any] = None


class PriceActionAnalyzer:
    def __init__(self):
        self.name = "Price Action Analyzer"

    def analyze(self, candles: List[Dict[str, Any]]) -> AnalysisResult:
        if len(candles) <20:
            return AnalysisResult(
                decision='wait',
                confidence=0,
                metadata={'reason': 'Insufficient data'}
            )
        
        decision = 'wait'
        confidence=0
        metadata = {}
        
        # Look at last 5 candles
        last5 = candles[-5:]
        current_candle = last5[-1]
        prev_candle = last5[-2]
        
        # Check for engulfing patterns
        is_bullish_engulfing = (
            prev_candle['close'] < prev_candle['open'] and
            current_candle['close'] > current_candle['open'] and
            current_candle['open'] <= prev_candle['close'] and
            current_candle['close'] >= prev_candle['open']
        )
        
        is_bearish_engulfing = (
            prev_candle['close'] > prev_candle['open'] and
            current_candle['close'] < current_candle['open'] and
            current_candle['open'] >= prev_candle['close'] and
            current_candle['close'] <= prev_candle['open']
        )
        
        # Check for pin bar (small body, long wick)
        body_size = abs(current_candle['close'] - current_candle['open'])
        upper_wick = current_candle['high'] - max(current_candle['open'], current_candle['close'])
        lower_wick = min(current_candle['open'], current_candle['close']) - current_candle['low']
        
        is_pin_bar = (
            upper_wick > body_size *2 or lower_wick > body_size *2
        )
        
        if is_bullish_engulfing:
            decision = 'buy'
            confidence +=70
            metadata['pattern'] = 'Bullish Engulfing'
        elif is_bearish_engulfing:
            decision = 'sell'
            confidence +=70
            metadata['pattern'] = 'Bearish Engulfing'
        elif is_pin_bar:
            if lower_wick > upper_wick:
                decision = 'buy'
                confidence +=60
                metadata['pattern'] = 'Bullish Pin Bar'
            else:
                decision = 'sell'
                confidence +=60
                metadata['pattern'] = 'Bearish Pin Bar'
        
        # Check for breakouts
        # Get last 20 candle highs and lows
        recent_highs = [c['high'] for c in candles[-20:]]
        recent_lows = [c['low'] for c in candles[-20:]]
        
        highest_high = max(recent_highs[:-1])
        lowest_low = min(recent_lows[:-1])
        
        if current_candle['high'] > highest_high:
            if confidence < 70:
                decision = 'buy'
            confidence +=20
            metadata['breakout'] = 'Resistance Breakout'
        
        if current_candle['low'] < lowest_low:
            if confidence <70:
                decision = 'sell'
            confidence +=20
            metadata['breakout'] = 'Support Breakout'
        
        confidence = min(max(confidence,0),100)
        
        metadata.update({
            'current_candle': current_candle,
            'is_pin_bar': is_pin_bar,
            'highest_high_20': highest_high,
            'lowest_low_20': lowest_low
        })
        
        return AnalysisResult(
            decision=decision,
            confidence=confidence,
            metadata=metadata
        )
