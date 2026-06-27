from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database.session import get_db
from app.infrastructure.mt5.connector import get_mt5_connector, MT5Connector
from app.core.config.settings import settings
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    database: str
    mt5: str
    version: str


@router.get("", response_model=HealthStatus)
async def health_check(
    db: Session = Depends(get_db),
    mt5: MT5Connector = Depends(get_mt5_connector)
):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unhealthy"

    mt5_status = "connected" if mt5.is_connected() else "disconnected"
    overall_status = "healthy" if db_status == "healthy" else "unhealthy"

    return HealthStatus(
        status=overall_status,
        database=db_status,
        mt5=mt5_status,
        version=settings.APP_VERSION
    )


@router.post("/mt5/connect")
async def connect_mt5(mt5: MT5Connector = Depends(get_mt5_connector)):
    try:
        success = mt5.connect()
        return {"status": "success" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/mt5/disconnect")
async def disconnect_mt5(mt5: MT5Connector = Depends(get_mt5_connector)):
    mt5.disconnect()
    return {"status": "success"}
