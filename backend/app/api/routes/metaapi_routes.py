from fastapi import APIRouter, HTTPException, Depends
from app.api.schemas.schemas import (
    MT5ConnectRequest,
    TradeOrderRequest,
    ClosePositionRequest
)
from app.infrastructure.mt5.metaapi_connector import get_metaapi_connector, MetaApiConnector
from app.core.logging.logger import get_logger
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = get_logger(__name__)

router = APIRouter(prefix="/metaapi", tags=["MetaApi"])


@router.post("/connect", response_model=Dict[str, Any])
async def connect_metaapi(
    request: MT5ConnectRequest,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    logger.info(f"Attempting to connect to MetaApi...")
    result = await connector.connect(request.login, request.password, request.server)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/disconnect", response_model=Dict[str, Any])
async def disconnect_metaapi(
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    connector.disconnect()
    return {"success": True, "message": "Disconnected from MetaApi"}


@router.get("/status", response_model=Dict[str, Any])
async def get_metaapi_status(
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    return await connector.get_detailed_status()


@router.get("/account", response_model=Optional[Dict[str, Any]])
async def get_account_info(
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    account_info = await connector.get_account_info()
    if account_info is None:
        raise HTTPException(status_code=500, detail="Failed to get account info")
    
    return account_info


@router.get("/positions", response_model=List[Dict[str, Any]])
async def get_positions(
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    positions = await connector.get_open_positions()
    return positions


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_history(
    days: int = 7,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)
    history = await connector.get_deal_history(date_from, date_to)
    return history


@router.get("/candles/{symbol}/{timeframe}", response_model=Optional[List[Dict[str, Any]]])
async def get_candles(
    symbol: str,
    timeframe: str,
    count: int = 100,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    candles = await connector.get_candles(symbol, timeframe, count)
    return candles


@router.get("/symbols", response_model=List[str])
async def get_symbols(
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    symbols = await connector.get_symbols()
    return symbols


@router.get("/orders", response_model=List[Dict[str, Any]])
async def get_orders(
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    orders = await connector.get_orders()
    return orders


@router.get("/tick/{symbol}", response_model=Optional[Dict[str, Any]])
async def get_tick(
    symbol: str,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    tick = await connector.get_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=500, detail="Failed to get tick data")
    
    return tick


@router.post("/trade/buy", response_model=Optional[Dict[str, Any]])
async def open_buy(
    request: TradeOrderRequest,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    result = await connector.open_buy_order(request.symbol, request.volume, request.sl, request.tp)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to open buy order")
    
    return result


@router.post("/trade/sell", response_model=Optional[Dict[str, Any]])
async def open_sell(
    request: TradeOrderRequest,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    result = await connector.open_sell_order(request.symbol, request.volume, request.sl, request.tp)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to open sell order")
    
    return result


@router.post("/trade/close/{position_id}", response_model=Optional[Dict[str, Any]])
async def close_position_endpoint(
    position_id: str,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    result = await connector.close_position(position_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to close position")
    
    return result


@router.post("/trade/close-all", response_model=List[Dict[str, Any]])
async def close_all_positions_endpoint(
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    if not connector.is_connected():
        raise HTTPException(status_code=400, detail="Not connected to MetaApi")
    
    results = await connector.close_all_positions()
    return results


@router.post("/demo-account", response_model=Dict[str, Any])
async def create_demo_account(
    login: int = None,
    connector: MetaApiConnector = Depends(get_metaapi_connector)
):
    raise HTTPException(status_code=501, detail="Demo account creation via MetaApi requires account registration at https://metaapi.cloud")
