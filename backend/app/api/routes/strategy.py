from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database.session import get_db
from app.core.security import get_current_user
from app.api.schemas.schemas import (
    StrategyConfig,
    StrategyConfigCreate,
    StrategyConfigUpdate,
    LogEntry,
    AccountOverview,
    BotControlRequest,
    User,
)
from app.infrastructure.database.repositories import (
    StrategyConfigRepository,
    LogEntryRepository,
    AccountRepository,
)
from app.infrastructure.mt5.connector import get_mt5_connector, MT5Connector
from app.domain.models.account import Account

router = APIRouter(prefix="/strategy", tags=["Strategy"])


# Create a Pydantic schema for Account if it doesn't exist
from pydantic import BaseModel

class AccountResponse(BaseModel):
    id: int
    login: int
    server: str
    account_type: str
    broker: str
    is_active: bool
    
    class Config:
        from_attributes = True


@router.get("/accounts", response_model=List[AccountResponse])
def get_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account_repo = AccountRepository(db)
    accounts = account_repo.get_all()
    return accounts


def get_strategy_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return StrategyConfigRepository(db), LogEntryRepository(db)


@router.get("/config/{account_id}", response_model=StrategyConfig)
def get_strategy_config(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = StrategyConfigRepository(db)
    config = repo.get_by_account_id(account_id)
    if not config:
        # Create default config if not exists
        config = repo.create({
            "account_id": account_id,
            "selected_strategy": "EMATrendStrategy",
            "risk_percent": 1.0,
            "max_daily_loss": 100.0,
            "max_weekly_loss": 500.0,
            "lot_size": 0.1,
            "max_open_trades": 5,
            "max_consecutive_losses": 3,
            "is_bot_active": False,
            "is_paused": False,
            "safety_mode": True,
            "schedule_timeframe": "H1",
            "trailing_stop_enabled": False,
            "trailing_stop_pips": 50,
            "breakeven_enabled": False,
            "breakeven_pips": 30,
        })
    return config


@router.put("/config/{account_id}", response_model=StrategyConfig)
def update_strategy_config(
    account_id: int,
    config_update: StrategyConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = StrategyConfigRepository(db)
    config = repo.get_by_account_id(account_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    update_data = config_update.model_dump(exclude_unset=True)
    return repo.update(config, update_data)


@router.post("/control", response_model=StrategyConfig)
def bot_control(
    request: BotControlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = StrategyConfigRepository(db)
    account_repo = AccountRepository(db)
    # Assume first account for now
    account = account_repo.get_all()[0]
    config = repo.get_by_account_id(account.id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    update_data = {}
    if request.action == "start":
        update_data["is_bot_active"] = True
        update_data["is_paused"] = False
    elif request.action == "stop":
        update_data["is_bot_active"] = False
        update_data["is_paused"] = False
    elif request.action == "pause":
        update_data["is_paused"] = True
    elif request.action == "resume":
        update_data["is_paused"] = False
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")
    return repo.update(config, update_data)


@router.get("/logs/{account_id}", response_model=List[LogEntry])
def get_logs(
    account_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = LogEntryRepository(db)
    return repo.get_by_account_id(account_id, skip, limit)


@router.post("/logs", response_model=LogEntry)
def create_log(
    log_data: LogEntry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = LogEntryRepository(db)
    return repo.create(log_data.model_dump())


@router.get("/account-overview/{account_id}", response_model=AccountOverview)
def get_account_overview(
    account_id: int,
    db: Session = Depends(get_db),
    mt5: MT5Connector = Depends(get_mt5_connector),
    current_user: User = Depends(get_current_user),
):
    from app.application.services.strategy_runner import strategy_runner
    config_repo = StrategyConfigRepository(db)
    config = config_repo.get_by_account_id(account_id)
    
    daily_pnl = 0.0
    weekly_pnl = 0.0
    try:
        daily_pnl = float(strategy_runner.calculate_daily_pnl(account_id, db))
        weekly_pnl = float(strategy_runner.calculate_weekly_pnl(account_id, db))
    except:
        pass
    
    if not mt5.is_connected():
        # Return demo data if MT5 not connected
        return AccountOverview(
            balance=10000.0,
            equity=10000.0,
            free_margin=10000.0,
            profit=0.0,
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            active_strategy=config.selected_strategy if config else None,
            current_signal=None
        )
    
    mt5_info = mt5.get_account_info()
    if not mt5_info:
        # Return demo data if MT5 info not available
        return AccountOverview(
            balance=10000.0,
            equity=10000.0,
            free_margin=10000.0,
            profit=0.0,
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            active_strategy=config.selected_strategy if config else None,
            current_signal=None
        )
    
    return AccountOverview(
        balance=float(mt5_info.balance),
        equity=float(mt5_info.equity),
        free_margin=float(mt5_info.margin_free),
        profit=float(mt5_info.profit),
        daily_pnl=daily_pnl,
        weekly_pnl=weekly_pnl,
        active_strategy=config.selected_strategy if config else None,
        current_signal=None  # Can be enhanced to store last signal
    )
