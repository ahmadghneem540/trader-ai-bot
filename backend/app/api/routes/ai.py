from fastapi import APIRouter, HTTPException, status, Depends
from app.application.services.ai_service import ai_service
from app.infrastructure.mt5.connector import MT5Connector, get_mt5_connector
from app.core.logging.logger import get_logger
from app.api.schemas.schemas import AIAnalyzeRequest, AIAnalyzeResponse, GenericResponse, TradingPanelRequest
from typing import List, Optional

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/test")
async def test_ai():
    try:
        result = await ai_service.test_connection()
        return result
    except ValueError as e:
        logger.error(f"AI service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error in AI test endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while communicating with the AI service"
        )


@router.post("/analyze", response_model=AIAnalyzeResponse)
async def analyze_candles(request: AIAnalyzeRequest):
    try:
        # Convert candles to dicts
        candles_dicts = [candle.model_dump() for candle in request.candles]
        result = await ai_service.analyze_candles(request.symbol, request.timeframe, candles_dicts)
        return result
    except ValueError as e:
        logger.error(f"AI service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error in AI analyze endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while communicating with the AI service"
        )


@router.post("/auto-trade", response_model=GenericResponse[dict])
async def auto_trade(
    request: TradingPanelRequest, 
    symbol: Optional[str] = "XAUUSD", 
    timeframe: Optional[str] = "H1", 
    mt5_connector: MT5Connector = Depends(get_mt5_connector)
):
    try:
        # 1. Check if MT5 is connected
        if not mt5_connector.is_connected():
            return GenericResponse(
                success=False,
                message="MT5 not connected",
                data=None,
                error=None
            )
        
        # 2. Get candles from MT5
        candles = mt5_connector.get_candles(symbol, timeframe, 200)
        if not candles:
            return GenericResponse(
                success=False,
                message="Failed to get candles from MT5",
                data=None,
                error=None
            )
        
        # 3. Analyze with AI
        analysis = await ai_service.analyze_candles(symbol, timeframe, candles)
        
        # 4. Decide whether to trade
        action = None
        if analysis.get("confidence", 0) > 70:
            if analysis.get("trend") == "bullish":
                action = "buy"
                result = mt5_connector.open_buy_order(symbol, request.volume, request.sl, request.tp)
            elif analysis.get("trend") == "bearish":
                action = "sell"
                result = mt5_connector.open_sell_order(symbol, request.volume, request.sl, request.tp)
        
        # 5. Return result
        return GenericResponse(
            success=True,
            message="AI auto-trade executed",
            data={
                "analysis": analysis,
                "action": action
            }
        )
        
    except Exception as e:
        logger.exception(f"AI auto-trade error: {str(e)}")
        return GenericResponse(
            success=False,
            message=str(e),
            data=None,
            error=None
        )
