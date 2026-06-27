from sqlalchemy import Column, Integer, String, Boolean, Numeric
from sqlalchemy.orm import relationship
from app.domain.models.base import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    digits = Column(Integer, nullable=False)
    point = Column(Numeric(10, 5), nullable=False)
    contract_size = Column(Numeric(18, 2), nullable=False)
    is_active = Column(Boolean, default=True)

    candles = relationship("Candle", back_populates="symbol")
    ticks = relationship("Tick", back_populates="symbol")
    signals = relationship("Signal", back_populates="symbol")
    orders = relationship("Order", back_populates="symbol")
    positions = relationship("Position", back_populates="symbol")
    backtests = relationship("Backtest", back_populates="symbol")
