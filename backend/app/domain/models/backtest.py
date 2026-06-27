from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.domain.models.base import Base, TimestampMixin


class Backtest(Base, TimestampMixin):
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(255), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    symbol_name = Column(String(50), nullable=False)
    timeframe = Column(String(20), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    initial_balance = Column(Numeric(18, 2), nullable=False)
    final_balance = Column(Numeric(18, 2))
    net_profit = Column(Numeric(18, 2))
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Numeric(5, 2))
    max_drawdown = Column(Numeric(10, 2))
    profit_factor = Column(Numeric(10, 2))
    sharpe_ratio = Column(Numeric(10, 2))
    average_trade_duration = Column(Numeric(10, 2))  # in minutes
    status = Column(String(20), nullable=False)  # pending, running, completed, failed
    completed_at = Column(DateTime(timezone=True))

    symbol = relationship("Symbol", back_populates="backtests")
    trades = relationship("BacktestTrade", back_populates="backtest", cascade="all, delete-orphan")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id"), nullable=False)
    trade_type = Column(String(10), nullable=False)  # buy, sell
    entry_price = Column(Numeric(18, 5), nullable=False)
    exit_price = Column(Numeric(18, 5))
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True))
    volume = Column(Numeric(10, 2), nullable=False)
    stop_loss = Column(Numeric(18, 5))
    take_profit = Column(Numeric(18, 5))
    profit = Column(Numeric(18, 2))
    profit_pct = Column(Numeric(10, 2))
    duration = Column(Numeric(10, 2))  # in minutes
    exit_reason = Column(String(50))  # sl, tp, signal, close

    backtest = relationship("Backtest", back_populates="trades")


class StrategyResult(Base, TimestampMixin):
    __tablename__ = "strategy_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(255), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id"))
    timeframe = Column(String(20))
    parameters = Column(Text)  # JSON
    performance_metrics = Column(Text)  # JSON
    is_active = Column(Boolean, default=False)
