from sqlalchemy import Column, BigInteger, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.domain.models.base import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("symbol_id", "timeframe", "time", name="_symbol_timeframe_time_uc"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    timeframe = Column(String(20), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    open = Column(Numeric(18, 5), nullable=False)
    high = Column(Numeric(18, 5), nullable=False)
    low = Column(Numeric(18, 5), nullable=False)
    close = Column(Numeric(18, 5), nullable=False)
    volume = Column(BigInteger, nullable=False)
    tick_volume = Column(BigInteger)
    spread = Column(Integer)
    real_volume = Column(BigInteger)

    symbol = relationship("Symbol", back_populates="candles")
