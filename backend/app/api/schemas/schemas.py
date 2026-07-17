from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class ErrorInfo(BaseModel):
    stage: Optional[str] = None
    error: str
    mt5_last_error: Optional[Any] = None
    traceback: Optional[str] = None


class GenericResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[ErrorInfo] = None


class SymbolBase(BaseModel):
    name: str
    description: Optional[str] = None
    digits: int
    point: float
    contract_size: float
    is_active: bool = True


class SymbolCreate(SymbolBase):
    pass


class Symbol(SymbolBase):
    id: int

    class Config:
        from_attributes = True


class CandleBase(BaseModel):
    symbol_id: int
    timeframe: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: Optional[int] = None
    spread: Optional[int] = None
    real_volume: Optional[int] = None


class CandleCreate(CandleBase):
    pass


class Candle(CandleBase):
    id: int

    class Config:
        from_attributes = True


class TickBase(BaseModel):
    symbol_id: int
    time: datetime
    bid: float
    ask: float
    last: Optional[float] = None
    volume: Optional[int] = None
    volume_real: Optional[float] = None


class TickCreate(TickBase):
    pass


class Tick(TickBase):
    id: int

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    mt5_ticket: Optional[int] = None
    account_id: int
    symbol_id: int
    signal_id: Optional[int] = None
    order_type: str
    action: str
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    status: str
    comment: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class Order(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PositionBase(BaseModel):
    mt5_ticket: Optional[int] = None
    account_id: int
    symbol_id: int
    order_id: Optional[int] = None
    position_type: str
    volume: float
    open_price: float
    open_time: datetime
    sl: Optional[float] = None
    tp: Optional[float] = None
    current_price: Optional[float] = None
    swap: Optional[float] = None
    profit: Optional[float] = None
    is_open: bool = True
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    close_reason: Optional[str] = None


class PositionCreate(PositionBase):
    pass


class Position(PositionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OpenOrderRequest(BaseModel):
    symbol_name: str
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = ""


class TradeOrderRequest(BaseModel):
    symbol: str
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None


class ModifySLTPRequest(BaseModel):
    mt5_ticket: int
    sl: Optional[float] = None
    tp: Optional[float] = None


class ClosePositionRequest(BaseModel):
    mt5_ticket: int
    comment: str = ""


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class StrategyConfigBase(BaseModel):
    account_id: int
    selected_strategy: Optional[str] = "GoldAutonomousStrategy"
    risk_percent: Optional[float] = 1.0
    max_daily_loss: Optional[float] = 100.0
    max_weekly_loss: Optional[float] = 500.0
    lot_size: Optional[float] = 0.1
    max_open_trades: Optional[int] = 5
    max_consecutive_losses: Optional[int] = 3
    is_bot_active: Optional[bool] = False
    is_paused: Optional[bool] = False
    safety_mode: Optional[bool] = True
    schedule_timeframe: Optional[str] = "H1"
    trailing_stop_enabled: Optional[bool] = False
    trailing_stop_pips: Optional[int] = 50
    breakeven_enabled: Optional[bool] = False
    breakeven_pips: Optional[int] = 30


class StrategyConfigCreate(StrategyConfigBase):
    pass


class StrategyConfigUpdate(BaseModel):
    selected_strategy: Optional[str] = None
    risk_percent: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_weekly_loss: Optional[float] = None
    lot_size: Optional[float] = None
    max_open_trades: Optional[int] = None
    max_consecutive_losses: Optional[int] = None
    is_bot_active: Optional[bool] = None
    is_paused: Optional[bool] = None
    safety_mode: Optional[bool] = None
    schedule_timeframe: Optional[str] = None
    trailing_stop_enabled: Optional[bool] = None
    trailing_stop_pips: Optional[int] = None
    breakeven_enabled: Optional[bool] = None
    breakeven_pips: Optional[int] = None


class StrategyConfig(StrategyConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LogEntryBase(BaseModel):
    account_id: Optional[int] = None
    log_type: str
    message: str
    symbol: Optional[str] = None
    created_at: datetime


class LogEntryCreate(LogEntryBase):
    pass


class LogEntry(LogEntryBase):
    id: int

    class Config:
        from_attributes = True


class AccountOverview(BaseModel):
    balance: float
    equity: float
    free_margin: float
    profit: float
    daily_pnl: Optional[float] = 0.0
    weekly_pnl: Optional[float] = 0.0
    active_strategy: Optional[str] = None
    current_signal: Optional[str] = None


class BotControlRequest(BaseModel):
    action: str


class BacktestBase(BaseModel):
    strategy_name: str
    symbol_id: int
    symbol_name: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_balance: float


class BacktestCreate(BaseModel):
    strategy_name: str
    symbol_name: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0


class Backtest(BacktestBase):
    id: int
    final_balance: Optional[float] = None
    net_profit: Optional[float] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    win_rate: Optional[float] = None
    max_drawdown: Optional[float] = None
    profit_factor: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    average_trade_duration: Optional[float] = None
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BacktestTradeBase(BaseModel):
    backtest_id: int
    trade_type: str
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    profit: Optional[float] = None
    profit_pct: Optional[float] = None
    duration: Optional[float] = None
    exit_reason: Optional[str] = None


class BacktestTradeCreate(BacktestTradeBase):
    pass


class BacktestTrade(BacktestTradeBase):
    id: int

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    strategies: List[Dict[str, Any]]


class MT5ConnectRequest(BaseModel):
    login: int
    password: str
    server: str


class MT5ConnectionStatus(BaseModel):
    connected: bool
    account_info: Optional[Dict[str, Any]] = None


class MT5StatusResponse(BaseModel):
    connected: bool
    terminal: Optional[str] = None
    account: Optional[str] = None
    server: Optional[str] = None
    balance: float = 0.0
    equity: float = 0.0
    symbol_ready: bool = False
    candles_ready: bool = False
    last_error: Optional[str] = None


class MT5AccountInfo(BaseModel):
    login: int
    name: str
    server: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    profit: float
    currency: str
    leverage: int


class OpenPosition(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    current_price: float
    profit: float
    swap: float
    open_time: datetime
    sl: Optional[float] = None
    tp: Optional[float] = None


class TradeHistoryItem(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    close_price: float
    profit: float
    open_time: datetime
    close_time: datetime


class TradeHistoryResponse(BaseModel):
    trades: List[TradeHistoryItem]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float


class CandlesRequest(BaseModel):
    symbol: str
    timeframe: str
    count: Optional[int] = 500


class TradingPanelRequest(BaseModel):
    symbol: str
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None


class SimpleCandle(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: Optional[int] = None
    spread: Optional[int] = None
    real_volume: Optional[int] = None


class AIAnalyzeRequest(BaseModel):
    symbol: str
    timeframe: str
    candles: List[SimpleCandle]


class AIAnalyzeResponse(BaseModel):
    trend: str
    confidence: int
    reason: str
    support: List[float]
    resistance: List[float]


# MetaApi Schemas
class MetaApiConnectRequest(BaseModel):
    login: int
    password: str
    server: str
    account_id: Optional[str] = None


class MetaApiCreateDemoAccountRequest(BaseModel):
    broker: str
    server: str
    leverage: int = 100
    balance: float = 10000.0


class MetaApiAccountStatus(BaseModel):
    connected: bool
    demo_mode: bool
    metaapi_available: bool
    credentials: Optional[Dict[str, Any]] = None
