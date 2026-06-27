from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.database.session import get_db
from app.domain.models.backtest import Backtest, BacktestTrade
from app.domain.models.symbol import Symbol
from app.infrastructure.database.repositories import (
    BacktestRepository,
    BacktestTradeRepository,
    SymbolRepository,
    CandleRepository
)
from app.api.schemas.schemas import (
    Backtest as BacktestSchema,
    BacktestCreate,
    BacktestTrade as BacktestTradeSchema,
    StrategyListResponse
)
from app.application.services.backtest_engine import BacktestEngine
from app.application.services.strategies.ema_trend import EMATrendStrategy
from app.core.security import get_current_user
from datetime import datetime

router = APIRouter()


def run_backtest_task(backtest_id: int, db: Session):
    backtest_repo = BacktestRepository(db)
    symbol_repo = SymbolRepository(db)
    candle_repo = CandleRepository(db)
    trade_repo = BacktestTradeRepository(db)
    
    backtest = backtest_repo.get(backtest_id)
    if not backtest:
        return
    
    symbol = symbol_repo.get(backtest.symbol_id)
    if not symbol:
        backtest.status = "failed"
        backtest_repo.update(backtest, {"status": "failed"})
        return
    
    candles_query = candle_repo.get_by_symbol_timeframe(
        backtest.symbol_id,
        backtest.timeframe,
        start_time=backtest.start_date,
        end_time=backtest.end_date,
        limit=100000
    )
    
    candles_list = []
    for c in candles_query:
        candles_list.append({
            'id': c.id,
            'symbol_id': c.symbol_id,
            'timeframe': c.timeframe,
            'time': c.time,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'tick_volume': c.tick_volume,
            'spread': c.spread,
            'real_volume': c.real_volume,
            'symbol_name': symbol.name
        })
    
    strategy = EMATrendStrategy()
    engine = BacktestEngine(strategy, initial_balance=backtest.initial_balance)
    try:
        performance = engine.run(
            candles_list,
            symbol.name,
            backtest.timeframe,
            backtest.start_date,
            backtest.end_date
        )
        
        update_data = {
            "status": "completed",
            "final_balance": performance['final_balance'],
            "net_profit": performance['net_profit'],
            "total_trades": performance['total_trades'],
            "winning_trades": performance['winning_trades'],
            "losing_trades": performance['losing_trades'],
            "win_rate": performance['win_rate'],
            "max_drawdown": performance['max_drawdown'],
            "profit_factor": performance['profit_factor'] if performance['profit_factor'] != float('inf') else None,
            "sharpe_ratio": performance['sharpe_ratio'],
            "average_trade_duration": performance['average_trade_duration'],
            "completed_at": datetime.utcnow()
        }
        backtest = backtest_repo.update(backtest, update_data)
        
        for t in performance['trades']:
            trade_data = {
                "backtest_id": backtest.id,
                "trade_type": t['type'],
                "entry_price": t['entry_price'],
                "exit_price": t['exit_price'],
                "entry_time": t['entry_time'],
                "exit_time": t['exit_time'],
                "volume": t['volume'],
                "sl": t['sl'],
                "tp": t['tp'],
                "profit": t['profit'],
                "profit_pct": t['profit_pct'],
                "duration": t['duration'],
                "exit_reason": t['exit_reason']
            }
            trade_repo.create(trade_data)
        
    except Exception as e:
        backtest_repo.update(backtest, {"status": "failed"})


@router.post("/run", response_model=BacktestSchema)
def run_backtest(
    backtest_data: BacktestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    symbol_repo = SymbolRepository(db)
    backtest_repo = BacktestRepository(db)
    
    symbol = symbol_repo.get_by_name(backtest_data.symbol_name)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    db_backtest = Backtest(
        strategy_name=backtest_data.strategy_name,
        symbol_id=symbol.id,
        symbol_name=symbol.name,
        timeframe=backtest_data.timeframe,
        start_date=backtest_data.start_date,
        end_date=backtest_data.end_date,
        initial_balance=backtest_data.initial_balance,
        status="pending"
    )
    
    db_backtest = backtest_repo.create({
        "strategy_name": backtest_data.strategy_name,
        "symbol_id": symbol.id,
        "symbol_name": symbol.name,
        "timeframe": backtest_data.timeframe,
        "start_date": backtest_data.start_date,
        "end_date": backtest_data.end_date,
        "initial_balance": backtest_data.initial_balance,
        "status": "pending"
    })
    background_tasks.add_task(run_backtest_task, db_backtest.id, db)
    
    return db_backtest


@router.get("/results", response_model=List[BacktestSchema])
def get_backtest_results(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    repo = BacktestRepository(db)
    return repo.get_all(skip=skip, limit=limit)


@router.get("/{backtest_id}", response_model=BacktestSchema)
def get_backtest_by_id(
    backtest_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    repo = BacktestRepository(db)
    backtest = repo.get(backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return backtest


@router.get("/{backtest_id}/trades", response_model=List[BacktestTradeSchema])
def get_backtest_trades(
    backtest_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    repo = BacktestTradeRepository(db)
    return repo.get_by_backtest_id(backtest_id)


@router.get("/strategies/list", response_model=StrategyListResponse)
def list_strategies(
    current_user = Depends(get_current_user)
):
    strategies = [
        {
            "name": "EMATrendStrategy",
            "description": "EMA Trend Strategy (EMA 50/200, RSI, MACD)"
        }
    ]
    return StrategyListResponse(strategies=strategies)
