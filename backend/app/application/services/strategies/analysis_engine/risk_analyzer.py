from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class AnalysisResult:
    decision: str  # 'buy', 'sell', 'wait'
    confidence: float  # 0-100
    metadata: Dict[str, Any] = None


class RiskAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.name = "Risk Analyzer"
        self.config = {
            'max_daily_loss': 100.0,
            'max_open_trades': 1,
            'max_drawdown': 20.0,
            **config
        }

    def analyze(
        self, 
        current_profit_today: float,
        open_positions: List[Dict],
        account_balance: float,
        account_equity: float,
        max_drawdown: float = 0.0
    ) -> AnalysisResult:
        decision = 'wait'
        confidence = 80
        metadata = {}
        
        # Check daily loss limit
        if current_profit_today <= -self.config['max_daily_loss']:
            metadata['daily_limit_hit'] = True
            confidence = 0
        
        # Check max open trades
        if len(open_positions) >= self.config['max_open_trades']:
            metadata['max_open_trades_hit'] = True
            confidence = 0
        
        # Check drawdown
        if max_drawdown >= self.config['max_drawdown']:
            metadata['drawdown_limit_hit'] = True
            confidence = 0
        
        return AnalysisResult(
            decision=decision,
            confidence=confidence,
            metadata=metadata
        )
