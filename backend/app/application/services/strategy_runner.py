from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database.session import SessionLocal
from app.infrastructure.mt5.connector import MT5Connector
from app.infrastructure.database.repositories import (
    StrategyConfigRepository,
    AccountRepository,
    PositionRepository,
    LogEntryRepository,
    SymbolRepository,
    CandleRepository
)
from app.domain.models.log_entry import LogEntry
from app.application.services.strategies.ema_trend import EMATrendStrategy
from app.application.services.strategies.ai_strategy import AIStrategy
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class StrategyRunner:
    def __init__(self):
        self.supported_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        self.strategies = {
            "EMATrendStrategy": EMATrendStrategy,
            "AIStrategy": AIStrategy
        }
        self.mt5 = MT5Connector()

    def get_db_session(self) -> Session:
        return SessionLocal()

    def calculate_daily_pnl(self, account_id: int, db: Session) -> Decimal:
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        # Calculate from closed trades today - placeholder
        return Decimal(0.0)

    def calculate_weekly_pnl(self, account_id: int, db: Session) -> Decimal:
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        # Calculate from closed trades this week - placeholder
        return Decimal(0.0)

    def check_risk_limits(self, config, db: Session, mt5_account) -> tuple[bool, str]:
        if config.safety_mode and not mt5_account.get("is_demo", True):
            return False, "Safety mode enabled - real trading disabled!"

        daily_pnl = self.calculate_daily_pnl(config.account_id, db)
        if daily_pnl <= -config.max_daily_loss:
            return False, f"Daily loss limit hit: {daily_pnl} > -{config.max_daily_loss}"

        weekly_pnl = self.calculate_weekly_pnl(config.account_id, db)
        if weekly_pnl <= -config.max_weekly_loss:
            return False, f"Weekly loss limit hit: {weekly_pnl} > -{config.max_weekly_loss}"

        return True, "OK"

    def run_cycle(self, symbol_name: str, timeframe: str):
        db = self.get_db_session()
        try:
            config_repo = StrategyConfigRepository(db)
            log_repo = LogEntryRepository(db)
            symbol_repo = SymbolRepository(db)
            candle_repo = CandleRepository(db)
            position_repo = PositionRepository(db)

            config = config_repo.get_by_account_id(1)
            if not config:
                logger.warning("No strategy config found")
                return

            if not config.is_bot_active or config.is_paused:
                logger.info("Bot inactive or paused")
                return

            if not self.mt5.is_connected():
                logger.warning("MT5 not connected")
                return

            mt5_account = self.mt5.get_account_info()
            safe, reason = self.check_risk_limits(config, db, mt5_account)
            if not safe:
                logger.error(reason)
                log = LogEntry(
                    account_id=config.account_id,
                    log_type="error",
                    message=f"Bot stopped: {reason}",
                    symbol=symbol_name
                )
                log_repo.create(log.__dict__)
                config.is_bot_active = False
                config_repo.update(config, {"is_bot_active": False})
                return

            symbol = symbol_repo.get_by_name(symbol_name)
            if not symbol:
                logger.error(f"Symbol {symbol_name} not found in DB")
                return

            candles = candle_repo.get_by_symbol_timeframe(
                symbol.id,
                timeframe,
                limit=300
            )
            if not candles or len(candles) < 200:
                logger.warning(f"Not enough candles for {symbol_name}")
                return

            strategy_class = self.strategies.get(config.selected_strategy)
            if not strategy_class:
                logger.error(f"Strategy {config.selected_strategy} not found")
                return
            strategy = strategy_class()

            candles_dict_list = []
            for c in candles:
                candles_dict_list.append({
                    "symbol_name": symbol_name,
                    "open": float(c.open),
                    "high": float(c.high),
                    "low": float(c.low),
                    "close": float(c.close),
                    "time": c.time
                })
            current_tick = self.mt5.get_tick(symbol_name)
            if not current_tick:
                logger.warning(f"Live tick not available for {symbol_name}")
                return

            current_price = current_tick["ask"]

            signal = strategy.generate_signal(candles_dict_list, current_price)

            if signal and strategy.validate_entry(signal, candles_dict_list):
                log = LogEntry(
                    account_id=config.account_id,
                    log_type="signal",
                    message=f"Generated {signal.signal_type} signal on {signal.symbol} @ {current_price}",
                    symbol=signal.symbol
                )
                log_repo.create(log.__dict__)
                logger.info(f"Generated {signal.signal_type} signal on {signal.symbol}")

                open_positions = position_repo.get_open_positions(config.account_id)
                if len(open_positions) >= config.max_open_trades:
                    logger.warning("Max open trades limit hit")
                    return

                lot_size = float(config.lot_size)
                sl = strategy.calculate_stop_loss(current_price, signal.signal_type, candles_dict_list)
                tp = strategy.calculate_take_profit(current_price, signal.signal_type, candles_dict_list)

                try:
                    if signal.signal_type == "buy":
                        result = self.mt5.open_buy_order(
                            symbol_name,
                            lot_size,
                            sl if sl > 0 else None,
                            tp if tp > 0 else None
                        )
                    else:
                        result = self.mt5.open_sell_order(
                            symbol_name,
                            lot_size,
                            sl if sl > 0 else None,
                            tp if tp > 0 else None
                        )

                    if result and result.retcode == 10009:
                        log = LogEntry(
                            account_id=config.account_id,
                            log_type="open_trade",
                            message=f"Opened {signal.signal_type} trade on {symbol_name}",
                            symbol=symbol_name
                        )
                        log_repo.create(log.__dict__)
                        logger.info(f"Opened {signal.signal_type} trade on {symbol_name}")
                    else:
                        error_msg = result.comment if hasattr(result, 'comment') else "Unknown error"
                        log = LogEntry(
                            account_id=config.account_id,
                            log_type="error",
                            message=f"Failed to open trade: {error_msg}",
                            symbol=symbol_name
                        )
                        log_repo.create(log.__dict__)
                        logger.error(f"Failed to open trade: {error_msg}")
                except Exception as e:
                    log = LogEntry(
                        account_id=config.account_id,
                        log_type="error",
                        message=f"Exception opening trade: {str(e)}",
                        symbol=symbol_name
                    )
                    log_repo.create(log.__dict__)
                    logger.error(f"Exception opening trade: {str(e)}")

            # Manage existing positions (trailing stop, breakeven)
            self.manage_positions(config, position_repo, log_repo, db)

        except Exception as e:
            logger.error(f"Strategy runner error: {str(e)}", exc_info=True)
        finally:
            db.close()

    def manage_positions(self, config, position_repo, log_repo, db):
        open_positions = position_repo.get_open_positions(config.account_id)
        for pos in open_positions:
            symbol_name = None
            if hasattr(pos, 'symbol') and pos.symbol:
                symbol_name = pos.symbol.name
            if not symbol_name:
                continue

            try:
                current_tick = self.mt5.get_tick(symbol_name)
                if not current_tick:
                    continue

                current_price = current_tick['ask'] if pos.position_type == "buy" else current_tick['bid']

                if config.trailing_stop_enabled:
                    self.apply_trailing_stop(pos, current_price, config)
                if config.breakeven_enabled:
                    self.apply_breakeven(pos, current_price, config)
            except Exception as e:
                logger.error(f"Error managing position {pos.mt5_ticket}: {str(e)}")

    def apply_trailing_stop(self, position, current_price, config):
        point = 0.0001 if position.symbol.name not in ["XAUUSD", "XAGUSD"] else 0.01
        if position.position_type == "buy":
            new_sl = current_price - (config.trailing_stop_pips * point)
            if new_sl > (position.sl or 0):
                self.mt5.modify_position_sl_tp(position.mt5_ticket, new_sl, position.tp)
        else:
            new_sl = current_price + (config.trailing_stop_pips * point)
            if new_sl < (position.sl or float('inf')):
                self.mt5.modify_position_sl_tp(position.mt5_ticket, new_sl, position.tp)

    def apply_breakeven(self, position, current_price, config):
        point = 0.0001 if position.symbol.name not in ["XAUUSD", "XAGUSD"] else 0.01
        if position.position_type == "buy":
            breakeven_price = position.open_price + (config.breakeven_pips * point)
            if current_price >= breakeven_price and (position.sl is None or position.sl < position.open_price):
                self.mt5.modify_position_sl_tp(position.mt5_ticket, position.open_price, position.tp)
        else:
            breakeven_price = position.open_price - (config.breakeven_pips * point)
            if current_price <= breakeven_price and (position.sl is None or position.sl > position.open_price):
                self.mt5.modify_position_sl_tp(position.mt5_ticket, position.open_price, position.tp)


strategy_runner = StrategyRunner()
