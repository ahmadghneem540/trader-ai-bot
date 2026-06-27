from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from app.infrastructure.database.base_repository import BaseRepository
from app.domain.models.symbol import Symbol
from app.domain.models.candle import Candle
from app.domain.models.tick import Tick
from app.domain.models.order import Order
from app.domain.models.position import Position
from app.domain.models.user import User
from app.domain.models.account import Account
from app.domain.models.risk_limit import RiskLimit
from app.domain.models.strategy_config import StrategyConfig
from app.domain.models.log_entry import LogEntry
from app.domain.models.backtest import Backtest, BacktestTrade, StrategyResult
from datetime import datetime


class SymbolRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Symbol)

    def get_by_name(self, name: str) -> Optional[Symbol]:
        return self.db.execute(select(Symbol).where(Symbol.name == name)).scalar_one_or_none()


class CandleRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Candle)

    def get_by_symbol_timeframe(
        self, symbol_id: int, timeframe: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 10000
    ) -> List[Candle]:
        query = select(Candle).where(Candle.symbol_id == symbol_id, Candle.timeframe == timeframe)
        if start_time:
            query = query.where(Candle.time >= start_time)
        if end_time:
            query = query.where(Candle.time <= end_time)
        query = query.order_by(Candle.time.asc()).limit(limit)
        return self.db.execute(query).scalars().all()

    def get_latest(self, symbol_id: int, timeframe: str) -> Optional[Candle]:
        query = (
            select(Candle)
            .where(Candle.symbol_id == symbol_id, Candle.timeframe == timeframe)
            .order_by(Candle.time.desc())
            .limit(1)
        )
        return self.db.execute(query).scalar_one_or_none()


class TickRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Tick)

    def get_by_symbol(
        self, symbol_id: int, start_time: Optional[datetime] = None, limit: int = 1000
    ) -> List[Tick]:
        query = select(Tick).where(Tick.symbol_id == symbol_id)
        if start_time:
            query = query.where(Tick.time >= start_time)
        query = query.order_by(Tick.time.desc()).limit(limit)
        return self.db.execute(query).scalars().all()


class OrderRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Order)

    def get_by_mt5_ticket(self, mt5_ticket: int) -> Optional[Order]:
        return self.db.execute(select(Order).where(Order.mt5_ticket == mt5_ticket)).scalar_one_or_none()

    def get_by_account(self, account_id: int, skip: int = 0, limit: int = 100) -> List[Order]:
        query = select(Order).where(Order.account_id == account_id).offset(skip).limit(limit)
        return self.db.execute(query).scalars().all()


class PositionRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Position)

    def get_by_mt5_ticket(self, mt5_ticket: int) -> Optional[Position]:
        return self.db.execute(select(Position).where(Position.mt5_ticket == mt5_ticket)).scalar_one_or_none()

    def get_open_positions(self, account_id: int) -> List[Position]:
        query = select(Position).where(Position.account_id == account_id, Position.is_open == True)
        return self.db.execute(query).scalars().all()


class AccountRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Account)

    def get_active_accounts(self) -> List[Account]:
        query = select(Account).where(Account.is_active == True)
        return self.db.execute(query).scalars().all()


class RiskLimitRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, RiskLimit)

    def get_by_account_id(self, account_id: int) -> Optional[RiskLimit]:
        return self.db.execute(select(RiskLimit).where(RiskLimit.account_id == account_id)).scalar_one_or_none()


class UserRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.execute(select(User).where(User.username == username)).scalar_one_or_none()


class StrategyConfigRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, StrategyConfig)

    def get_by_account_id(self, account_id: int) -> Optional[StrategyConfig]:
        return self.db.execute(select(StrategyConfig).where(StrategyConfig.account_id == account_id)).scalar_one_or_none()


class LogEntryRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, LogEntry)

    def get_by_account_id(self, account_id: int, skip: int = 0, limit: int = 100) -> List[LogEntry]:
        query = select(LogEntry).where(LogEntry.account_id == account_id).order_by(LogEntry.created_at.desc()).offset(skip).limit(limit)
        return self.db.execute(query).scalars().all()


class BacktestRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Backtest)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Backtest]:
        query = select(Backtest).order_by(Backtest.created_at.desc()).offset(skip).limit(limit)
        return self.db.execute(query).scalars().all()


class BacktestTradeRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, BacktestTrade)

    def get_by_backtest_id(self, backtest_id: int) -> List[BacktestTrade]:
        query = select(BacktestTrade).where(BacktestTrade.backtest_id == backtest_id).order_by(BacktestTrade.entry_time.asc())
        return self.db.execute(query).scalars().all()


class StrategyResultRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, StrategyResult)
