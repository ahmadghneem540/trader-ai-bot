from typing import List, Optional
from sqlalchemy.orm import Session
from app.infrastructure.database.repositories import SymbolRepository
from app.infrastructure.mt5.connector import MT5Connector
from app.domain.models.symbol import Symbol
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class SymbolService:
    def __init__(self, db: Session, mt5_connector: MT5Connector):
        self.db = db
        self.mt5_connector = mt5_connector
        self.symbol_repo = SymbolRepository(db)

    def get_all_symbols(self) -> List[Symbol]:
        return self.symbol_repo.get_all()

    def get_symbol_by_name(self, name: str) -> Optional[Symbol]:
        return self.symbol_repo.get_by_name(name)

    def sync_symbol_from_mt5(self, symbol_name: str) -> Optional[Symbol]:
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot sync symbol")
            return None

        mt5_symbol = self.mt5_connector.get_symbol_info(symbol_name)
        if not mt5_symbol:
            logger.error(f"Symbol {symbol_name} not found in MT5")
            return None

        existing_symbol = self.symbol_repo.get_by_name(symbol_name)
        symbol_data = {
            "name": symbol_name,
            "description": mt5_symbol.description,
            "digits": mt5_symbol.digits,
            "point": mt5_symbol.point,
            "contract_size": mt5_symbol.trade_contract_size,
            "is_active": True
        }

        if existing_symbol:
            return self.symbol_repo.update(existing_symbol, symbol_data)
        else:
            return self.symbol_repo.create(symbol_data)

    def sync_all_symbols_from_mt5(self) -> List[Symbol]:
        if not self.mt5_connector.is_connected():
            logger.error("MT5 not connected, cannot sync symbols")
            return []

        import MetaTrader5 as mt5
        mt5_symbols = mt5.symbols_get()
        if not mt5_symbols:
            return []

        synced_symbols = []
        for mt5_sym in mt5_symbols:
            synced = self.sync_symbol_from_mt5(mt5_sym.name)
            if synced:
                synced_symbols.append(synced)
        return synced_symbols
