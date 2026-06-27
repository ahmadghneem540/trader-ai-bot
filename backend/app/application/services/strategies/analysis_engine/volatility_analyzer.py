from dataclasses import dataclass
from typing import List, Dict, Any
from app.application.services.strategies.indicators import calculate_atr

@dataclass
class AnalysisResult:
    decision: str  # 'buy', 'sell', 'wait'
    confidence: float  # 0-100
    metadata: Dict[str, Any] = None


class VolatilityAnalyzer:
    def __init__(self):
        self.name = "Volatility Analyzer"

    def analyze(self, candles: List[Dict[str, Any]], spread: float = 0.0) -> AnalysisResult:
        if len(candles) < 20:
            return AnalysisResult(
                decision='wait',
                confidence=0,
                metadata={'reason': 'Insufficient data'}
            )
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        atr = calculate_atr(highs, lows, closes, 14)
        latest_atr = atr[-1] if atr else None
        
        if latest_atr is None:
            return AnalysisResult(
                decision='wait',
                confidence=0,
                metadata={'reason': 'ATR not ready'}
            )
        
        # Calculate market speed based on recent candle ranges
        recent_ranges = [h - l for h, l in zip(highs[-10:], lows[-10:])]
        avg_recent_range = sum(recent_ranges)/len(recent_ranges)
        
        # Normalize volatility
        if avg_recent_range > latest_atr *1.5:
            market_speed = "High"
            confidence =70
        elif avg_recent_range < latest_atr *0.5:
            market_speed = "Low"
            confidence=50
        else:
            market_speed = "Normal"
            confidence=80
        
        # Check spread
        spread_filter_ok = spread < latest_atr *0.3
        
        if not spread_filter_ok:
            confidence = max(0, confidence -30)
        
        return AnalysisResult(
            decision='wait',  # volatility doesn't give direction
            confidence=confidence,
            metadata={
                'atr': latest_atr,
                'spread': spread,
                'market_speed': market_speed,
                'spread_ok': spread_filter_ok
            }
        )
