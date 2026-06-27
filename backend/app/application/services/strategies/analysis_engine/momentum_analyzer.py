from dataclasses import dataclass
from typing import List, Dict, Any
from app.application.services.strategies.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_atr
)

@dataclass
class AnalysisResult:
    decision: str  # 'buy', 'sell', 'wait'
    confidence: float  # 0-100
    metadata: Dict[str, Any] = None


class MomentumAnalyzer:
    def __init__(self):
        self.name = "Momentum Analyzer"

    def analyze(self, candles: List[Dict[str, Any]]) -> AnalysisResult:
        if len(candles) < 50:
            return AnalysisResult(
                decision='wait',
                confidence=0,
                metadata={'reason': 'Insufficient data'}
            )
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        rsi = calculate_rsi(closes, 14)
        macd_line, signal_line, histogram = calculate_macd(closes)
        atr = calculate_atr(highs, lows, closes, 14)
        
        current_idx = -1
        current_price = closes[current_idx]
        
        latest_rsi = rsi[current_idx]
        latest_macd = macd_line[current_idx]
        latest_signal = signal_line[current_idx]
        latest_hist = histogram[current_idx]
        latest_atr = atr[current_idx]
        
        if None in [latest_rsi, latest_macd, latest_signal, latest_atr]:
            return AnalysisResult(
                decision='wait',
                confidence=0,
                metadata={'reason': 'Indicators not ready'}
            )
        
        decision = 'wait'
        confidence = 0
        
        # RSI Conditions
        rsi_buy_signal = latest_rsi < 30
        rsi_sell_signal = latest_rsi >70
        
        # MACD Conditions
        macd_buy_signal = latest_macd > latest_signal and latest_hist > 0
        macd_sell_signal = latest_macd < latest_signal and latest_hist <0
        
        if rsi_buy_signal and macd_buy_signal:
            decision = 'buy'
            confidence += 60
            if latest_rsi <25:
                confidence +=20
            if latest_hist > histogram[current_idx-1]:
                confidence +=10
        elif rsi_sell_signal and macd_sell_signal:
            decision='sell'
            confidence +=60
            if latest_rsi>75:
                confidence +=20
            if latest_hist < histogram[current_idx-1]:
                confidence +=10
        
        confidence = min(max(confidence,0),100)
        
        return AnalysisResult(
            decision=decision,
            confidence=confidence,
            metadata={
                'rsi': latest_rsi,
                'macd_line': latest_macd,
                'signal_line': latest_signal,
                'histogram': latest_hist,
                'atr': latest_atr
            }
        )
