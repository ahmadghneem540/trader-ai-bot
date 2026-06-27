from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database.session import get_db
from app.infrastructure.mt5.connector import get_mt5_connector, MT5Connector
from app.application.services.trading_service import TradingService
from app.api.schemas.schemas import (
    Order,
    Position,
    OpenOrderRequest,
    ModifySLTPRequest,
    ClosePositionRequest
)
from app.infrastructure.database.repositories import OrderRepository, PositionRepository

router = APIRouter(prefix="/trading", tags=["Trading"])


def get_trading_service(
    db: Session = Depends(get_db),
    mt5_connector: MT5Connector = Depends(get_mt5_connector)
) -> TradingService:
    return TradingService(db, mt5_connector)


@router.post("/buy", response_model=Order)
def open_buy_order(
    request: OpenOrderRequest,
    service: TradingService = Depends(get_trading_service)
):
    order = service.open_buy_order(
        request.symbol_name,
        request.volume,
        request.sl,
        request.tp,
        request.comment
    )
    if not order:
        raise HTTPException(status_code=500, detail="Failed to open buy order")
    return order


@router.post("/sell", response_model=Order)
def open_sell_order(
    request: OpenOrderRequest,
    service: TradingService = Depends(get_trading_service)
):
    order = service.open_sell_order(
        request.symbol_name,
        request.volume,
        request.sl,
        request.tp,
        request.comment
    )
    if not order:
        raise HTTPException(status_code=500, detail="Failed to open sell order")
    return order


@router.post("/close", response_model=Position)
def close_position(
    request: ClosePositionRequest,
    service: TradingService = Depends(get_trading_service)
):
    position = service.close_position(request.mt5_ticket, request.comment)
    if not position:
        raise HTTPException(status_code=500, detail="Failed to close position")
    return position


@router.post("/modify-sl-tp", response_model=Position)
def modify_sl_tp(
    request: ModifySLTPRequest,
    service: TradingService = Depends(get_trading_service)
):
    position = service.modify_sl_tp(request.mt5_ticket, request.sl, request.tp)
    if not position:
        raise HTTPException(status_code=500, detail="Failed to modify SL/TP")
    return position


@router.get("/positions/open", response_model=List[Position])
def get_open_positions(
    db: Session = Depends(get_db)
):
    return PositionRepository(db).get_open_positions(1)


@router.get("/orders", response_model=List[Order])
def get_orders(
    db: Session = Depends(get_db)
):
    return OrderRepository(db).get_by_account(1)
