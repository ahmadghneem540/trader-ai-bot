from dataclasses import dataclass
from typing import List, Dict, Any
from app.application.services.strategies.indicators import (
    calculate_ema,
    calculate_sma
)

@dataclass
class AnalysisResult:
    decision: str  # 'buy', 'sell', 'wait'
    confidence: float  # 0-100
    metadata: Dict[str, Any] = None


class TrendAnalyzer:
    def __init__(self):
        self.name = "Trend Analyzer"

    def analyze(self, candles: List[Dict[str, Any]]) -> AnalysisResult:
        if len(candles) < 200:
            return AnalysisResult(
                decision='wait',
                confidence=0,
                metadata={'reason': 'Insufficient data for trend analysis'}
            )
        
        closes = [candle['close'] for candle in candles]
        
        # Calculate indicators
        ema50 = calculate_ema(closes, 50)
        ema200 = calculate_ema(closes, 200)
        sma200 = calculate_sma(closes, 200)
        
        current_idx = -1
        current_price = closes[current_idx]
        
        # Get latest indicator values
        latest_ema50 = ema50[current_idx]
        latest_ema200 = ema200[current_idx]
        latest_sma200 = sma200[current_idx]
        
        if None in [latest_ema50, latest_ema200, latest_sma200]:
            return AnalysisResult(
                decision='wait',
                confidence=0,
                metadata={'reason': 'Indicators not ready'}
            )
        
        # Determine trend direction
        trend = 'wait'
        confidence = 0
        
        # EMA50 and EMA200 relationship
        ema_trend_up = latest_ema50 > latest_ema200
        ema_trend_down = latest_ema50 < latest_ema200
        
        # Price relative to EMA200 and SMA200
        price_above_ema200 = current_price > latest_ema200
        price_above_sma200 = current_price > latest_sma200
        price_below_ema200 = current_price < latest_ema200
        price_below_sma200 = current_price < latest_sma200
        
        # Check trend strength by comparing last 50 candles
        trend_strength = 0
        for i in range(max(0, len(candles)-50), len(candles)):
            if ema50[i] is not None and ema200[i] is not None:
                if ema50[i] > ema200[i]:
                    trend_strength +=1
                elif ema50[i] < ema200[i]:
                    trend_strength -=1
        
        if ema_trend_up and price_above_ema200 and price_above_sma200:
            trend = 'buy'
            confidence = 50  # base confidence
            
            # Increase confidence based on trend strength
            if trend_strength > 30:
                confidence += 30
            elif trend_strength > 15:
                confidence += 20
            
            # Price above EMA50?
            if current_price > latest_ema50:
                confidence += 10
                
        elif ema_trend_down and price_below_ema200 and price_below_sma200:
            trend = 'sell'
            confidence =50
            
            if trend_strength < -30:
                confidence +=30
            elif trend_strength < -15:
                confidence +=20
            
            if current_price < latest_ema50:
                confidence +=10
        
        confidence = min(max(confidence,0),100)
        
        return AnalysisResult(
            decision=trend,
            confidence=confidence,
            metadata={
                'ema50': latest_ema50,
                'ema200': latest_ema200,
                'sma200': latest_sma200,
                'trend_strength': trend_strength,
                'current_price': current_price
            }
        )
