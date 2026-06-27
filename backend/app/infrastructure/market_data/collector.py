import MetaTrader5 as mt5
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.logging.logger import get_logger
from app.infrastructure.mt5.connector import MT5Connector
from app.infrastructure.database.repositories import (
    SymbolRepository,
    CandleRepository,
    TickRepository
)
from app.domain.models.candle import Candle
from app.domain.models.tick import Tick

logger = get_logger(__name__)


class MarketDataCollector:
    def __init__(self, mt5_connector: MT5Connector, db: Session):
        self.mt5_connector = mt5_connector
        self.db = db
        self.symbol_repo = SymbolRepository(db)
        self.candle_repo = CandleRepository(db)
        self.tick_repo = TickRepository(db)

    def get_historical_candles(
        self,
        symbol_name: str,
        timeframe: str,
        count: int = 100,
        from_time: Optional[datetime] = None,
        save_to_db: bool = True
    ) -> List[Dict[str, Any]]:
        if not self.mt5_connector.is_connected():
            raise Exception("MT5 not connected")

        # Map string timeframe to MT5 constants
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1
        }
        mt5_tf = tf_map.get(timeframe)
        if not mt5_tf:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        if from_time:
            rates = mt5.copy_rates_from(symbol_name, mt5_tf, from_time, count)
        else:
            rates = mt5.copy_rates_from_pos(symbol_name, mt5_tf, 0, count)

        if rates is None:
            logger.error(f"Failed to get historical data for {symbol_name}")
            return []

        symbol = self.symbol_repo.get_by_name(symbol_name)
        if not symbol:
            logger.error(f"Symbol {symbol_name} not found in DB")
            return []

        candles_data = []
        for rate in rates:
            candle_data = {
                "symbol_id": symbol.id,
                "timeframe": timeframe,
                "time": datetime.fromtimestamp(rate[0]),
                "open": rate[1],
                "high": rate[2],
                "low": rate[3],
                "close": rate[4],
                "tick_volume": rate[5],
                "spread": rate[6],
                "real_volume": rate[7],
            }
            candles_data.append(candle_data)

            if save_to_db:
                # Check if candle already exists
                existing = self.candle_repo.get_latest(symbol.id, timeframe)
                if not existing or existing.time < candle_data["time"]:
                    self.candle_repo.create(candle_data)

        return candles_data

    def get_current_tick(self, symbol_name: str, save_to_db: bool = True) -> Optional[Dict[str, Any]]:
        if not self.mt5_connector.is_connected():
            raise Exception("MT5 not connected")

        tick = mt5.symbol_info_tick(symbol_name)
        if tick is None:
            return None

        symbol = self.symbol_repo.get_by_name(symbol_name)
        if not symbol:
            logger.error(f"Symbol {symbol_name} not found in DB")
            return None

        tick_data = {
            "symbol_id": symbol.id,
            "time": datetime.fromtimestamp(tick.time),
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "volume_real": tick.volume_real
        }

        if save_to_db:
            self.tick_repo.create(tick_data)

        return tick_data

    def save_candle(self, symbol_id: int, candle_data: Dict[str, Any]) -> Candle:
        return self.candle_repo.create(candle_data)

    def save_tick(self, symbol_id: int, tick_data: Dict[str, Any]) -> Tick:
        return self.tick_repo.create(tick_data)
