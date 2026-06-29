from typing import Optional, Dict, Any
from app.application.services.strategies.base import StrategyBase, Signal
from app.application.services.strategies.indicators import calculate_atr
from app.application.services.ai_service import ai_service
import asyncio


class AIStrategy(StrategyBase):
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.name = "AIStrategy"
        self.risk_reward_ratio = self.parameters.get("risk_reward_ratio", 2.0)
        self.atr_period = self.parameters.get("atr_period", 14)
        self.min_confidence = self.parameters.get("min_confidence", 0.7)

    def generate_signal(self, candles: list, current_price: float) -> Optional[Signal]:
        if len(candles) < 50:
            return None

        # Get symbol name
        symbol_name = 'unknown'
        if len(candles) > 0:
            if isinstance(candles[-1], dict):
                symbol_name = candles[-1].get('symbol_name', 'XAUUSD')
            elif hasattr(candles[-1], 'symbol') and candles[-1].symbol and hasattr(candles[-1].symbol, 'name'):
                symbol_name = candles[-1].symbol.name
            else:
                symbol_name = 'XAUUSD'

        try:
            # Run async AI analysis synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            analysis = loop.run_until_complete(
                ai_service.analyze_candles(symbol_name, "H1", candles)
            )
            loop.close()

            confidence = analysis.get('confidence', 0)
            if confidence < self.min_confidence:
                return None

            trend = analysis.get('trend', '')
            if trend == 'bullish':
                return Signal(
                    signal_type='buy',
                    symbol=symbol_name,
                    price=current_price,
                    confidence=confidence,
                    metadata=analysis
                )
            elif trend == 'bearish':
                return Signal(
                    signal_type='sell',
                    symbol=symbol_name,
                    price=current_price,
                    confidence=confidence,
                    metadata=analysis
                )

            return None
        except Exception as e:
            return None

    def validate_entry(self, signal: Signal, candles: list) -> bool:
        if not signal or signal.confidence < self.min_confidence:
            return False
        return True

    def validate_exit(self, position: dict, current_candle: dict) -> tuple[bool, str]:
        position_type = position.get('type', 'buy')
        sl = position.get('sl')
        tp = position.get('tp')
        
        if isinstance(current_candle, dict):
            current_price = current_candle.get('close', 0.0)
        else:
            current_price = current_candle.close if hasattr(current_candle, 'close') else 0.0

        if not sl or not tp:
            return False, 'no sl/tp'
        
        if position_type == 'buy':
            if current_price <= sl:
                return True, 'sl'
            if current_price >= tp:
                return True, 'tp'
        elif position_type == 'sell':
            if current_price >= sl:
                return True, 'sl'
            if current_price <= tp:
                return True, 'tp'
        return False, ''

    def calculate_stop_loss(self, entry_price: float, direction: str, candles: list) -> float:
        highs, lows, closes = [], [], []
        for c in candles:
            if isinstance(c, dict):
                highs.append(c.get('high', 0.0))
                lows.append(c.get('low', 0.0))
                closes.append(c.get('close', 0.0))
            else:
                highs.append(c.high)
                lows.append(c.low)
                closes.append(c.close)

        atr = calculate_atr(highs, lows, closes, self.atr_period)
        last_atr = atr[-1] if (atr and len(atr) > 0 and atr[-1] is not None) else entry_price * 0.01
        if direction == 'buy':
            return entry_price - (2 * last_atr)
        else:
            return entry_price + (2 * last_atr)

    def calculate_take_profit(self, entry_price: float, direction: str, candles: list) -> float:
        sl = self.calculate_stop_loss(entry_price, direction, candles)
        if direction == 'buy':
            risk = entry_price - sl
            return entry_price + (self.risk_reward_ratio * risk)
        else:
            risk = sl - entry_price
            return entry_price - (self.risk_reward_ratio * risk)
