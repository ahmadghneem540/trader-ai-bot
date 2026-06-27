from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:
    signal_type: str  # 'buy', 'sell', 'hold'
    symbol: str
    price: float
    confidence: float = 1.0
    metadata: Dict[str, Any] = None


class StrategyBase(ABC):
    """Base class for all trading strategies."""

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        self.parameters = parameters or {}
        self.name = "BaseStrategy"

    @abstractmethod
    def generate_signal(self, candles: list, current_price: float) -> Optional[Signal]:
        """Generate a trading signal based on current market data."""
        pass

    @abstractmethod
    def validate_entry(self, signal: Signal, candles: list) -> bool:
        """Validate if entry conditions are met."""
        pass

    @abstractmethod
    def validate_exit(self, position: dict, current_candle: dict) -> tuple[bool, str]:
        """Validate if exit conditions are met. Returns (should_exit, reason)."""
        pass

    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, direction: str, candles: list) -> float:
        """Calculate stop loss price."""
        pass

    @abstractmethod
    def calculate_take_profit(self, entry_price: float, direction: str, candles: list) -> float:
        """Calculate take profit price."""
        pass
