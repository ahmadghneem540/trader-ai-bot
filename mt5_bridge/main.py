from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


app = FastAPI(title="TraderAI MT5 Bridge", version="1.0.0")


class ConnectRequest(BaseModel):
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None


class TradeRequest(BaseModel):
    symbol: str
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None


class CloseRequest(BaseModel):
    ticket: int


class ModifyRequest(BaseModel):
    ticket: int
    sl: Optional[float] = None
    tp: Optional[float] = None


def _require_mt5() -> None:
    if not MT5_AVAILABLE:
        raise HTTPException(status_code=503, detail="MetaTrader5 package is not installed in the bridge environment")


def _namedtuple_to_dict(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if hasattr(value, "_asdict"):
        return value._asdict()
    if isinstance(value, dict):
        return value
    return dict(value)


def _last_error() -> Dict[str, Any]:
    try:
        code, message = mt5.last_error()
        return {"code": code, "message": message}
    except Exception:
        return {"code": None, "message": None}


def _ensure_initialized() -> None:
    _require_mt5()
    if mt5.terminal_info() is not None:
        return
    if not mt5.initialize():
        raise HTTPException(status_code=503, detail={"stage": "initialize", "last_error": _last_error()})


def _ensure_symbol(symbol: str) -> None:
    _ensure_initialized()
    if not mt5.symbol_select(symbol, True):
        raise HTTPException(status_code=404, detail={"stage": "symbol_select", "symbol": symbol, "last_error": _last_error()})


def _timeframe(value: str) -> int:
    mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    if value not in mapping:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe: {value}")
    return mapping[value]


def _order_result(result: Any) -> Optional[Dict[str, Any]]:
    data = _namedtuple_to_dict(result)
    if data is None:
        return None
    return {
        "retcode": data.get("retcode"),
        "order": data.get("order"),
        "deal": data.get("deal"),
        "volume": data.get("volume"),
        "price": data.get("price"),
        "comment": data.get("comment"),
        "request_id": data.get("request_id"),
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "mt5_available": MT5_AVAILABLE}


@app.post("/connect")
def connect(request: ConnectRequest) -> Dict[str, Any]:
    _require_mt5()
    mt5.shutdown()
    initialized = mt5.initialize()
    if not initialized:
        raise HTTPException(status_code=503, detail={"stage": "initialize", "last_error": _last_error()})

    if request.login and request.password and request.server:
        logged_in = mt5.login(request.login, password=request.password, server=request.server)
        if not logged_in:
            raise HTTPException(status_code=401, detail={"stage": "login", "last_error": _last_error()})

    account = _namedtuple_to_dict(mt5.account_info())
    return {
        "success": True,
        "message": "Connected to MT5 terminal",
        "connected": account is not None,
        "account": account,
    }


@app.post("/disconnect")
def disconnect() -> Dict[str, Any]:
    _require_mt5()
    mt5.shutdown()
    return {"success": True, "disconnected": True}


@app.get("/status")
def status() -> Dict[str, Any]:
    if not MT5_AVAILABLE:
        return {"connected": False, "terminal": "unavailable", "last_error": "MetaTrader5 package is not installed"}

    terminal = _namedtuple_to_dict(mt5.terminal_info())
    account = _namedtuple_to_dict(mt5.account_info())
    connected = bool(terminal and terminal.get("connected") and account)
    return {
        "connected": connected,
        "terminal": terminal.get("name") if terminal else None,
        "account": str(account.get("login")) if account else None,
        "server": account.get("server") if account else None,
        "balance": float(account.get("balance", 0.0)) if account else 0.0,
        "equity": float(account.get("equity", 0.0)) if account else 0.0,
        "symbol_ready": mt5.symbol_info("XAUUSD") is not None if terminal else False,
        "candles_ready": False,
        "last_error": None if connected else _last_error(),
        "checks": {
            "terminal_running": terminal is not None,
            "mt5_initialized": terminal is not None,
            "login_success": account is not None,
            "account_info": account is not None,
            "terminal_info": terminal is not None,
        },
    }


@app.get("/account")
def account() -> Dict[str, Any]:
    _ensure_initialized()
    info = _namedtuple_to_dict(mt5.account_info())
    if info is None:
        raise HTTPException(status_code=404, detail={"stage": "account_info", "last_error": _last_error()})
    return info


@app.get("/symbols")
def symbols() -> List[Dict[str, Any]]:
    _ensure_initialized()
    result = mt5.symbols_get()
    if result is None:
        raise HTTPException(status_code=500, detail={"stage": "symbols_get", "last_error": _last_error()})
    return [
        {
            "symbol": item.name,
            "description": item.description,
            "spread": item.spread,
            "digits": item.digits,
            "visible": item.visible,
            "trade_mode": item.trade_mode,
        }
        for item in result
    ]


@app.get("/tick/{symbol}")
def tick(symbol: str) -> Dict[str, Any]:
    _ensure_symbol(symbol)
    data = _namedtuple_to_dict(mt5.symbol_info_tick(symbol))
    if data is None:
        raise HTTPException(status_code=404, detail={"stage": "symbol_info_tick", "last_error": _last_error()})
    return data


@app.get("/candles/{symbol}/{timeframe}")
def candles(symbol: str, timeframe: str, count: int = 500) -> List[Dict[str, Any]]:
    _ensure_symbol(symbol)
    rates = mt5.copy_rates_from_pos(symbol, _timeframe(timeframe), 0, count)
    if rates is None or len(rates) == 0:
        start = datetime.now() - timedelta(days=60)
        rates = mt5.copy_rates_from(symbol, _timeframe(timeframe), start, count)
    if rates is None:
        raise HTTPException(status_code=500, detail={"stage": "copy_rates", "last_error": _last_error()})
    return [
        {
            "time": int(item[0]),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "tick_volume": int(item[5]),
            "spread": int(item[6]),
            "real_volume": int(item[7]),
        }
        for item in rates
    ]


@app.get("/open_positions")
def open_positions(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    _ensure_initialized()
    result = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if result is None:
        return []
    return [item._asdict() for item in result]


@app.get("/positions")
def positions(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    return open_positions(symbol)


@app.get("/orders")
def orders() -> List[Dict[str, Any]]:
    _ensure_initialized()
    result = mt5.orders_get()
    if result is None:
        return []
    return [item._asdict() for item in result]


@app.get("/history")
def history(date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> List[Dict[str, Any]]:
    _ensure_initialized()
    end = date_to or datetime.now()
    start = date_from or (end - timedelta(days=30))
    result = mt5.history_deals_get(start, end)
    if result is None:
        return []
    return [item._asdict() for item in result]


@app.post("/buy")
def buy(request: TradeRequest) -> Dict[str, Any]:
    _ensure_symbol(request.symbol)
    price = mt5.symbol_info_tick(request.symbol).ask
    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": request.symbol,
        "volume": request.volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "sl": request.sl,
        "tp": request.tp,
        "deviation": 10,
        "magic": 234000,
        "comment": "TraderAI Bridge Buy",
        "type_filling": mt5.ORDER_FILLING_IOC,
    })
    data = _order_result(result)
    if data is None:
        raise HTTPException(status_code=500, detail={"stage": "order_send", "last_error": _last_error()})
    return data


@app.post("/sell")
def sell(request: TradeRequest) -> Dict[str, Any]:
    _ensure_symbol(request.symbol)
    price = mt5.symbol_info_tick(request.symbol).bid
    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": request.symbol,
        "volume": request.volume,
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": request.sl,
        "tp": request.tp,
        "deviation": 10,
        "magic": 234000,
        "comment": "TraderAI Bridge Sell",
        "type_filling": mt5.ORDER_FILLING_IOC,
    })
    data = _order_result(result)
    if data is None:
        raise HTTPException(status_code=500, detail={"stage": "order_send", "last_error": _last_error()})
    return data


@app.post("/close")
def close(request: CloseRequest) -> Dict[str, Any]:
    _ensure_initialized()
    position = mt5.positions_get(ticket=request.ticket)
    if not position:
        raise HTTPException(status_code=404, detail=f"Position {request.ticket} not found")
    pos = position[0]
    tick_data = mt5.symbol_info_tick(pos.symbol)
    order_type = mt5.ORDER_TYPE_BUY if pos.type == mt5.POSITION_TYPE_SELL else mt5.ORDER_TYPE_SELL
    price = tick_data.ask if order_type == mt5.ORDER_TYPE_BUY else tick_data.bid
    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "position": pos.ticket,
        "price": price,
        "deviation": 10,
        "magic": 234000,
        "comment": "TraderAI Bridge Close",
        "type_filling": mt5.ORDER_FILLING_IOC,
    })
    data = _order_result(result)
    if data is None:
        raise HTTPException(status_code=500, detail={"stage": "order_send", "last_error": _last_error()})
    return data


@app.post("/modify")
def modify(request: ModifyRequest) -> Dict[str, Any]:
    _ensure_initialized()
    position = mt5.positions_get(ticket=request.ticket)
    if not position:
        raise HTTPException(status_code=404, detail=f"Position {request.ticket} not found")
    pos = position[0]
    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos.symbol,
        "position": pos.ticket,
        "sl": request.sl if request.sl is not None else pos.sl,
        "tp": request.tp if request.tp is not None else pos.tp,
    })
    data = _order_result(result)
    if data is None:
        raise HTTPException(status_code=500, detail={"stage": "order_send", "last_error": _last_error()})
    return data
