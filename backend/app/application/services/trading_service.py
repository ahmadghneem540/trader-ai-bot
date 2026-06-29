from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.logging.logger import get_logger
from app.infrastructure.mt5.connector import MT5Connector
from app.infrastructure.database.repositories import (
    SymbolRepository,
    OrderRepository,
    PositionRepository
)
from app.domain.models.order import Order
from app.domain.models.position import Position

logger = get_logger(__name__)


class TradingService:
    def __init__(self, db: Session, mt5_connector: MT5Connector):
        self.db = db
        self.mt5_connector = mt5_connector
        self.symbol_repo = SymbolRepository(db)
        self.order_repo = OrderRepository(db)
        self.position_repo = PositionRepository(db)

    def open_buy_order(
        self,
        symbol_name: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = ""
    ) -> Optional[Order]:
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot open order")
            return None

        symbol = self.symbol_repo.get_by_name(symbol_name)
        if not symbol:
            logger.error(f"Symbol {symbol_name} not found")
            return None

        # Use mt5_connector to open buy order
        result = self.mt5_connector.open_buy_order(symbol_name, volume, sl, tp)
        if not result or (hasattr(result, 'retcode') and result.retcode != 10009):  # TRADE_RETCODE_DONE is 10009
            logger.error("Order failed")
            return None

        # Save order to DB
        order_ticket = result.order if hasattr(result, 'order') else None
        if not order_ticket:
            return None

        tick = self.mt5_connector.get_tick(symbol_name)
        price = tick.get("ask") if tick else 0.0

        order_data = {
            "mt5_ticket": order_ticket,
            "account_id": 1,  # TODO: Replace with real account
            "symbol_id": symbol.id,
            "order_type": "MARKET",
            "action": "BUY",
            "volume": volume,
            "price": price,
            "sl": sl,
            "tp": tp,
            "status": "FILLED",
            "comment": comment
        }
        db_order = self.order_repo.create(order_data)

        # Check if position opened
        self._sync_position_after_order(order_ticket)
        return db_order

    def open_sell_order(
        self,
        symbol_name: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = ""
    ) -> Optional[Order]:
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot open order")
            return None

        symbol = self.symbol_repo.get_by_name(symbol_name)
        if not symbol:
            logger.error(f"Symbol {symbol_name} not found")
            return None

        # Use mt5_connector to open sell order
        result = self.mt5_connector.open_sell_order(symbol_name, volume, sl, tp)
        if not result or (hasattr(result, 'retcode') and result.retcode != 10009):
            logger.error("Order failed")
            return None

        order_ticket = result.order if hasattr(result, 'order') else None
        if not order_ticket:
            return None

        tick = self.mt5_connector.get_tick(symbol_name)
        price = tick.get("bid") if tick else 0.0

        order_data = {
            "mt5_ticket": order_ticket,
            "account_id": 1,
            "symbol_id": symbol.id,
            "order_type": "MARKET",
            "action": "SELL",
            "volume": volume,
            "price": price,
            "sl": sl,
            "tp": tp,
            "status": "FILLED",
            "comment": comment
        }
        db_order = self.order_repo.create(order_data)

        self._sync_position_after_order(order_ticket)
        return db_order

    def close_position(
        self,
        mt5_ticket: int,
        comment: str = ""
    ) -> Optional[Position]:
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot close position")
            return None

        # Use mt5_connector to close position
        result = self.mt5_connector.close_position(mt5_ticket)
        if not result or (hasattr(result, 'retcode') and result.retcode != 10009):
            logger.error("Close position failed")
            return None

        # Update DB position
        db_position = self.position_repo.get_by_mt5_ticket(mt5_ticket)
        if db_position:
            self.position_repo.update(db_position, {
                "is_open": False,
                "close_time": datetime.now(),
                "close_reason": "MANUAL"
            })
        return db_position

    def modify_sl_tp(
        self,
        mt5_ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> Optional[Position]:
        # TODO: Add modify_sl_tp method to mt5_connector if needed
        logger.warning("modify_sl_tp not yet implemented via mt5_connector")
        return None

    def _sync_position_after_order(self, order_ticket: int):
        # Wait a bit for position to open
        import time
        time.sleep(0.5)

        # Use mt5_connector to get positions
        positions = self.mt5_connector.get_open_positions()
        for pos in positions:
            db_position = self.position_repo.get_by_mt5_ticket(pos.get("ticket"))
            symbol = self.symbol_repo.get_by_name(pos.get("symbol"))
            if not symbol:
                continue

            position_data = {
                "mt5_ticket": pos.get("ticket"),
                "account_id": 1,
                "symbol_id": symbol.id,
                "order_id": None,
                "position_type": pos.get("type", "BUY"),
                "volume": pos.get("volume"),
                "open_price": pos.get("open_price"),
                "open_time": datetime.fromtimestamp(pos.get("time")) if pos.get("time") else datetime.now(),
                "sl": pos.get("sl"),
                "tp": pos.get("tp"),
                "current_price": pos.get("current_price"),
                "swap": pos.get("swap"),
                "profit": pos.get("profit"),
                "is_open": True
            }

            if db_position:
                self.position_repo.update(db_position, position_data)
            else:
                self.position_repo.create(position_data)

    def sync_open_positions(self):
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected")
            return

        positions = self.mt5_connector.get_open_positions()
        if not positions:
            return

        for pos in positions:
            self._sync_position_after_order(pos.get("ticket"))
