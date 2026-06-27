from typing import Optional, Dict, Any
from datetime import datetime
from app.application.services.strategies.base import StrategyBase, Signal
from app.application.services.strategies.indicators import (
    calculate_ema, calculate_rsi, calculate_macd, calculate_atr
)


class EMATrendStrategy(StrategyBase):
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.name = "EMATrendStrategy"
        self.ema_fast_period = self.parameters.get("ema_fast_period", 50)
        self.ema_slow_period = self.parameters.get("ema_slow_period", 200)
        self.rsi_period = self.parameters.get("rsi_period", 14)
        self.rsi_buy_threshold = self.parameters.get("rsi_buy_threshold", 55)
        self.rsi_sell_threshold = self.parameters.get("rsi_sell_threshold", 45)
        self.macd_fast_period = self.parameters.get("macd_fast_period", 12)
        self.macd_slow_period = self.parameters.get("macd_slow_period", 26)
        self.macd_signal_period = self.parameters.get("macd_signal_period", 9)
        self.atr_period = self.parameters.get("atr_period", 14)
        self.risk_reward_ratio = self.parameters.get("risk_reward_ratio", 2.0)

    def generate_signal(self, candles: list, current_price: float) -> Optional[Signal]:
        if len(candles) < max(self.ema_slow_period + 10, self.macd_slow_period + self.atr_period + 10):
            return None

        closes, highs, lows = [], [], []
        for c in candles:
            if isinstance(c, dict):
                closes.append(c.get('close', 0.0))
                highs.append(c.get('high', 0.0))
                lows.append(c.get('low', 0.0))
            else:
                closes.append(c.close)
                highs.append(c.high)
                lows.append(c.low)

        ema_fast = calculate_ema(closes, self.ema_fast_period)
        ema_slow = calculate_ema(closes, self.ema_slow_period)
        rsi = calculate_rsi(closes, self.rsi_period)
        macd_line, signal_line, histogram = calculate_macd(
            closes,
            self.macd_fast_period,
            self.macd_slow_period,
            self.macd_signal_period
        )

        if (
            len(ema_fast) == 0
            or ema_fast[-1] is None
            or ema_slow[-1] is None
            or rsi[-1] is None
            or macd_line[-1] is None
            or signal_line[-1] is None
            or histogram[-1] is None
            or len(histogram) < 2
        ):
            return None

        buy_condition = (
            ema_fast[-1] > ema_slow[-1]
            and rsi[-1] > self.rsi_buy_threshold
            and histogram[-1] > 0
            and histogram[-1] > histogram[-2]
            and macd_line[-1] > signal_line[-1]
        )

        sell_condition = (
            ema_fast[-1] < ema_slow[-1]
            and rsi[-1] < self.rsi_sell_threshold
            and histogram[-1] < 0
            and histogram[-1] < histogram[-2]
            and macd_line[-1] < signal_line[-1]
        )

        symbol_name = 'unknown'
        if len(candles) > 0:
            if isinstance(candles[-1], dict):
                symbol_name = candles[-1].get('symbol_name', 'unknown')
            elif hasattr(candles[-1], 'symbol') and candles[-1].symbol and hasattr(candles[-1].symbol, 'name'):
                symbol_name = candles[-1].symbol.name
            else:
                symbol_name = 'unknown'

        if buy_condition:
            return Signal(signal_type='buy', symbol=symbol_name, price=current_price)
        elif sell_condition:
            return Signal(signal_type='sell', symbol=symbol_name, price=current_price)
        return None

    def validate_entry(self, signal: Signal, candles: list) -> bool:
        if len(candles) < 10:
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
