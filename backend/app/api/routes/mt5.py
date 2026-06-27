from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from app.core.logging.logger import get_mt5_logger, get_mt5_errors_logger
from app.infrastructure.mt5.connector import get_mt5_connector, MT5Connector
from app.api.schemas.schemas import (
    MT5ConnectRequest,
    MT5ConnectionStatus,
    MT5AccountInfo,
    OpenPosition,
    TradeHistoryResponse,
    TradingPanelRequest,
    GenericResponse,
    ErrorInfo
)
import traceback

router = APIRouter(prefix="/mt5", tags=["MT5"])
mt5_logger = get_mt5_logger()
mt5_errors_logger = get_mt5_errors_logger()


@router.post("/connect", response_model=GenericResponse[dict])
def connect_to_mt5(request: MT5ConnectRequest, mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        result = mt5_connector.connect(request.login, request.password, request.server)
        if result.get("success"):
            return GenericResponse(
                success=True,
                message="Connected to MT5 successfully",
                data=result,
                error=None
            )
        else:
            return GenericResponse(
                success=False,
                message="Failed to connect to MT5",
                data=None,
                error=ErrorInfo(
                    stage=result.get("stage"),
                    error=result.get("error", "Unknown error"),
                    mt5_last_error=result.get("mt5_last_error"),
                    traceback=result.get("traceback")
                )
            )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"connect_to_mt5 exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.post("/disconnect", response_model=GenericResponse[dict])
def disconnect_from_mt5(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        mt5_connector.disconnect()
        return GenericResponse(
            success=True,
            message="Disconnected from MT5 successfully",
            data={"disconnected": True},
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"disconnect_from_mt5 exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/status", response_model=GenericResponse[dict])
def get_connection_status(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        is_connected = mt5_connector.is_connected()
        account_info = mt5_connector.get_account_info() if is_connected else None
        return GenericResponse(
            success=True,
            message="Connection status retrieved successfully",
            data={
                "connected": is_connected,
                "account_info": account_info
            },
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_connection_status exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/account", response_model=GenericResponse[MT5AccountInfo])
def get_account_info(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        account_info = mt5_connector.get_account_info()
        if not account_info:
            return GenericResponse(
                success=False,
                message="Failed to get account info",
                data=None,
                error=ErrorInfo(
                    stage="account",
                    error="Failed to get account info",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        return GenericResponse(
            success=True,
            message="Account info retrieved successfully",
            data=MT5AccountInfo(
                login=account_info.get("login", 0),
                name=account_info.get("name", ""),
                server=account_info.get("server", ""),
                balance=float(account_info.get("balance", 0.0)),
                equity=float(account_info.get("equity", 0.0)),
                margin=float(account_info.get("margin", 0.0)),
                free_margin=float(account_info.get("margin_free", 0.0)),
                profit=float(account_info.get("profit", 0.0)),
                currency=account_info.get("currency", ""),
                leverage=int(account_info.get("leverage", 0))
            ),
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_account_info exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/positions", response_model=GenericResponse[List[OpenPosition]])
def get_open_positions(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        positions = mt5_connector.get_open_positions()
        result = []

        for pos in positions:
            tick = mt5_connector.get_tick(pos["symbol"])
            current_price = tick["ask"] if pos["type"] == 0 else tick["bid"]

            result.append(OpenPosition(
                ticket=pos["ticket"],
                symbol=pos["symbol"],
                type="buy" if pos["type"] == 0 else "sell",
                volume=float(pos["volume"]),
                open_price=float(pos["price_open"]),
                current_price=current_price,
                profit=float(pos["profit"]),
                swap=float(pos["swap"]),
                open_time=datetime.fromtimestamp(pos["time"]),
                sl=float(pos["sl"]) if pos["sl"] != 0 else None,
                tp=float(pos["tp"]) if pos["tp"] != 0 else None
            ))

        return GenericResponse(
            success=True,
            message="Open positions retrieved successfully",
            data=result,
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_open_positions exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/history", response_model=GenericResponse[TradeHistoryResponse])
def get_trade_history(days: int = 30, mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)

        deals = mt5_connector.get_deal_history(date_from, date_to)

        # We need to import TradeHistoryItem here
        from app.api.schemas.schemas import TradeHistoryItem

        trades = []
        total_profit = 0.0
        winning_trades = 0
        losing_trades = 0

        # Filter for deal entries that are position closes
        for deal in deals:
            if deal["entry"] == 1:  # 1 is DEAL_ENTRY_OUT
                profit = float(deal["profit"])
                total_profit += profit

                if profit > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1

                trades.append(TradeHistoryItem(
                    ticket=deal["position_id"],
                    symbol=deal["symbol"],
                    type="buy" if deal["type"] == 1 else "sell",
                    volume=float(deal["volume"]),
                    open_price=float(deal["price_open"]),
                    close_price=float(deal["price"]),
                    profit=profit,
                    open_time=datetime.fromtimestamp(deal["time_msc"] // 1000),
                    close_time=datetime.fromtimestamp(deal["time_msc"] // 1000)
                ))

        total_trades = len(trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        return GenericResponse(
            success=True,
            message="Trade history retrieved successfully",
            data=TradeHistoryResponse(
                trades=trades,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_profit=total_profit
            ),
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_trade_history exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/candles/{symbol}/{timeframe}", response_model=GenericResponse[List[dict]])
def get_candles(symbol: str, timeframe: str, count: int = 500, mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        candles = mt5_connector.get_candles(symbol, timeframe, count)
        if candles is None:
            return GenericResponse(
                success=False,
                message="Failed to get candles",
                data=None,
                error=ErrorInfo(
                    stage="candles",
                    error="Failed to get candles",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        return GenericResponse(
            success=True,
            message="Candles retrieved successfully",
            data=candles,
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_candles exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/symbols", response_model=GenericResponse[List[dict]])
def get_symbols(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        symbols = mt5_connector.get_symbols()
        return GenericResponse(
            success=True,
            message="Symbols retrieved successfully",
            data=symbols,
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_symbols exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/orders", response_model=GenericResponse[List[dict]])
def get_orders(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        orders = mt5_connector.get_orders()
        return GenericResponse(
            success=True,
            message="Pending orders retrieved successfully",
            data=orders,
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_orders exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/tick/{symbol}", response_model=GenericResponse[dict])
def get_tick(symbol: str, mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        tick = mt5_connector.get_tick(symbol)
        if tick is None:
            return GenericResponse(
                success=False,
                message="Failed to get tick data",
                data=None,
                error=ErrorInfo(
                    stage="ticks",
                    error="Failed to get tick data",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        return GenericResponse(
            success=True,
            message="Tick data retrieved successfully",
            data=tick,
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_tick exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.post("/trade/buy", response_model=GenericResponse[dict])
def open_buy_position(request: TradingPanelRequest, mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        result = mt5_connector.open_buy_order("XAUUSD", request.volume, request.sl, request.tp)

        if not result or result.retcode != 10009:
            error_msg = result.comment if hasattr(result, 'comment') else "Unknown error"
            return GenericResponse(
                success=False,
                message="Failed to open buy position",
                data=None,
                error=ErrorInfo(
                    stage="trade",
                    error=error_msg,
                    mt5_last_error=getattr(result, 'retcode', None) if hasattr(result, 'retcode') else None,
                    traceback=None
                )
            )

        return GenericResponse(
            success=True,
            message="Buy position opened successfully",
            data={"ticket": result.order},
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"open_buy_position exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.post("/trade/sell", response_model=GenericResponse[dict])
def open_sell_position(request: TradingPanelRequest, mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        result = mt5_connector.open_sell_order("XAUUSD", request.volume, request.sl, request.tp)

        if not result or result.retcode != 10009:
            error_msg = result.comment if hasattr(result, 'comment') else "Unknown error"
            return GenericResponse(
                success=False,
                message="Failed to open sell position",
                data=None,
                error=ErrorInfo(
                    stage="trade",
                    error=error_msg,
                    mt5_last_error=getattr(result, 'retcode', None) if hasattr(result, 'retcode') else None,
                    traceback=None
                )
            )

        return GenericResponse(
            success=True,
            message="Sell position opened successfully",
            data={"ticket": result.order},
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"open_sell_position exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.post("/trade/close/{ticket}", response_model=GenericResponse[dict])
def close_position(ticket: int, mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        result = mt5_connector.close_position(ticket)

        if not result or result.retcode != 10009:
            error_msg = result.comment if hasattr(result, 'comment') else "Unknown error"
            return GenericResponse(
                success=False,
                message="Failed to close position",
                data=None,
                error=ErrorInfo(
                    stage="trade",
                    error=error_msg,
                    mt5_last_error=getattr(result, 'retcode', None) if hasattr(result, 'retcode') else None,
                    traceback=None
                )
            )

        return GenericResponse(
            success=True,
            message="Position closed successfully",
            data={"ticket": ticket},
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"close_position exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.post("/trade/close-all", response_model=GenericResponse[dict])
def close_all_positions(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=ErrorInfo(
                    stage="connection",
                    error="MT5 not connected",
                    mt5_last_error=None,
                    traceback=None
                )
            )

        results = mt5_connector.close_all_positions()
        return GenericResponse(
            success=True,
            message="All positions closed",
            data={"results_count": len(results), "results": results},
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"close_all_positions exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/debug", response_model=GenericResponse[dict])
def get_debug_info(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        return GenericResponse(
            success=True,
            message="Debug info retrieved successfully",
            data={
                "debug_info": mt5_connector.get_debug_info(),
                "logs": mt5_connector.get_debug_logs()
            },
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_debug_info exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/debug/full", response_model=GenericResponse[dict])
def get_full_debug_info(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        debug_info = mt5_connector.get_full_debug_info()
        return GenericResponse(
            success=True,
            message="Full debug info retrieved successfully",
            data=debug_info,
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_full_debug_info exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )


@router.get("/debug/logs", response_model=GenericResponse[List[dict]])
def get_debug_logs(mt5_connector: MT5Connector = Depends(get_mt5_connector)):
    try:
        logs = mt5_connector.get_debug_logs()
        return GenericResponse(
            success=True,
            message="Debug logs retrieved successfully",
            data=logs,
            error=None
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        mt5_errors_logger.error(f"get_debug_logs exception: {str(e)}\n{error_traceback}")
        return GenericResponse(
            success=False,
            message="Internal server error",
            data=None,
            error=ErrorInfo(
                stage="api",
                error=str(e),
                mt5_last_error=None,
                traceback=error_traceback
            )
        )
