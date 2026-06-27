from sqlalchemy import Column, Integer, Numeric, Boolean, ForeignKey, String
from sqlalchemy.orm import relationship
from app.domain.models.base import Base, TimestampMixin


class StrategyConfig(Base, TimestampMixin):
    __tablename__ = "strategy_configs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    selected_strategy = Column(String(255), default="EMATrendStrategy")
    risk_percent = Column(Numeric(5, 2), default=1.0)
    max_daily_loss = Column(Numeric(10, 2), default=100.0)
    max_weekly_loss = Column(Numeric(10, 2), default=500.0)
    lot_size = Column(Numeric(10, 2), default=0.1)
    max_open_trades = Column(Integer, default=5)
    max_consecutive_losses = Column(Integer, default=3)
    is_bot_active = Column(Boolean, default=False)
    is_paused = Column(Boolean, default=False)
    safety_mode = Column(Boolean, default=True)  # Default DEMO ONLY
    schedule_timeframe = Column(String(20), default="H1")  # M15 or H1
    trailing_stop_enabled = Column(Boolean, default=False)
    trailing_stop_pips = Column(Integer, default=50)
    breakeven_enabled = Column(Boolean, default=False)
    breakeven_pips = Column(Integer, default=30)

    account = relationship("Account", back_populates="strategy_configs")
