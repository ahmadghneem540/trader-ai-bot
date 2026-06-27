from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.domain.models.base import Base


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    balance = Column(Numeric(18, 2), nullable=False)
    equity = Column(Numeric(18, 2), nullable=False)
    margin = Column(Numeric(18, 2), nullable=False)
    free_margin = Column(Numeric(18, 2), nullable=False)
    margin_level = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    account = relationship("Account", back_populates="account_snapshots")
