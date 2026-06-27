import MetaTrader5 as mt5
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
        return self._open_order(
            symbol_name=symbol_name,
            action=mt5.ORDER_TYPE_BUY,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=comment
        )

    def open_sell_order(
        self,
        symbol_name: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = ""
    ) -> Optional[Order]:
        return self._open_order(
            symbol_name=symbol_name,
            action=mt5.ORDER_TYPE_SELL,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=comment
        )

    def _open_order(
        self,
        symbol_name: str,
        action: int,
        volume: float,
        sl: Optional[float],
        tp: Optional[float],
        comment: str
    ) -> Optional[Order]:
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot open order")
            return None

        symbol = self.symbol_repo.get_by_name(symbol_name)
        if not symbol:
            logger.error(f"Symbol {symbol_name} not found")
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol_name,
            "volume": volume,
            "type": action,
            "price": mt5.symbol_info_tick(symbol_name).ask if action == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol_name).bid,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed, retcode={result.retcode}")
            return None

        # Save order to DB
        order_data = {
            "mt5_ticket": result.order,
            "account_id": 1,  # TODO: Replace with real account
            "symbol_id": symbol.id,
            "order_type": "MARKET",
            "action": "BUY" if action == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": volume,
            "price": request["price"],
            "sl": sl,
            "tp": tp,
            "status": "FILLED",
            "comment": comment
        }
        db_order = self.order_repo.create(order_data)

        # Check if position opened
        self._sync_position_after_order(result.order)
        return db_order

    def close_position(
        self,
        mt5_ticket: int,
        comment: str = ""
    ) -> Optional[Position]:
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot close position")
            return None

        position = mt5.positions_get(ticket=mt5_ticket)
        if not position:
            logger.error(f"Position {mt5_ticket} not found")
            return None

        pos = position[0]
        close_action = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_action,
            "position": pos.ticket,
            "price": mt5.symbol_info_tick(pos.symbol).bid if close_action == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(pos.symbol).ask,
            "deviation": 10,
            "magic": 234000,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Close position failed, retcode={result.retcode}")
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
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot modify position")
            return None

        position = mt5.positions_get(ticket=mt5_ticket)
        if not position:
            logger.error(f"Position {mt5_ticket} not found")
            return None

        pos = position[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": pos.ticket,
            "sl": sl if sl is not None else pos.sl,
            "tp": tp if tp is not None else pos.tp,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Modify SL/TP failed, retcode={result.retcode}")
            return None

        db_position = self.position_repo.get_by_mt5_ticket(mt5_ticket)
        if db_position:
            self.position_repo.update(db_position, {"sl": sl, "tp": tp})
        return db_position

    def _sync_position_after_order(self, order_ticket: int):
        # Wait a bit for position to open
        import time
        time.sleep(0.5)

        positions = mt5.positions_get()
        for pos in positions:
            db_position = self.position_repo.get_by_mt5_ticket(pos.ticket)
            symbol = self.symbol_repo.get_by_name(pos.symbol)
            if not symbol:
                continue

            position_data = {
                "mt5_ticket": pos.ticket,
                "account_id": 1,
                "symbol_id": symbol.id,
                "order_id": None,
                "position_type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                "volume": pos.volume,
                "open_price": pos.price_open,
                "open_time": datetime.fromtimestamp(pos.time),
                "sl": pos.sl,
                "tp": pos.tp,
                "current_price": pos.price_current,
                "swap": pos.swap,
                "profit": pos.profit,
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

        positions = mt5.positions_get()
        if not positions:
            return

        for pos in positions:
            self._sync_position_after_order(pos.ticket)
