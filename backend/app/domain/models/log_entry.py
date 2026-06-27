from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.domain.models.base import Base


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    log_type = Column(String(50), nullable=False)  # signal, open_trade, closed_trade, error, info
    message = Column(Text, nullable=False)
    symbol = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    account = relationship("Account", back_populates="log_entries")
