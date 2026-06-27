from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database.session import get_db
from app.infrastructure.mt5.connector import get_mt5_connector, MT5Connector
from app.application.services.symbol_service import SymbolService
from app.api.schemas.schemas import Symbol

router = APIRouter(prefix="/symbols", tags=["Symbols"])


def get_symbol_service(
    db: Session = Depends(get_db),
    mt5_connector: MT5Connector = Depends(get_mt5_connector)
) -> SymbolService:
    return SymbolService(db, mt5_connector)


@router.get("", response_model=List[Symbol])
def get_all_symbols(service: SymbolService = Depends(get_symbol_service)):
    return service.get_all_symbols()


@router.get("/{name}", response_model=Symbol)
def get_symbol(name: str, service: SymbolService = Depends(get_symbol_service)):
    symbol = service.get_symbol_by_name(name)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return symbol


@router.post("/sync/{name}", response_model=Symbol)
def sync_symbol(name: str, service: SymbolService = Depends(get_symbol_service)):
    symbol = service.sync_symbol_from_mt5(name)
    if not symbol:
        raise HTTPException(status_code=404, detail="Failed to sync symbol")
    return symbol


@router.post("/sync-all", response_model=List[Symbol])
def sync_all_symbols(service: SymbolService = Depends(get_symbol_service)):
    return service.sync_all_symbols_from_mt5()
