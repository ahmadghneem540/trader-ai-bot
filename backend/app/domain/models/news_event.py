from sqlalchemy import Column, Integer, String, DateTime
from app.domain.models.base import Base


class NewsEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    currency = Column(String(10))
    impact = Column(String(20))
    event_time = Column(DateTime(timezone=True), nullable=False)
    actual = Column(String(255))
    forecast = Column(String(255))
    previous = Column(String(255))
    source = Column(String(255))
