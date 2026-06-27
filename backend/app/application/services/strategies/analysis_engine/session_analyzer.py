from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime, time
import pytz

@dataclass
class AnalysisResult:
    decision: str  # 'buy', 'sell', 'wait'
    confidence: float  # 0-100
    metadata: Dict[str, Any] = None


class SessionAnalyzer:
    def __init__(self, timezone: str = "UTC"):
        self.name = "Session Analyzer"
        self.timezone = pytz.timezone(timezone)
    
    def get_session(self, dt: datetime) -> str:
        # Convert to UTC first if needed
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        else:
            dt = dt.astimezone(pytz.utc)
        
        hour = dt.hour
        
        # Session definitions (UTC)
        # London: 08:00-16:00
        # New York: 13:00-21:00
        # Asian: 00:00-08:00
        if 8 <= hour < 16:
            return "London"
        elif 13 <= hour <21:
            return "New York"
        else:
            return "Asian"
    
    def analyze(self, current_datetime: datetime) -> AnalysisResult:
        session = self.get_session(current_datetime)
        
        metadata = {
            'session': session,
            'datetime_utc': current_datetime.isoformat(),
            'hour_utc': current_datetime.hour
        }
        
        # London and New York sessions are most active
        if session in ["London", "New York"]:
            confidence = 80
        else:
            # Asian session is less volatile
            confidence = 40
        
        return AnalysisResult(
            decision='wait',  # session doesn't directly give buy/sell
            confidence=confidence,
            metadata=metadata
        )
