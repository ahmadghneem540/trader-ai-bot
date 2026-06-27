from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.domain.models.base import Base, TimestampMixin


class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    signal_type = Column(String(20), nullable=False)
    reason = Column(Text)
    confidence = Column(Numeric(5, 2))
    strategy_name = Column(String(255))

    symbol = relationship("Symbol", back_populates="signals")
    orders = relationship("Order", back_populates="signal")
