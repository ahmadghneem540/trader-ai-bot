from sqlalchemy import Column, Integer, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.domain.models.base import Base


class RiskLimit(Base):
    __tablename__ = "risk_limits"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    max_daily_loss = Column(Numeric(10, 2))
    max_drawdown = Column(Numeric(5, 2))
    max_position_size = Column(Numeric(10, 2))
    max_open_positions = Column(Integer)
    is_active = Column(Boolean, default=True)

    account = relationship("Account", back_populates="risk_limits")
