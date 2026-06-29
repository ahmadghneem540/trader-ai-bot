
import os
# Set environment variable BEFORE importing anything that uses passlib
os.environ['PASSLIB_BCRYPT_BUG_DETECTION'] = 'skip'

from app.core.config.settings import settings
from app.core.database.session import Base, engine
from app.domain.models import (
    User, Account, Symbol, Candle, Order, Position, Backtest, AccountSnapshot,
    LogEntry, NewsEvent, RiskLimit, Signal, StrategyConfig, Tick
)
import sys

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")
