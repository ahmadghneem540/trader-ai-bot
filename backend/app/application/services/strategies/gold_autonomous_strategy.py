from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.application.services.strategies.base import StrategyBase, Signal
from app.application.services.strategies.indicators import calculate_atr
from app.application.services.strategies.analysis_engine import (
    TrendAnalyzer,
    MomentumAnalyzer,
    PriceActionAnalyzer,
    VolatilityAnalyzer,
    SessionAnalyzer,
    RiskAnalyzer
)
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EngineDecision:
    decision: str  # buy, sell, wait
    confidence: float  # 0-100
    analyzer_results: Dict[str, Any]
    metadata: Dict[str, Any]


class GoldAutonomousStrategy(StrategyBase):
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.name = "GoldAutonomousStrategy"
        
        # Default parameters
        self.default_params = {
            'confidence_threshold': 85.0,
            'max_open_trades': 1,
            'max_daily_loss': 100.0,
            'atr_multiplier_sl': 1.5,
            'atr_multiplier_tp': 3.0
        }
        
        self.params = {**self.default_params, **(parameters or {})}
        
        # Initialize analyzers
        self.trend_analyzer = TrendAnalyzer()
        self.momentum_analyzer = MomentumAnalyzer()
        self.price_action_analyzer = PriceActionAnalyzer()
        self.volatility_analyzer = VolatilityAnalyzer()
        self.session_analyzer = SessionAnalyzer()
        self.risk_analyzer = RiskAnalyzer(self.params)
        self.last_decision = None
    
    def _compute_analyzers(
        self,
        candles: List[Dict],
        current_datetime: datetime,
        spread: float = 0.0,
        current_profit_today: float = 0.0,
        open_positions: List = [],
        account_balance: float = 0.0,
        account_equity: float =0.0,
        max_drawdown: float =0.0
    ) -> Dict[str, Dict]:
        results = {}
        
        results['trend'] = {
            'decision': self.trend_analyzer.analyze(candles).decision,
            'confidence': self.trend_analyzer.analyze(candles).confidence,
            'metadata': self.trend_analyzer.analyze(candles).metadata
        }
        
        results['momentum'] = {
            'decision': self.momentum_analyzer.analyze(candles).decision,
            'confidence': self.momentum_analyzer.analyze(candles).confidence,
            'metadata': self.momentum_analyzer.analyze(candles).metadata
        }
        
        results['price_action'] = {
            'decision': self.price_action_analyzer.analyze(candles).decision,
            'confidence': self.price_action_analyzer.analyze(candles).confidence,
            'metadata': self.price_action_analyzer.analyze(candles).metadata
        }
        
        results['volatility'] = {
            'decision': self.volatility_analyzer.analyze(candles, spread).decision,
            'confidence': self.volatility_analyzer.analyze(candles, spread).confidence,
            'metadata': self.volatility_analyzer.analyze(candles, spread).metadata
        }
        
        results['session'] = {
            'decision': self.session_analyzer.analyze(current_datetime).decision,
            'confidence': self.session_analyzer.analyze(current_datetime).confidence,
            'metadata': self.session_analyzer.analyze(current_datetime).metadata
        }
        
        results['risk'] = {
            'decision': self.risk_analyzer.analyze(
                current_profit_today,
                open_positions,
                account_balance,
                account_equity,
                max_drawdown
            ).decision,
            'confidence': self.risk_analyzer.analyze(
                current_profit_today,
                open_positions,
                account_balance,
                account_equity,
                max_drawdown
            ).confidence,
            'metadata': self.risk_analyzer.analyze(
                current_profit_today,
                open_positions,
                account_balance,
                account_equity,
                max_drawdown
            ).metadata
        }
        
        return results
    
    def _aggregate_decision(self, analyzer_results: Dict[str, Dict]) -> EngineDecision:
        total_confidence =0
        buy_votes =0
        sell_votes=0
        wait_votes=0
        
        for name, res in analyzer_results.items():
            if name == 'risk':
                continue
                
            confidence = res['confidence']
            decision = res['decision']
            
            if decision == 'buy':
                buy_votes +=1
                total_confidence += confidence
            elif decision == 'sell':
                sell_votes +=1
                total_confidence += confidence
            else:
                wait_votes +=1
        
        # Check risk
        risk_conf = analyzer_results['risk']['confidence']
        if risk_conf ==0:
            return EngineDecision(
                decision='wait',
                confidence=0,
                analyzer_results=analyzer_results,
                metadata={'reason': 'Risk limits hit'}
            )
        
        num_analyzers = len([a for a in analyzer_results if a != 'risk'])
        avg_confidence = total_confidence / num_analyzers if num_analyzers >0 else 0
        
        final_decision = 'wait'
        if buy_votes > sell_votes and buy_votes >=2:
            final_decision = 'buy'
        elif sell_votes > buy_votes and sell_votes >=2:
            final_decision = 'sell'
        
        return EngineDecision(
            decision=final_decision,
            confidence=avg_confidence,
            analyzer_results=analyzer_results,
            metadata={}
        )
    
    def generate_signal(
        self, 
        candles: list, 
        current_price: float,
        spread: float = 0.0,
        current_datetime: Optional[datetime] = None,
        current_profit_today: float = 0.0,
        open_positions: List = [],
        account_balance: float = 0.0,
        account_equity: float = 0.0,
        max_drawdown: float = 0.0
    ) -> Optional[Signal]:
        if current_datetime is None:
            current_datetime = datetime.now()

        symbol_name = "unknown"
        if candles and isinstance(candles[-1], dict):
            symbol_name = candles[-1].get("symbol_name", "unknown")
            
        # Compute all analyzers
        analyzer_results = self._compute_analyzers(
            candles,
            current_datetime,
            spread,
            current_profit_today,
            open_positions,
            account_balance,
            account_equity,
            max_drawdown
        )
        
        # Aggregate decision
        engine_decision = self._aggregate_decision(analyzer_results)
        self.last_decision = engine_decision
        
        logger.info(f"Analysis Decision: {engine_decision.decision}, Confidence: {engine_decision.confidence}%")
        
        # Check confidence threshold
        if engine_decision.confidence < self.params['confidence_threshold']:
            logger.info(f"Confidence {engine_decision.confidence}% below threshold {self.params['confidence_threshold']}% - no trade")
            return None
            
        if engine_decision.decision not in ['buy', 'sell']:
            return None
            
        return Signal(
            symbol=symbol_name,
            signal_type=engine_decision.decision,
            price=current_price,
            confidence=engine_decision.confidence,
            metadata={
                'analyzer_results': analyzer_results,
                'engine_decision': engine_decision
            }
        )

    def validate_entry(self, signal: Signal, candles: list) -> bool:
        return True

    def validate_exit(self, position: dict, current_candle: dict) -> tuple[bool, str]:
        return False, ""

    def calculate_stop_loss(self, entry_price: float, direction: str, candles: list) -> float:
        # Use ATR to calculate SL
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        closes = [c['close'] for c in candles]
        atr = calculate_atr(highs, lows, closes,14)
        latest_atr = atr[-1] if atr else 10.0
        
        if direction == 'buy':
            return entry_price - (latest_atr * self.params['atr_multiplier_sl'])
        else:
            return entry_price + (latest_atr * self.params['atr_multiplier_sl'])

    def calculate_take_profit(self, entry_price: float, direction: str, candles: list) -> float:
        # Use ATR to calculate TP
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        closes = [c['close'] for c in candles]
        atr = calculate_atr(highs, lows, closes,14)
        latest_atr = atr[-1] if atr else 10.0
        
        if direction == 'buy':
            return entry_price + (latest_atr * self.params['atr_multiplier_tp'])
        else:
            return entry_price - (latest_atr * self.params['atr_multiplier_tp'])
