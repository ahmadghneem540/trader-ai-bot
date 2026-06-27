import math
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.domain.models.backtest import Backtest, BacktestTrade
from app.application.services.strategies.base import StrategyBase
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    def __init__(self, strategy: StrategyBase, initial_balance: float = 10000.0):
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.equity_history = []
        self.trades = []
        self.open_positions = []

    def run(
        self,
        candles: List[Dict[str, Any]],
        symbol_name: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        self.equity = self.initial_balance
        self.balance = self.initial_balance
        self.trades = []
        self.open_positions = []
        self.equity_history = []

        position_size = 0.1
        for i in range(len(candles)):
            current_candles = candles[:i + 1]
            current_candle = candles[i]
            current_price = current_candle['close']
            
            for position in list(self.open_positions):
                should_exit, reason = self.strategy.validate_exit(position, current_candle)
                if should_exit:
                    self.close_position(position, current_price, current_candle['time'], reason)
            
            if len(self.open_positions) == 0:
                signal = self.strategy.generate_signal(current_candles, current_price)
                if signal and self.strategy.validate_entry(signal, current_candles):
                    sl = self.strategy.calculate_stop_loss(current_price, signal.signal_type, current_candles)
                    tp = self.strategy.calculate_take_profit(current_price, signal.signal_type, current_candles)
                    self.open_position(
                        signal.signal_type,
                        current_price,
                        current_candle['time'],
                        position_size,
                        sl,
                        tp,
                        symbol_name
                    )
            
            self.equity = self.balance + sum(pos['unrealized_pnl'] for pos in self.open_positions if pos)
            self.equity_history.append({
                'time': current_candle['time'],
                'equity': self.equity
            })
        
        for position in list(self.open_positions):
            self.close_position(position, candles[-1]['close'], candles[-1]['time'], 'end of test')
        
        performance = self.calculate_performance()
        return performance

    def open_position(
        self, direction: str, entry_price: float, entry_time: datetime, volume: float, sl: float, tp: float, symbol_name: str
    ):
        position = {
            'type': direction,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'volume': volume,
            'sl': sl,
            'tp': tp,
            'symbol': symbol_name,
            'unrealized_pnl': 0.0
        }
        self.open_positions.append(position)

    def close_position(self, position: dict, exit_price: float, exit_time: datetime, reason: str):
        direction = position['type']
        entry_price = position['entry_price']
        if direction == 'buy':
            pnl = (exit_price - entry_price) * position['volume'] * 100
        else:
            pnl = (entry_price - exit_price) * position['volume'] * 100
        
        duration = (exit_time - position['entry_time']).total_seconds() / 60
        
        trade = {
            'type': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'volume': position['volume'],
            'sl': position['sl'],
            'tp': position['tp'],
            'profit': pnl,
            'profit_pct': ((pnl / self.initial_balance) * 100),
            'duration': duration,
            'exit_reason': reason,
            'symbol': position['symbol']
        }
        self.trades.append(trade)
        self.balance += pnl
        self.open_positions.remove(position)

    def calculate_performance(self) -> Dict[str, Any]:
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['profit'] > 0])
        losing_trades = len([t for t in self.trades if t['profit'] <=0])
        
        win_rate = 0.0
        if total_trades > 0:
            win_rate = (winning_trades / total_trades) * 100
        
        gross_profit = sum(t['profit'] for t in self.trades if t['profit'] > 0)
        gross_loss = abs(sum(t['profit'] for t in self.trades if t['profit'] <0))
        profit_factor = 0.0
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = float('inf')
        
        total_return = self.balance - self.initial_balance
        
        equity_values = [h['equity'] for h in self.equity_history]
        peak = self.initial_balance
        max_drawdown = 0.0
        for eq in equity_values:
            if eq > peak:
                peak = eq
            drawdown = (peak - eq) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        returns = []
        for i in range(1, len(equity_values)):
            returns.append((equity_values[i] - equity_values[i-1]) / equity_values[i-1])
        
        sharpe_ratio = 0.0
        if len(returns) > 0 and self.initial_balance > 0:
            avg_return = sum(returns)/len(returns) if returns else 0.0
            std_dev = math.sqrt(sum((r - avg_return)**2 for r in returns)/len(returns)) if len(returns) >0 else 0.0
            if std_dev > 0:
                sharpe_ratio = (avg_return / std_dev) * math.sqrt(252)
        
        avg_duration = 0.0
        if total_trades >0:
            avg_duration = sum(t['duration'] for t in self.trades)/total_trades
        
        return {
            'final_balance': self.balance,
            'net_profit': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'average_trade_duration': avg_duration,
            'trades': self.trades
        }
