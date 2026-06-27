from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from sqlalchemy.orm import relationship
from app.domain.models.base import Base, TimestampMixin


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(BigInteger, unique=True, nullable=False)
    server = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)
    broker = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)

    account_snapshots = relationship("AccountSnapshot", back_populates="account")
    orders = relationship("Order", back_populates="account")
    positions = relationship("Position", back_populates="account")
    risk_limits = relationship("RiskLimit", back_populates="account")
    strategy_configs = relationship("StrategyConfig", back_populates="account")
    log_entries = relationship("LogEntry", back_populates="account")
