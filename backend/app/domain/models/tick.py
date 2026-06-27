from sqlalchemy import Column, BigInteger, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.domain.models.base import Base


class Tick(Base):
    __tablename__ = "ticks"

    id = Column(BigInteger, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    bid = Column(Numeric(18, 5), nullable=False)
    ask = Column(Numeric(18, 5), nullable=False)
    last = Column(Numeric(18, 5))
    volume = Column(BigInteger)
    volume_real = Column(Numeric(18, 2))

    symbol = relationship("Symbol", back_populates="ticks")
