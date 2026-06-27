from sqlalchemy import Column, Integer, String, Numeric, BigInteger, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.domain.models.base import Base, TimestampMixin


class Position(Base, TimestampMixin):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    mt5_ticket = Column(BigInteger, unique=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))
    position_type = Column("type", String(20), nullable=False)
    volume = Column(Numeric(10, 2), nullable=False)
    open_price = Column(Numeric(18, 5), nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    sl = Column(Numeric(18, 5))
    tp = Column(Numeric(18, 5))
    current_price = Column(Numeric(18, 5))
    swap = Column(Numeric(10, 2))
    profit = Column(Numeric(10, 2))
    is_open = Column(Boolean, default=True)
    close_price = Column(Numeric(18, 5))
    close_time = Column(DateTime(timezone=True))
    close_reason = Column(String(50))

    account = relationship("Account", back_populates="positions")
    symbol = relationship("Symbol", back_populates="positions")
    order = relationship("Order", back_populates="positions")
