from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database.session import get_db
from app.infrastructure.mt5.connector import get_mt5_connector, MT5Connector
from app.infrastructure.market_data.collector import MarketDataCollector
from app.api.schemas.schemas import Candle, Tick
from app.infrastructure.database.repositories import CandleRepository, TickRepository, SymbolRepository

router = APIRouter(prefix="/market-data", tags=["Market Data"])


def get_market_data_collector(
    db: Session = Depends(get_db),
    mt5_connector: MT5Connector = Depends(get_mt5_connector)
) -> MarketDataCollector:
    return MarketDataCollector(mt5_connector, db)


@router.get("/candles/{symbol_name}", response_model=List[Candle])
def get_candles(
    symbol_name: str,
    timeframe: str = Query("H1"),
    count: int = Query(100, ge=1, le=10000),
    save_to_db: bool = Query(True),
    collector: MarketDataCollector = Depends(get_market_data_collector),
    db: Session = Depends(get_db)
):
    try:
        collector.get_historical_candles(symbol_name, timeframe, count, save_to_db=save_to_db)
        symbol = SymbolRepository(db).get_by_name(symbol_name)
        if not symbol:
            raise HTTPException(status_code=404, detail="Symbol not found")
        candles = CandleRepository(db).get_by_symbol_timeframe(symbol.id, timeframe, limit=count)
        return candles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticks/{symbol_name}", response_model=List[Tick])
def get_ticks(
    symbol_name: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    symbol = SymbolRepository(db).get_by_name(symbol_name)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return TickRepository(db).get_by_symbol(symbol.id, limit=limit)


@router.get("/tick/{symbol_name}", response_model=Optional[Tick])
def get_current_tick(
    symbol_name: str,
    save_to_db: bool = Query(True),
    collector: MarketDataCollector = Depends(get_market_data_collector)
):
    try:
        tick = collector.get_current_tick(symbol_name, save_to_db=save_to_db)
        if not tick:
            raise HTTPException(status_code=404, detail="Tick not found")
        return tick
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
