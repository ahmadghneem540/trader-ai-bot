from typing import Optional, Dict, Any, List
from app.core.config.settings import settings
from app.core.logging.logger import get_logger
import asyncio
import traceback
from datetime import datetime, timedelta

logger = get_logger(__name__)

try:
    from metaapi_cloud_sdk import MetaApi
    META_API_AVAILABLE = True
except ImportError:
    META_API_AVAILABLE = False
    logger.warning("metaapi-cloud-sdk not available - MetaApi features disabled")


class MetaApiConnector:
    _instance: Optional["MetaApiConnector"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._connected: bool = False
        self._demo_mode: bool = not META_API_AVAILABLE
        self._api = None
        self._account = None
        self._connection = None
        self._credentials: Dict[str, Any] = {}
        self._debug_info: Dict[str, Any] = {}
        self._initialized = True
        
        if META_API_AVAILABLE and settings.META_API_TOKEN:
            try:
                self._api = MetaApi(settings.META_API_TOKEN)
                logger.info("MetaApi initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MetaApi: {str(e)}")

    async def _get_account(self, account_id: Optional[str] = None):
        """Get or create a MetaTrader account on MetaApi"""
        if not self._api:
            raise Exception("MetaApi not initialized")
        
        account_id = account_id or settings.META_API_ACCOUNT_ID
        
        if not account_id:
            raise Exception("No MetaApi account ID not configured")
        
        accounts = await self._api.metatrader_account_api.get_accounts()
        account = next((a for a in accounts if a.id == account_id), None)
        
        if not account:
            raise Exception(f"Account {account_id} not found")
        
        return account

    async def connect(self, login: int, password: str, server: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Connect to MetaTrader account via MetaApi"""
        try:
            if self._demo_mode:
                self._connected = True
                self._credentials = {"login": login, "server": server}
                return {"success": True, "message": "Connected in demo mode"}
            
            account = await self._get_account(account_id)
            
            if account.state != "DEPLOYED":
                await account.deploy()
                await account.wait_deployed()
            
            self._connection = await account.connect()
            await self._connection.wait_synchronized({"timeoutInSeconds": 300})
            
            self._connected = True
            self._credentials = {"login": login, "password": password, "server": server}
            self._account = account
            
            logger.info(f"Connected to MetaTrader account {login} via MetaApi")
            return {"success": True, "message": "Connected successfully"}
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Failed to connect via MetaApi: {str(e)}\n{error_trace}")
            return {
                "success": False,
                "error": str(e),
                "traceback": error_trace
            }

    def disconnect(self):
        """Disconnect from MetaApi"""
        self._connected = False
        self._connection = None
        self._account = None
        logger.info("Disconnected from MetaApi")

    def is_connected(self) -> bool:
        return self._connected

    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        if self._demo_mode:
            return {
                "login": self._credentials.get("login", 0),
                "name": "Demo Account",
                "server": self._credentials.get("server", ""),
                "balance": 10000.0,
                "equity": 10000.0,
                "margin": 0.0,
                "margin_free": 10000.0,
                "profit": 0.0,
                "currency": "USD",
                "leverage": 100
            }
        
        if not self._connection:
            return None
        
        try:
            account_info = await self._connection.get_account_information()
            return account_info
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return None

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        if self._demo_mode:
            return []
        
        if not self._connection:
            return []
        
        try:
            positions = await self._connection.get_positions()
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return []

    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders"""
        if self._demo_mode:
            return []
        
        if not self._connection:
            return []
        
        try:
            orders = await self._connection.get_orders()
            return orders
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            return []

    async def get_deal_history(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        """Get deal history"""
        if self._demo_mode:
            return []
        
        if not self._connection:
            return []
        
        try:
            deals = await self._connection.get_deals_by_time_range(
                from_time=date_from.isoformat(),
                to_time=date_to.isoformat()
            )
            return deals
        except Exception as e:
            logger.error(f"Failed to get deal history: {str(e)}")
            return []

    async def get_candles(self, symbol: str, timeframe: str, count: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get candles"""
        if self._demo_mode:
            import random
            import time
            now = int(time.time())
            timeframe_seconds = {
                "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
                "H1": 3600, "H4": 14400, "D1": 86400
            }
            dt = timeframe_seconds.get(timeframe, 3600)
            candles = []
            current_price = 3000.0
            for i in range(count):
                t = now - (count - i - 1) * dt
                change = random.uniform(-10, 10)
                open_p = current_price
                close_p = open_p + change
                high_p = max(open_p, close_p) + random.uniform(0, 5)
                low_p = min(open_p, close_p) - random.uniform(0, 5)
                candles.append({
                    "time": t,
                    "open": round(open_p, 2),
                    "high": round(high_p, 2),
                    "low": round(low_p, 2),
                    "close": round(close_p, 2)
                })
                current_price = close_p
            return candles
        
        if not self._connection:
            return None
        
        try:
            timeframe_map = {
                "M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
                "H1": "1h", "H4": "4h", "D1": "1d"
            }
            candles = await self._connection.get_candles(
                symbol, timeframe_map.get(timeframe, "1h"), count
            )
            return candles
        except Exception as e:
            logger.error(f"Failed to get candles: {str(e)}")
            return None

    async def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get tick data"""
        if self._demo_mode:
            import random
            import time
            base_price = 3000.0
            return {
                "time": int(time.time()),
                "bid": base_price + random.uniform(-5, 5),
                "ask": base_price + random.uniform(-4.5, 5.5),
                "last": base_price + random.uniform(-4.7, 5.3),
                "volume": random.randint(1, 100)
            }
        
        if not self._connection:
            return None
        
        try:
            tick = await self._connection.get_symbol_price(symbol)
            return tick
        except Exception as e:
            logger.error(f"Failed to get tick: {str(e)}")
            return None

    async def open_buy_order(self, symbol: str, volume: float, sl: Optional[float] = None, tp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Open buy order"""
        if self._demo_mode:
            return {"retcode": 10009, "order": 123456, "comment": "Demo order"}
        
        if not self._connection:
            return None
        
        try:
            result = await self._connection.create_market_buy_order(
                symbol, volume, stop_loss=sl, take_profit=tp
            )
            return result
        except Exception as e:
            logger.error(f"Failed to open buy order: {str(e)}")
            return None

    async def open_sell_order(self, symbol: str, volume: float, sl: Optional[float] = None, tp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Open sell order"""
        if self._demo_mode:
            return {"retcode": 10009, "order": 123457, "comment": "Demo order"}
        
        if not self._connection:
            return None
        
        try:
            result = await self._connection.create_market_sell_order(
                symbol, volume, stop_loss=sl, take_profit=tp
            )
            return result
        except Exception as e:
            logger.error(f"Failed to open sell order: {str(e)}")
            return None

    async def close_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Close position"""
        if self._demo_mode:
            return {"retcode": 10009, "comment": "Demo close"}
        
        if not self._connection:
            return None
        
        try:
            result = await self._connection.close_position(position_id)
            return result
        except Exception as e:
            logger.error(f"Failed to close position: {str(e)}")
            return None

    async def close_all_positions(self) -> List[Dict[str, Any]]:
        """Close all positions"""
        if self._demo_mode:
            return [{"retcode": 10009, "comment": "Demo close all"}]
        
        if not self._connection:
            return []
        
        try:
            positions = await self.get_open_positions()
            results = []
            for position in positions:
                result = await self.close_position(position["id"])
                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Failed to close all positions: {str(e)}")
            return []

    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        return {
            "connected": self._connected,
            "demo_mode": self._demo_mode,
            "metaapi_available": META_API_AVAILABLE,
            "credentials": {k: "***" if k == "password" else v for k, v in self._credentials.items()}
        }

    async def get_symbols(self) -> List[str]:
        """Get available symbols"""
        if self._demo_mode:
            return ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        
        if not self._connection:
            return []
        
        try:
            symbols = await self._connection.get_symbols()
            return symbols
        except Exception as e:
            logger.error(f"Failed to get symbols: {str(e)}")
            return []


_metaapi_connector: Optional[MetaApiConnector] = None


def get_metaapi_connector() -> MetaApiConnector:
    global _metaapi_connector
    if _metaapi_connector is None:
        _metaapi_connector = MetaApiConnector()
    return _metaapi_connector
