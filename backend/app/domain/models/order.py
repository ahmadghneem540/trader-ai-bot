from sqlalchemy import Column, Integer, String, Numeric, BigInteger, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.domain.models.base import Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    mt5_ticket = Column(BigInteger, unique=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    order_type = Column(String(20), nullable=False)
    action = Column(String(20), nullable=False)
    volume = Column(Numeric(10, 2), nullable=False)
    price = Column(Numeric(18, 5))
    sl = Column(Numeric(18, 5))
    tp = Column(Numeric(18, 5))
    status = Column(String(20), nullable=False)
    comment = Column(String(255))

    account = relationship("Account", back_populates="orders")
    symbol = relationship("Symbol", back_populates="orders")
    signal = relationship("Signal", back_populates="orders")
    positions = relationship("Position", back_populates="order")
