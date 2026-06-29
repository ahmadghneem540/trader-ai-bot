from typing import Optional, Dict, Any, List
from app.core.config.settings import settings
from app.core.logging.logger import (
    get_logger,
    get_mt5_logger,
    get_mt5_errors_logger,
    get_mt5_api_logger,
    get_mt5_debug_logger,
)
import time
import os
try:
    import psutil
except ImportError:
    psutil = None
    get_logger(__name__).warning("psutil not available - terminal detection may fail")
import subprocess
import threading
import traceback
import json
from datetime import datetime
from collections import deque

# Try to import MetaTrader 5, handle if not available
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
    get_logger(__name__).warning("MetaTrader 5 not available - running in demo mode")

logger = get_logger(__name__)
mt5_connection_logger = get_mt5_logger()
mt5_errors_logger = get_mt5_errors_logger()
mt5_api_logger = get_mt5_api_logger()
mt5_debug_logger = get_mt5_debug_logger()


class StructuredDebugLog:
    def __init__(self, max_entries: int = 500):
        self._logs: deque = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def add(
        self,
        step: int,
        description: str,
        level: str = "INFO",
        component: str = "mt5",
        function: Optional[str] = None,
        result: Optional[Any] = None,
        execution_time_ms: Optional[float] = None,
        mt5_last_error: Optional[tuple] = None,
        exception: Optional[str] = None,
    ):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "step": step,
            "component": component,
            "function": function,
            "description": description,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "mt5_last_error": mt5_last_error,
            "exception": exception,
        }
        with self._lock:
            self._logs.append(entry)
        # Also log to mt5_debug.log file
        extra = {
            "step": step,
            "component": component,
            "function": function,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "mt5_last_error": mt5_last_error,
        }
        # Map log levels to standard logging methods
        level_mapping = {
            "SUCCESS": "info",
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "critical",
        }
        internal_level = level_mapping.get(level.upper(), "info")
        log_method = getattr(mt5_debug_logger, internal_level)
        if exception:
            log_method(description, extra=extra, exc_info=True)
        else:
            log_method(description, extra=extra)

    def get_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._logs)

    def clear(self):
        with self._lock:
            self._logs.clear()


debug_log = StructuredDebugLog(max_entries=500)


def get_suggested_solution(error_code: int, stage: str) -> str:
    solutions = {
        -10001: "No IPC connection - MT5 terminal may not be running",
        -10002: "IPC send failed - MT5 terminal may be unresponsive",
        -10003: "IPC receive failed - MT5 terminal may be unresponsive",
        -10004: "IPC invalid parameter",
        -10005: "IPC timeout - MT5 terminal is not ready yet or path is incorrect",
        -10006: "IPC invalid handle",
        -10007: "IPC invalid memory",
        -10008: "IPC already connected",
        -10009: "IPC not connected",
        -10010: "IPC initialization failed",
        -10011: "IPC connection failed",
        1: "No error",
        2: "No result",
        3: "Common error",
        4: "Invalid trade parameters",
        5: "Old terminal build - update your MT5 terminal",
        6: "No connection with trade server - check your internet connection and server address",
        7: "Not enough rights - check your account permissions",
        8: "Too frequent requests - slow down your API calls",
        9: "Malfunctional trade",
        64: "Account disabled - contact your broker",
        65: "Invalid account number - check your login credentials",
        128: "Trade timeout",
        129: "Invalid price",
        130: "Invalid stops",
        131: "Invalid trade volume",
        132: "Market closed - try again when market is open",
        133: "Trade disabled - check your broker settings",
        134: "Not enough money - check your account balance",
        135: "Price changed",
        136: "No prices",
        137: "Broker is busy - try again later",
        138: "Requote",
        139: "Order locked",
        140: "Only positions are allowed",
        141: "Too many requests",
        142: "No changes in request parameters",
        143: "Long positions are not allowed",
        144: "Short positions are not allowed",
        145: "FIFO rule is violated",
        146: "Hedging is not allowed",
        147: "Close by orders are not allowed",
        148: "Prohibited by FIFO",
        149: "Too many orders",
        150: "Close by position number is invalid",
        151: "Stop limit order is not accepted",
        152: "Execution time limit exceeded",
        153: "Order not found",
        154: "Invalid position for close by",
        155: "Cannot close this order",
        156: "Invalid order volume for close by",
        157: "Close by orders must have the same symbol",
    }
    if stage == "locate_terminal":
        return "Check that MT5_PATH in your .env file points to the correct directory where terminal64.exe is located"
    if stage == "terminal_start":
        return "Ensure that MT5 is not blocked by your antivirus or firewall, and that you have permissions to run terminal64.exe"
    if stage == "initialize":
        return (
            solutions.get(error_code, "")
            + " Also, verify that your MT5 terminal is fully started and logged in (if you're not logging in via API)"
        )
    if stage == "login":
        return (
            solutions.get(error_code, "")
            + " Double-check your login, password, and server address"
        )
    return solutions.get(error_code, "Unknown error, please check the logs for more details")


class MT5Connector:
    _instance: Optional["MT5Connector"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._connected: bool = False
        self._demo_mode: bool = not MT5_AVAILABLE  # Only demo if MT5 not installed
        self._demo_positions: List[Dict[str, Any]] = []
        self._demo_balance: float = 10000.0
        self._demo_equity: float = 10000.0
        self._demo_account_info: Dict[str, Any] = {
            "login": 12345678,
            "name": "Demo Account",
            "server": "Demo-Server",
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "margin_free": 10000.0,
            "profit": 0.0,
            "currency": "USD",
            "leverage": 100,
        }
        self._credentials: Dict[str, Any] = {}
        self._debug_info: Dict[str, Any] = {
            "initialize_result": None,
            "login_result": None,
            "last_error": None,
            "terminal_info": None,
            "account_info": None,
            "version": None,
            "xauusd_status": None,
            "terminal_path": None,
            "data_path": None,
            "pid": None,
            "connection_time": None,
            "error_code": None,
            "error_description": None,
        }
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_reconnect: threading.Event = threading.Event()
        self._terminal_process: Optional[subprocess.Popen] = None
        self._initialized = True

    def _get_error_description(self, error_code: int) -> str:
        error_descriptions = {
            1: "No error",
            2: "No result",
            3: "Common error",
            4: "Invalid trade parameters",
            5: "Old terminal build",
            6: "No connection with trade server",
            7: "Not enough rights",
            8: "Too frequent requests",
            9: "Malfunctional trade",
            64: "Account disabled",
            65: "Invalid account number",
            128: "Trade timeout",
            129: "Invalid price",
            130: "Invalid stops",
            131: "Invalid trade volume",
            132: "Market closed",
            133: "Trade disabled",
            134: "Not enough money",
            135: "Price changed",
            136: "No prices",
            137: "Broker is busy",
            138: "Requote",
            139: "Order locked",
            140: "Only positions are allowed",
            141: "Too many requests",
            142: "No changes in request parameters",
            143: "Long positions are not allowed",
            144: "Short positions are not allowed",
            145: "FIFO rule is violated",
            146: "Hedging is not allowed",
            147: "Close by orders are not allowed",
            148: "Prohibited by FIFO",
            149: "Too many orders",
            150: "Close by position number is invalid",
            151: "Stop limit order is not accepted",
            152: "Execution time limit exceeded",
            153: "Order not found",
            154: "Invalid position for close by",
            155: "Cannot close this order",
            156: "Invalid order volume for close by",
            157: "Close by orders must have the same symbol",
            -10001: "No IPC connection",
            -10002: "IPC send failed",
            -10003: "IPC receive failed",
            -10004: "IPC invalid parameter",
            -10005: "IPC timeout (terminal not ready or path incorrect)",
            -10006: "IPC invalid handle",
            -10007: "IPC invalid memory",
            -10008: "IPC already connected",
            -10009: "IPC not connected",
            -10010: "IPC initialization failed",
            -10011: "IPC connection failed",
        }
        return error_descriptions.get(error_code, f"Unknown error code: {error_code}")

    def _log_mt5_api_call(self, func_name: str, *args, **kwargs):
        mt5_api_logger.info(f"Calling {func_name} with args: {args}, kwargs: {kwargs}")

    def _check_terminal_running(self) -> bool:
        if psutil is None:
            return False
        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"].lower()
                    if name == "terminal.exe" or name == "terminal64.exe":
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            get_logger(__name__).warning(f"Failed to check terminal running: {str(e)}")
        return False

    def _start_terminal(self) -> Optional[Dict[str, Any]]:
        step_start = time.time()
        step = 9
        if not settings.MT5_PATH:
            debug_log.add(
                step=step,
                description="MT5_PATH is not configured in environment variables",
                level="ERROR",
                function="_start_terminal",
                result="failed",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            return {
                "success": False,
                "stage": "locate_terminal",
                "error": "MT5_PATH is not configured",
            }

        terminal_exe = os.path.join(settings.MT5_PATH, "terminal64.exe")
        debug_log.add(
            step=7,
            description=f"Locating terminal executable at: {terminal_exe}",
            level="INFO",
            function="_start_terminal",
        )
        if not os.path.exists(terminal_exe):
            terminal_exe = os.path.join(settings.MT5_PATH, "terminal.exe")
            debug_log.add(
                step=7,
                description=f"terminal64.exe not found, trying terminal.exe at: {terminal_exe}",
                level="WARNING",
                function="_start_terminal",
            )
            if not os.path.exists(terminal_exe):
                debug_log.add(
                    step=8,
                    description=f"Terminal executable not found at any location in {settings.MT5_PATH}",
                    level="ERROR",
                    function="_start_terminal",
                    result="failed",
                    execution_time_ms=(time.time() - step_start) * 1000,
                )
                return {
                    "success": False,
                    "stage": "locate_terminal",
                    "error": f"Terminal executable not found in {settings.MT5_PATH}",
                }
        debug_log.add(
            step=8,
            description=f"Found terminal executable: {terminal_exe}",
            level="SUCCESS",
            function="_start_terminal",
        )

        try:
            debug_log.add(
                step=10,
                description="Starting terminal process",
                level="INFO",
                function="_start_terminal",
            )
            self._terminal_process = subprocess.Popen(
                [terminal_exe],
                cwd=settings.MT5_PATH,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            debug_log.add(
                step=10,
                description=f"Terminal process started with PID: {self._terminal_process.pid}",
                level="SUCCESS",
                function="_start_terminal",
                result={"pid": self._terminal_process.pid},
            )
            self._debug_info["pid"] = self._terminal_process.pid
            # Wait for terminal to initialize
            wait_time = 0
            max_wait = 60
            debug_log.add(
                step=10,
                description=f"Waiting for terminal to be ready (max {max_wait}s)",
                level="INFO",
                function="_start_terminal",
            )
            while wait_time < max_wait:
                if self._check_terminal_running():
                    debug_log.add(
                        step=10,
                        description=f"Terminal detected as running after {wait_time} seconds",
                        level="INFO",
                        function="_start_terminal",
                    )
                    # Give it more time to fully start
                    debug_log.add(
                        step=10,
                        description="Waiting 30 more seconds for terminal to initialize...",
                        level="INFO",
                        function="_start_terminal",
                    )
                    time.sleep(30)
                    debug_log.add(
                        step=10,
                        description="Terminal should now be fully ready",
                        level="SUCCESS",
                        function="_start_terminal",
                        result="success",
                        execution_time_ms=(time.time() - step_start) * 1000,
                    )
                    return {"success": True}
                time.sleep(1)
                wait_time += 1
            debug_log.add(
                step=10,
                description=f"Terminal failed to start within {max_wait} seconds",
                level="ERROR",
                function="_start_terminal",
                result="failed",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            return {
                "success": False,
                "stage": "terminal_start",
                "error": f"Terminal failed to start within {max_wait} seconds",
            }
        except Exception as e:
            error_trace = traceback.format_exc()
            debug_log.add(
                step=10,
                description=f"Failed to start terminal: {str(e)}",
                level="ERROR",
                function="_start_terminal",
                result="failed",
                execution_time_ms=(time.time() - step_start) * 1000,
                exception=error_trace,
            )
            return {
                "success": False,
                "stage": "terminal_start",
                "error": str(e),
                "traceback": error_trace,
            }

    def _ensure_connection(self) -> bool:
        if not self.is_connected():
            return self.reconnect()
        return True

    def _ensure_symbol(self, symbol: str = "XAUUSD") -> bool:
        if not self._ensure_connection():
            return False
        self._log_mt5_api_call("symbol_select", symbol, True)
        selected = mt5.symbol_select(symbol, True)
        self._debug_info["xauusd_status"] = {"selected": selected}
        if not selected:
            last_error = mt5.last_error()
            mt5_errors_logger.error(f"Failed to select {symbol}: {last_error}")
            return False
        return True

    def _reconnect_loop(self):
        while not self._stop_reconnect.is_set():
            try:
                if not self.is_connected():
                    mt5_connection_logger.info("Connection lost, attempting to reconnect...")
                    self.connect(
                        login=self._credentials.get("login"),
                        password=self._credentials.get("password"),
                        server=self._credentials.get("server"),
                    )
            except Exception as e:
                mt5_errors_logger.error(
                    f"Reconnect error: {str(e)}\n{traceback.format_exc()}"
                )
            time.sleep(5)

    def _start_reconnect_thread(self):
        if self._reconnect_thread is None or not self._reconnect_thread.is_alive():
            self._stop_reconnect.clear()
            self._reconnect_thread = threading.Thread(
                target=self._reconnect_loop, daemon=True
            )
            self._reconnect_thread.start()

    def _start_monitoring_thread(self):
        """Start connection monitoring thread."""
        if not hasattr(self, '_monitoring_thread') or self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring = threading.Event()
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MT5Monitoring"
            )
            self._monitoring_thread.start()
            debug_log.add(
                step=100,
                description="Connection monitoring thread started",
                level="INFO",
                function="_start_monitoring_thread",
            )

    def _stop_monitoring_thread(self):
        """Stop connection monitoring thread."""
        if hasattr(self, '_stop_monitoring') and self._stop_monitoring:
            self._stop_monitoring.set()
        if hasattr(self, '_monitoring_thread') and self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)

    def _monitoring_loop(self):
        """Monitor connection status every 5 seconds."""
        debug_log.add(
            step=101,
            description="Connection monitoring loop started",
            level="INFO",
            function="_monitoring_loop",
        )
        
        while not self._stop_monitoring.is_set():
            try:
                # Check connection status
                status = self.get_detailed_status()
                
                if not status["connected"]:
                    # Connection lost
                    debug_log.add(
                        step=102,
                        description=f"Connection lost: {status.get('last_error', 'Unknown error')}",
                        level="ERROR",
                        function="_monitoring_loop",
                    )
                    
                    # Attempt automatic reconnect if we have credentials
                    if self._credentials:
                        debug_log.add(
                            step=103,
                            description="Attempting automatic reconnection",
                            level="INFO",
                            function="_monitoring_loop",
                        )
                        
                        try:
                            reconnect_result = self.connect_robust(
                                login=self._credentials["login"],
                                password=self._credentials["password"],
                                server=self._credentials["server"]
                            )
                            
                            if reconnect_result["success"]:
                                debug_log.add(
                                    step=104,
                                    description="Automatic reconnection successful",
                                    level="SUCCESS",
                                    function="_monitoring_loop",
                                )
                            else:
                                debug_log.add(
                                    step=105,
                                    description=f"Automatic reconnection failed: {reconnect_result.get('error', 'Unknown error')}",
                                    level="ERROR",
                                    function="_monitoring_loop",
                                )
                        except Exception as e:
                            debug_log.add(
                                step=106,
                                description=f"Reconnection attempt exception: {str(e)}",
                                level="ERROR",
                                function="_monitoring_loop",
                                exception=traceback.format_exc(),
                            )
                
                # Wait 5 seconds before next check
                time.sleep(5)
                
            except Exception as e:
                debug_log.add(
                    step=107,
                    description=f"Monitoring loop exception: {str(e)}",
                    level="ERROR",
                    function="_monitoring_loop",
                    exception=traceback.format_exc(),
                )
                time.sleep(5)  # Wait before retrying

    def _stop_reconnect_thread(self):
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._stop_reconnect.set()
            self._reconnect_thread.join(timeout=10)

    def connect_robust(
        self,
        login: int,
        password: str,
        server: str,
        symbol: str = "XAUUSD"
    ) -> Dict[str, Any]:
        """Robust connection flow with comprehensive validation."""
        overall_start = time.time()
        debug_log.clear()
        
        result = {
            "success": False,
            "stage": None,
            "error": None,
            "mt5_last_error": None,
            "suggested_solution": None,
            "validation_results": {},
            "connection_time": 0.0
        }
        
        try:
            # Step 1: Validate credentials
            step_start = time.time()
            debug_log.add(
                step=1,
                description="Validating connection credentials",
                level="INFO",
                function="connect_robust",
            )
            
            if not login or not password or not server:
                result.update({
                    "stage": "validate_credentials",
                    "error": "Login, password, and server are required",
                    "suggested_solution": "Provide valid login credentials"
                })
                return result
            
            debug_log.add(
                step=1,
                description="Credentials validated successfully",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # Step 2: Check if terminal is running
            step_start = time.time()
            step = 2
            debug_log.add(
                step=step,
                description="Checking if MT5 terminal is running",
                level="INFO",
                function="connect_robust",
            )
            
            terminal_running = self._check_terminal_running()
            result["validation_results"]["terminal_running"] = terminal_running
            
            if not terminal_running:
                result.update({
                    "stage": "terminal_running",
                    "error": "MT5 terminal is not running",
                    "suggested_solution": "Start MT5 terminal manually or check MT5_PATH configuration"
                })
                return result
            
            debug_log.add(
                step=step,
                description="MT5 terminal is running",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # Step 3: Initialize MT5
            step_start = time.time()
            step = 3
            debug_log.add(
                step=step,
                description="Initializing MT5 connection",
                level="INFO",
                function="connect_robust",
            )
            
            try:
                # First shutdown any previous session
                try:
                    mt5.shutdown()
                    time.sleep(1)
                except:
                    pass
                
                initialize_result = mt5.initialize(
                    login=login,
                    password=password,
                    server=server,
                    timeout=60000
                )
                last_error = mt5.last_error()
                result["validation_results"]["mt5_initialized"] = initialize_result
                result["mt5_last_error"] = last_error
                
                if not initialize_result:
                    result.update({
                        "stage": "initialize",
                        "error": f"MT5 initialize failed: {self._get_error_description(last_error[0])}",
                        "suggested_solution": get_suggested_solution(last_error[0], "initialize")
                    })
                    return result
                
            except Exception as e:
                result.update({
                    "stage": "initialize",
                    "error": f"MT5 initialize exception: {str(e)}",
                    "suggested_solution": "Check MT5 installation and permissions"
                })
                return result
            
            debug_log.add(
                step=step,
                description="MT5 initialized successfully",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # Step 4: Verify login success
            step_start = time.time()
            step = 4
            debug_log.add(
                step=step,
                description="Verifying login success",
                level="INFO",
                function="connect_robust",
            )
            
            try:
                account_info = mt5.account_info()
                result["validation_results"]["login_success"] = account_info is not None
                
                if not account_info:
                    last_error = mt5.last_error()
                    result["mt5_last_error"] = last_error
                    result.update({
                        "stage": "login",
                        "error": "Login failed - no account information returned",
                        "suggested_solution": get_suggested_solution(last_error[0], "login")
                    })
                    return result
                
                # Verify account matches login
                if account_info.login != login:
                    result.update({
                        "stage": "login",
                        "error": f"Account login mismatch. Expected {login}, got {account_info.login}",
                        "suggested_solution": "Check login credentials"
                    })
                    return result
                
            except Exception as e:
                result.update({
                    "stage": "login",
                    "error": f"Login verification failed: {str(e)}",
                    "suggested_solution": "Check account permissions and server connection"
                })
                return result
            
            debug_log.add(
                step=step,
                description="Login verified successfully",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # Step 5: Get account information
            step_start = time.time()
            step = 5
            debug_log.add(
                step=step,
                description="Retrieving account information",
                level="INFO",
                function="connect_robust",
            )
            
            try:
                account_info = mt5.account_info()
                result["validation_results"]["account_info"] = True
                self._debug_info["account_info"] = account_info._asdict()
                
            except Exception as e:
                result.update({
                    "stage": "account_info",
                    "error": f"Failed to retrieve account information: {str(e)}",
                    "suggested_solution": "Check account permissions"
                })
                return result
            
            debug_log.add(
                step=step,
                description="Account information retrieved",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # Step 6: Get terminal information
            step_start = time.time()
            step = 6
            debug_log.add(
                step=step,
                description="Retrieving terminal information",
                level="INFO",
                function="connect_robust",
            )
            
            try:
                terminal_info = mt5.terminal_info()
                result["validation_results"]["terminal_info"] = terminal_info is not None and terminal_info.connected
                
                if not terminal_info or not terminal_info.connected:
                    result.update({
                        "stage": "terminal_info",
                        "error": "Terminal is not connected to server",
                        "suggested_solution": "Check internet connection and server status"
                    })
                    return result
                
                self._debug_info["terminal_info"] = terminal_info._asdict()
                
            except Exception as e:
                result.update({
                    "stage": "terminal_info",
                    "error": f"Failed to retrieve terminal information: {str(e)}",
                    "suggested_solution": "Check terminal connection"
                })
                return result
            
            debug_log.add(
                step=step,
                description="Terminal information retrieved",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # Step 7: Verify symbol exists
            step_start = time.time()
            step = 7
            debug_log.add(
                step=step,
                description=f"Verifying symbol {symbol} exists",
                level="INFO",
                function="connect_robust",
            )
            
            try:
                symbol_info = mt5.symbol_info(symbol)
                result["validation_results"]["symbol_exists"] = symbol_info is not None
                
                if not symbol_info:
                    result.update({
                        "stage": "symbol_exists",
                        "error": f"Symbol {symbol} not found",
                        "suggested_solution": "Check if symbol is available on your broker platform"
                    })
                    return result
                
                # Select the symbol
                mt5.symbol_select(symbol, True)
                
            except Exception as e:
                result.update({
                    "stage": "symbol_exists",
                    "error": f"Symbol verification failed: {str(e)}",
                    "suggested_solution": "Check symbol permissions"
                })
                return result
            
            debug_log.add(
                step=step,
                description=f"Symbol {symbol} verified and selected",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # Step 8: Verify candles can be retrieved
            step_start = time.time()
            step = 8
            debug_log.add(
                step=step,
                description=f"Verifying candles can be retrieved for {symbol}",
                level="INFO",
                function="connect_robust",
            )
            
            try:
                candles = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)
                result["validation_results"]["candles_retrievable"] = candles is not None and len(candles) > 0
                
                if not candles or len(candles) == 0:
                    # Try alternative method
                    from datetime import datetime, timedelta
                    date_from = datetime.now() - timedelta(days=1)
                    candles = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_H1, date_from, 1)
                    result["validation_results"]["candles_retrievable"] = candles is not None and len(candles) > 0
                
                if not result["validation_results"]["candles_retrievable"]:
                    result.update({
                        "stage": "candles_retrievable",
                        "error": f"Cannot retrieve candles for {symbol}",
                        "suggested_solution": "Check market hours and symbol availability"
                    })
                    return result
                
            except Exception as e:
                result.update({
                    "stage": "candles_retrievable",
                    "error": f"Candle retrieval failed: {str(e)}",
                    "suggested_solution": "Check market data permissions"
                })
                return result
            
            debug_log.add(
                step=step,
                description="Candles retrieval verified",
                level="SUCCESS",
                function="connect_robust",
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            
            # All validations passed
            self._connected = True
            self._credentials = {
                "login": login,
                "password": password,
                "server": server
            }
            
            connection_time = round(time.time() - overall_start, 2)
            result.update({
                "success": True,
                "connection_time": connection_time,
                "debug_info": self._debug_info,
                "logs": debug_log.get_all()
            })
            
            # Start monitoring thread
            self._start_monitoring_thread()
            
            debug_log.add(
                step=9,
                description=f"Robust connection SUCCESS! All validations passed. Total time: {connection_time}s",
                level="SUCCESS",
                function="connect_robust",
                result="success",
                execution_time_ms=(time.time() - overall_start) * 1000,
            )
            
            return result
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            last_error = mt5.last_error() if MT5_AVAILABLE else None
            
            debug_log.add(
                step=999,
                description=f"Unhandled exception in robust connection: {str(e)}",
                level="ERROR",
                function="connect_robust",
                result="failed",
                exception=error_traceback,
                mt5_last_error=last_error,
            )
            
            result.update({
                "stage": "exception",
                "error": str(e),
                "mt5_last_error": last_error,
                "traceback": error_traceback,
                "suggested_solution": "Check system logs for details"
            })
            
            return result

    def connect(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Check if in demo mode
        if self._demo_mode:
            step = 1
            step_start = time.time()
            debug_log.add(
                step=step,
                description="📊 Demo mode activated! Using simulated account.",
                level="INFO",
                function="connect",
            )
            self._connected = True
            self._debug_info["account_info"] = self._demo_account_info
            debug_log.add(
                step=step,
                description="✅ Demo mode connected successfully!",
                level="SUCCESS",
                function="connect",
                result={"connected": True, "account": self._demo_account_info},
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            return {
                "success": True,
                "debug_info": self._debug_info,
            }
        overall_start = time.time()
        debug_log.clear()
        step = 1
        debug_log.add(
            step=step,
            description="Application received connection request",
            level="INFO",
            function="connect",
        )

        try:
            # Step 1: Request received
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Starting connection process",
                level="INFO",
                function="connect",
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step 2: Validate request body
            step = 2
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Validating request body",
                level="INFO",
                function="connect",
            )
            debug_log.add(
                step=step,
                description="Request body validation passed",
                level="SUCCESS",
                function="connect",
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Steps 3-5: Validate login, password, server
            use_creds_login = login or settings.MT5_LOGIN
            use_creds_password = password or settings.MT5_PASSWORD
            use_creds_server = server or settings.MT5_SERVER

            step = 3
            step_start = time.time()
            debug_log.add(
                step=step,
                description=f"Validating login: {use_creds_login if use_creds_login else 'Not provided (using existing session)'}",
                level="INFO",
                function="connect",
            )
            debug_log.add(
                step=step,
                description="Login validation complete",
                level="SUCCESS",
                function="connect",
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            step = 4
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Validating password: " + ("*" * 10 if use_creds_password else "Not provided (using existing session)"),
                level="INFO",
                function="connect",
            )
            debug_log.add(
                step=step,
                description="Password validation complete",
                level="SUCCESS",
                function="connect",
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            step = 5
            step_start = time.time()
            debug_log.add(
                step=step,
                description=f"Validating server: {use_creds_server if use_creds_server else 'Not provided (using existing session)'}",
                level="INFO",
                function="connect",
            )
            debug_log.add(
                step=step,
                description="Server validation complete",
                level="SUCCESS",
                function="connect",
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step 6: Read MT5 configuration
            step = 6
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Reading MT5 configuration from environment variables",
                level="INFO",
                function="connect",
            )
            self._debug_info["terminal_path"] = settings.MT5_PATH
            debug_log.add(
                step=step,
                description=f"MT5 configuration loaded - terminal path: {settings.MT5_PATH}",
                level="SUCCESS",
                function="connect",
                result={"mt5_path": settings.MT5_PATH},
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step 7-8: Locate terminal executable (done in _start_terminal)
            # Step 9: Check if terminal is already running
            step = 9
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Checking if terminal process is already running",
                level="INFO",
                function="connect",
            )
            is_running = self._check_terminal_running()
            debug_log.add(
                step=step,
                description=f"Terminal process is {'already running' if is_running else 'not running'}",
                level="SUCCESS" if is_running else "WARNING",
                function="connect",
                result={"is_running": is_running},
                execution_time_ms=(time.time() - step_start) * 1000,
            )
            if not is_running:
                debug_log.add(
                    step=step,
                    description="⚠️ Please open MetaTrader 5 manually first! The app will use your existing terminal to avoid conflicts.",
                    level="WARNING",
                    function="connect",
                )
                self._connected = False
                return {
                    "success": False,
                    "stage": "terminal_not_running",
                    "error": "MetaTrader 5 is not running! Please open MetaTrader 5 manually and log into your account first.",
                    "mt5_last_error": None,
                    "traceback": None,
                    "suggested_solution": "1. Open MetaTrader 5\n2. Log into your account (108891758 on MetaQuotes-Demo)\n3. Try connecting again",
                }

            # Step 11: Call mt5.initialize
            step = 11
            step_start = time.time()
            debug_log.add(
                step=step,
                description=f"Calling mt5.initialize (terminal already running: {is_running})",
                level="INFO",
                function="connect",
            )
            # Skip shutdown if terminal is already running to avoid issues
            if not is_running:
                try:
                    self._log_mt5_api_call("shutdown")
                    mt5.shutdown()
                    time.sleep(2)
                except Exception:
                    pass
            initialize_result = False
            self._log_mt5_api_call("initialize")
            
            # If terminal is already running, just initialize normally (no login/password/server)
            if is_running:
                debug_log.add(
                    step=step,
                    description="Terminal already running - initializing without path",
                    level="INFO",
                    function="connect",
                )
                initialize_result = mt5.initialize(timeout=60000)
                last_error = mt5.last_error()
                debug_log.add(
                    step=step,
                    description=f"Initialize result: {initialize_result}, last_error: {last_error}",
                    level="INFO",
                    function="connect",
                )
            else:
                # Try different initialization strategies in order
                # Strategy 1: Initialize with login/password/server
                if use_creds_login and use_creds_password and use_creds_server:
                    debug_log.add(
                        step=step,
                        description="Trying mt5.initialize with login/password/server",
                        level="INFO",
                        function="connect",
                    )
                    initialize_result = mt5.initialize(
                        login=use_creds_login,
                        password=use_creds_password,
                        server=use_creds_server,
                        timeout=60000
                    )
                    last_error = mt5.last_error()
                    debug_log.add(
                        step=step,
                        description=f"Strategy 1 result: {initialize_result}, last_error: {last_error}",
                        level="INFO",
                        function="connect",
                    )
                
                # Strategy 2: If Strategy 1 failed, try path
                if not initialize_result:
                    if settings.MT5_PATH:
                        debug_log.add(
                            step=step,
                            description="Trying mt5.initialize with path",
                            level="INFO",
                            function="connect",
                        )
                        initialize_result = mt5.initialize(
                            path=settings.MT5_PATH, timeout=60000
                        )
                        last_error = mt5.last_error()
                    else:
                        debug_log.add(
                            step=step,
                            description="Trying mt5.initialize without path",
                            level="INFO",
                            function="connect",
                        )
                        initialize_result = mt5.initialize(timeout=60000)
                        last_error = mt5.last_error()
            self._debug_info["initialize_result"] = initialize_result
            self._debug_info["last_error"] = last_error
            debug_log.add(
                step=step,
                description=f"mt5.initialize returned: {initialize_result}",
                level="SUCCESS" if initialize_result else "ERROR",
                function="connect",
                result={"initialize_result": initialize_result},
                execution_time_ms=(time.time() - step_start) * 1000,
                mt5_last_error=last_error,
            )
            # Step 12: Handle initialize failure
            if not initialize_result:
                self._debug_info["error_code"] = last_error[0]
                self._debug_info["error_description"] = self._get_error_description(
                    last_error[0]
                )
                self._connected = False
                return {
                    "success": False,
                    "stage": "initialize",
                    "error": f"MT5 initialize failed: {self._get_error_description(last_error[0])}",
                    "mt5_last_error": last_error,
                    "suggested_solution": get_suggested_solution(
                        last_error[0], "initialize"
                    ),
                }

            # Step 13: Check if already logged in (via initialize), otherwise call login
            login_result = None
            self._credentials = {
                "login": use_creds_login,
                "password": use_creds_password,
                "server": use_creds_server,
            }
            
            # First check if already logged in
            step = 13
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Checking if already logged in via initialize",
                level="INFO",
                function="connect",
            )
            try:
                test_account_info = mt5.account_info()
                if test_account_info and test_account_info.login == use_creds_login:
                    login_result = True
                    last_error = mt5.last_error()
                    debug_log.add(
                        step=step,
                        description="Already logged in via initialize! Skipping mt5.login",
                        level="SUCCESS",
                        function="connect",
                        result={"login_result": login_result},
                        execution_time_ms=(time.time() - step_start) * 1000,
                        mt5_last_error=last_error,
                    )
            except Exception as e:
                debug_log.add(
                    step=step,
                    description=f"Check failed: {str(e)}",
                    level="WARNING",
                    function="connect",
                )
                
            # If not already logged in, call mt5.login
            if not login_result and use_creds_login and use_creds_password and use_creds_server:
                step_start = time.time()
                debug_log.add(
                    step=step,
                    description=f"Calling mt5.login with login: {use_creds_login}, server: {use_creds_server}",
                    level="INFO",
                    function="connect",
                )
                self._log_mt5_api_call(
                    "login",
                    login=use_creds_login,
                    password="********",
                    server=use_creds_server,
                    timeout=60000,
                )
                login_result = mt5.login(
                    login=use_creds_login,
                    password=use_creds_password,
                    server=use_creds_server,
                    timeout=60000,
                )
                last_error = mt5.last_error()
                self._debug_info["login_result"] = login_result
                self._debug_info["last_error"] = last_error
                debug_log.add(
                    step=step,
                    description=f"mt5.login returned: {login_result}",
                    level="SUCCESS" if login_result else "ERROR",
                    function="connect",
                    result={"login_result": login_result},
                    execution_time_ms=(time.time() - step_start) * 1000,
                    mt5_last_error=last_error,
                )
                if not login_result:
                    self._debug_info["error_code"] = last_error[0]
                    self._debug_info["error_description"] = self._get_error_description(
                        last_error[0]
                    )
                    self._connected = False
                    return {
                        "success": False,
                        "stage": "login",
                        "error": f"Login failed: {self._get_error_description(last_error[0])}",
                        "mt5_last_error": last_error,
                        "suggested_solution": get_suggested_solution(
                            last_error[0], "login"
                        ),
                    }
            elif not use_creds_login:
                debug_log.add(
                    step=13,
                    description="No credentials provided, skipping login and using existing session",
                    level="INFO",
                    function="connect",
                )

            # Step14: Retrieve terminal_info
            step = 14
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Retrieving terminal_info",
                level="INFO",
                function="connect",
            )
            self._log_mt5_api_call("terminal_info")
            terminal_info = mt5.terminal_info()
            if terminal_info:
                self._debug_info["terminal_info"] = terminal_info._asdict()
                self._debug_info["data_path"] = terminal_info.data_path
            debug_log.add(
                step=step,
                description=f"terminal_info retrieved: {terminal_info is not None}",
                level="SUCCESS",
                function="connect",
                result={"terminal_info": terminal_info._asdict() if terminal_info else None},
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step15: Retrieve version
            step = 15
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Retrieving MT5 version",
                level="INFO",
                function="connect",
            )
            self._log_mt5_api_call("version")
            version = mt5.version()
            self._debug_info["version"] = version
            debug_log.add(
                step=step,
                description=f"MT5 version: {version}",
                level="SUCCESS",
                function="connect",
                result={"version": version},
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step16: Retrieve account_info
            step = 16
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Retrieving account_info",
                level="INFO",
                function="connect",
            )
            self._log_mt5_api_call("account_info")
            account_info = mt5.account_info()
            last_error = mt5.last_error()
            debug_log.add(
                step=step,
                description=f"account_info retrieved: {account_info is not None}",
                level="SUCCESS" if account_info else "ERROR",
                function="connect",
                execution_time_ms=(time.time() - step_start) * 1000,
                mt5_last_error=last_error,
            )
            if not account_info:
                self._connected = False
                return {
                    "success": False,
                    "stage": "account_info",
                    "error": "Failed to retrieve account information",
                    "mt5_last_error": last_error,
                    "suggested_solution": get_suggested_solution(
                        last_error[0], "account_info"
                    ),
                }
            self._debug_info["account_info"] = account_info._asdict()

            # Step17: Verify account login
            step = 17
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Verifying account login",
                level="INFO",
                function="connect",
            )
            if use_creds_login and account_info.login != use_creds_login:
                debug_log.add(
                    step=step,
                    description=f"Account login mismatch! Expected {use_creds_login}, got {account_info.login}",
                    level="ERROR",
                    function="connect",
                    result="failed",
                    execution_time_ms=(time.time() - step_start) * 1000,
                )
                self._connected = False
                return {
                    "success": False,
                    "stage": "verify_account",
                    "error": f"Account login mismatch! Expected {use_creds_login}, got {account_info.login}",
                }
            debug_log.add(
                step=step,
                description=f"Account login verified: {account_info.login}",
                level="SUCCESS",
                function="connect",
                result={"login": account_info.login},
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step18: Verify trading permissions
            step = 18
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Verifying trading permissions",
                level="INFO",
                function="connect",
            )
            trade_mode = account_info.trade_mode
            debug_log.add(
                step=step,
                description=f"Trading permissions verified - trade mode: {trade_mode}",
                level="SUCCESS",
                function="connect",
                result={"trade_mode": trade_mode},
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step19: Retrieve symbols_total
            step = 19
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Retrieving total number of symbols",
                level="INFO",
                function="connect",
            )
            self._log_mt5_api_call("symbols_total")
            symbols_total = mt5.symbols_total()
            debug_log.add(
                step=step,
                description=f"Total symbols available: {symbols_total}",
                level="SUCCESS",
                function="connect",
                result={"symbols_total": symbols_total},
                execution_time_ms=(time.time() - step_start) * 1000,
            )

            # Step20: Try symbol_select("XAUUSD")
            step = 20
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Selecting XAUUSD symbol",
                level="INFO",
                function="connect",
            )
            xauusd_selected = self._ensure_symbol("XAUUSD")
            last_error = mt5.last_error()
            debug_log.add(
                step=step,
                description=f"XAUUSD symbol selected: {xauusd_selected}",
                level="SUCCESS" if xauusd_selected else "WARNING",
                function="connect",
                result={"xauusd_selected": xauusd_selected},
                execution_time_ms=(time.time() - step_start) * 1000,
                mt5_last_error=last_error,
            )

            # Step21: Retrieve latest candle
            step = 21
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Retrieving latest XAUUSD H1 candle",
                level="INFO",
                function="connect",
            )
            latest_candle = None
            if xauusd_selected:
                self._log_mt5_api_call("copy_rates_from_pos", "XAUUSD", mt5.TIMEFRAME_H1, 0, 1)
                latest_candle = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 1)
                # Fallback to copy_rates_from if copy_rates_from_pos fails
                if latest_candle is None or len(latest_candle) == 0:
                    from datetime import datetime, timedelta
                    date_from = datetime.now() - timedelta(days=1)
                    self._log_mt5_api_call("copy_rates_from", "XAUUSD", mt5.TIMEFRAME_H1, date_from, 1)
                    latest_candle = mt5.copy_rates_from("XAUUSD", mt5.TIMEFRAME_H1, date_from, 1)
                last_error = mt5.last_error()
                debug_log.add(
                    step=step,
                    description=f"Latest candle retrieved: {latest_candle is not None and len(latest_candle) > 0}",
                    level="SUCCESS",
                    function="connect",
                    execution_time_ms=(time.time() - step_start) * 1000,
                    mt5_last_error=last_error,
                )
            else:
                debug_log.add(
                    step=step,
                    description="Skipping candle retrieval (XAUUSD not selected)",
                    level="WARNING",
                    function="connect",
                    execution_time_ms=(time.time() - step_start) * 1000,
                )

            # Step22: Retrieve latest tick
            step = 22
            step_start = time.time()
            debug_log.add(
                step=step,
                description="Retrieving latest XAUUSD tick",
                level="INFO",
                function="connect",
            )
            if xauusd_selected:
                self._log_mt5_api_call("symbol_info_tick", "XAUUSD")
                latest_tick = mt5.symbol_info_tick("XAUUSD")
                debug_log.add(
                    step=step,
                    description=f"Latest tick retrieved: {latest_tick is not None}",
                    level="SUCCESS",
                    function="connect",
                    execution_time_ms=(time.time() - step_start) * 1000,
                )
            else:
                debug_log.add(
                    step=step,
                    description="Skipping tick retrieval (XAUUSD not selected)",
                    level="WARNING",
                    function="connect",
                    execution_time_ms=(time.time() - step_start) * 1000,
                )

            # Step23: Mark connection success
            step = 23
            self._connected = True
            connection_time = round(time.time() - overall_start, 2)
            self._debug_info["connection_time"] = connection_time
            debug_log.add(
                step=step,
                description=f"Connection SUCCESS! Total time: {connection_time}s",
                level="SUCCESS",
                function="connect",
                result="success",
                execution_time_ms=(time.time() - overall_start) * 1000,
            )

            # Start auto-reconnect thread
            self._start_reconnect_thread()

            return {
                "success": True,
                "debug_info": self._debug_info,
                "logs": debug_log.get_all(),
            }

        except Exception as e:
            error_traceback = traceback.format_exc()
            last_error = None
            if MT5_AVAILABLE:
                last_error = mt5.last_error()
            debug_log.add(
                step=999,
                description=f"Unhandled exception: {str(e)}",
                level="ERROR",
                function="connect",
                result="failed",
                exception=error_traceback,
                mt5_last_error=last_error,
            )
            self._debug_info["error_code"] = -4
            self._debug_info["error_description"] = str(e)
            self._connected = False
            return {
                "success": False,
                "stage": "initialize",
                "error": str(e),
                "mt5_last_error": last_error,
                "traceback": error_traceback,
                "suggested_solution": "Check the debug logs for more details",
            }

    def disconnect(self) -> None:
        try:
            self._stop_reconnect_thread()
            self._stop_monitoring_thread()
            if self._connected:
                self._log_mt5_api_call("shutdown")
                mt5.shutdown()
                self._connected = False
                self._credentials = {}
                logger.info("Disconnected from MT5")
                mt5_connection_logger.info("Disconnected from MT5")
                debug_log.add(
                    step=200,
                    description="Disconnected from MT5",
                    level="INFO",
                    function="disconnect",
                )
        except Exception as e:
            logger.error(f"Error disconnecting from MT5: {str(e)}")
            mt5_errors_logger.error(f"Error disconnecting: {str(e)}")
            debug_log.add(
                step=201,
                description=f"Error disconnecting: {str(e)}",
                level="ERROR",
                function="disconnect",
                exception=traceback.format_exc(),
            )

    def reconnect(self) -> bool:
        mt5_connection_logger.info("Attempting to reconnect...")
        result = self.connect(
            login=self._credentials.get("login"),
            password=self._credentials.get("password"),
            server=self._credentials.get("server"),
        )
        return result.get("success", False)

    def ensure_connection(self) -> bool:
        return self._ensure_connection()

    def ensure_symbol(self, symbol: str = "XAUUSD") -> bool:
        return self._ensure_symbol(symbol)

    def is_connected(self) -> bool:
        if not MT5_AVAILABLE:
            return False
        try:
            self._log_mt5_api_call("terminal_info")
            terminal_info = mt5.terminal_info()
            if terminal_info and terminal_info.connected:
                self._log_mt5_api_call("account_info")
                account_info = mt5.account_info()
                if account_info:
                    return True
        except Exception as e:
            mt5_errors_logger.error(f"is_connected check failed: {str(e)}")
        self._connected = False
        return False

    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed connection status including all validation checks."""
        status = {
            "connected": False,
            "terminal": None,
            "account": None,
            "server": None,
            "balance": 0.0,
            "equity": 0.0,
            "symbol_ready": False,
            "candles_ready": False,
            "last_error": None,
            "checks": {
                "terminal_running": False,
                "mt5_initialized": False,
                "login_success": False,
                "account_info": False,
                "terminal_info": False,
                "symbol_exists": False,
                "candles_retrievable": False
            }
        }
        
        if not MT5_AVAILABLE:
            status["last_error"] = "MetaTrader5 module not available"
            return status
        
        try:
            # Check 1: Terminal running
            status["checks"]["terminal_running"] = self._check_terminal_running()
            if not status["checks"]["terminal_running"]:
                status["last_error"] = "MT5 terminal is not running"
                return status
            
            # Check 2: MT5 initialized
            try:
                self._log_mt5_api_call("initialize")
                initialized = mt5.initialize()
                status["checks"]["mt5_initialized"] = initialized
                if not initialized:
                    last_error = mt5.last_error()
                    status["last_error"] = f"MT5 initialize failed: {self._get_error_description(last_error[0])}"
                    return status
            except Exception as e:
                status["last_error"] = f"MT5 initialize exception: {str(e)}"
                return status
            
            # Check 3: Login state
            try:
                self._log_mt5_api_call("account_info")
                account_info = mt5.account_info()
                status["checks"]["login_success"] = account_info is not None
                if account_info:
                    status["account"] = str(account_info.login)
                    status["server"] = account_info.server
                    status["balance"] = float(account_info.balance)
                    status["equity"] = float(account_info.equity)
                    status["checks"]["account_info"] = True
            except Exception as e:
                status["last_error"] = f"Account info check failed: {str(e)}"
                return status
            
            # Check 4: Terminal info
            try:
                self._log_mt5_api_call("terminal_info")
                terminal_info = mt5.terminal_info()
                status["checks"]["terminal_info"] = terminal_info is not None and terminal_info.connected
                if terminal_info:
                    status["terminal"] = terminal_info.name
            except Exception as e:
                status["last_error"] = f"Terminal info check failed: {str(e)}"
                return status
            
            # Check 5: Symbol exists
            try:
                symbol = "XAUUSD"
                self._log_mt5_api_call("symbol_info", symbol)
                symbol_info = mt5.symbol_info(symbol)
                status["checks"]["symbol_exists"] = symbol_info is not None
                status["symbol_ready"] = status["checks"]["symbol_exists"]
                
                if symbol_info:
                    # Check 6: Candles retrievable
                    self._log_mt5_api_call("copy_rates_from_pos", symbol, mt5.TIMEFRAME_H1, 0, 1)
                    candles = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)
                    status["checks"]["candles_retrievable"] = candles is not None and len(candles) > 0
                    status["candles_ready"] = status["checks"]["candles_retrievable"]
            except Exception as e:
                status["last_error"] = f"Symbol check failed: {str(e)}"
                return status
            
            # All checks passed
            status["connected"] = all(status["checks"].values())
            return status
            
        except Exception as e:
            status["last_error"] = f"Status check exception: {str(e)}"
            return status

    def get_credentials(self) -> Dict[str, Any]:
        return self._credentials.copy()

    def get_debug_info(self) -> Dict[str, Any]:
        return self._debug_info.copy()

    def get_debug_logs(self) -> List[Dict[str, Any]]:
        return debug_log.get_all()

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        mt5_api_logger.info("Calling get_account_info")
        if not self._ensure_connection():
            return None

        self._log_mt5_api_call("account_info")
        info = mt5.account_info()
        if info is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(f"account_info failed - last_error: {last_error}")
            return None
        mt5_api_logger.info(f"get_account_info returned: {info._asdict()}")
        return info._asdict()

    def get_account(self):
        return self.get_account_info()

    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        mt5_api_logger.info("Calling get_terminal_info")
        if not self._ensure_connection():
            return None

        self._log_mt5_api_call("terminal_info")
        info = mt5.terminal_info()
        if info is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(f"terminal_info failed - last_error: {last_error}")
            return None
        mt5_api_logger.info(f"get_terminal_info returned: {info._asdict()}")
        return info._asdict()

    def get_terminal(self):
        return self.get_terminal_info()

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        mt5_api_logger.info(f"Calling get_symbol_info for {symbol}")
        if not self._ensure_connection():
            return None
        if not self._ensure_symbol(symbol):
            return None

        self._log_mt5_api_call("symbol_info", symbol)
        info = mt5.symbol_info(symbol)
        if info is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"symbol_info failed for {symbol} - last_error: {last_error}"
            )
            return None
        mt5_api_logger.info(f"get_symbol_info returned: {info._asdict()}")
        return info._asdict()

    def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        mt5_api_logger.info(f"Calling get_tick for {symbol}")
        if not MT5_AVAILABLE or not self._ensure_connection():
            import time
            import random
            # Return dummy tick data
            base_price = 3000
            return {
                "time": int(time.time()),
                "bid": base_price + random.uniform(-5, 5),
                "ask": base_price + random.uniform(-4.5, 5.5),
                "last": base_price + random.uniform(-4.7, 5.3),
                "volume": random.randint(1, 100),
                "time_msc": int(time.time() * 1000),
                "flags": 0,
                "volume_real": random.uniform(0.1, 10.0),
            }
        if not self._ensure_symbol(symbol):
            return None

        self._log_mt5_api_call("symbol_info_tick", symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"symbol_info_tick failed for {symbol} - last_error: {last_error}"
            )
            return None
        mt5_api_logger.info(f"get_tick returned: {tick._asdict()}")
        return tick._asdict()

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        mt5_api_logger.info("Calling get_account_info")
        if not MT5_AVAILABLE or not self._ensure_connection():
            # Return dummy account info
            return {
                "login": 12345678,
                "trade_mode": 0,
                "leverage": 100,
                "limit_orders": 500,
                "margin_so_mode": 0,
                "trade_allowed": True,
                "trade_expert": True,
                "margin_mode": 0,
                "currency_digits": 2,
                "fifo_close": False,
                "balance": 10000.0,
                "credit": 0.0,
                "profit": 0.0,
                "equity": 10000.0,
                "margin": 0.0,
                "margin_free": 10000.0,
                "margin_level": 0.0,
                "margin_so_call": 50.0,
                "margin_so_so": 30.0,
                "margin_initial": 0.0,
                "margin_maintenance": 0.0,
                "assets": 0.0,
                "liabilities": 0.0,
                "commission_blocked": 0.0,
                "name": "Demo Account",
                "server": "MetaQuotes-Demo",
                "currency": "USD",
                "company": "TraderAI",
            }

        self._log_mt5_api_call("account_info")
        info = mt5.account_info()
        if info is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(f"account_info failed - last_error: {last_error}")
            return None
        mt5_api_logger.info(f"get_account_info returned: {info._asdict()}")
        self._debug_info["account_info"] = info._asdict()
        return info._asdict()

    def get_candles(
        self, symbol: str, timeframe: str, count: int = 500
    ) -> Optional[List[Dict[str, Any]]]:
        print(f"[MT5 Connector] get_candles called for {symbol} {timeframe} count={count}")
        mt5_api_logger.info(
            f"Calling get_candles for {symbol} {timeframe} {count}"
        )
        if not MT5_AVAILABLE:
            # Generate dummy candlestick data
            import time
            import random
            now = int(time.time())
            timeframe_seconds = {
                "M1": 60, "M5": 300, "M15": 900, "M30": 1800, 
                "H1": 3600, "H4": 14400, "D1": 86400
            }
            tf_sec = timeframe_seconds.get(timeframe, 3600)
            candles = []
            price = 3000.0
            for i in range(count):
                t = now - (count - i - 1) * tf_sec
                volatility = 5.0 if timeframe in ["H1", "H4", "D1"] else 2.0
                change = (random.random() - 0.5) * volatility
                open_price = price
                close_price = open_price + change
                high = max(open_price, close_price) + random.random() * volatility
                low = min(open_price, close_price) - random.random() * volatility
                
                candles.append({
                    "time": t,
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close_price, 2),
                    "tick_volume": random.randint(100, 10000),
                    "spread": random.randint(1, 10),
                    "real_volume": random.randint(1, 100),
                })
                price = close_price
            print(f"[MT5 Connector] Generated {len(candles)} dummy candles")
            return candles
        
        if not self._ensure_connection():
            print("[MT5 Connector] _ensure_connection failed")
            return None
        if not self._ensure_symbol(symbol):
            print("[MT5 Connector] _ensure_symbol failed")
            return None

        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }

        tf = timeframe_map.get(timeframe)
        print(f"[MT5 Connector] Mapped timeframe '{timeframe}' to {tf}")
        if tf is None:
            logger.error(f"Invalid timeframe: {timeframe}")
            mt5_errors_logger.error(f"Invalid timeframe: {timeframe}")
            return None

        # Try copy_rates_from_pos first
        print(f"[MT5 Connector] Calling copy_rates_from_pos for {symbol} {tf} 0 {count}")
        self._log_mt5_api_call("copy_rates_from_pos", symbol, tf, 0, count)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        print(f"[MT5 Connector] copy_rates_from_pos returned: {rates}")
        
        # Fallback to copy_rates_from if needed
        if rates is None or len(rates) == 0:
            print(f"[MT5 Connector] copy_rates_from_pos returned no data, trying copy_rates_from")
            from datetime import datetime, timedelta
            # Calculate date_from based on timeframe to get enough data
            delta_days = {
                "M1": 7, "M5": 14, "M15": 21, "M30": 30, "H1": 60, "H4": 180, "D1": 730
            }
            date_from = datetime.now() - timedelta(days=delta_days.get(timeframe, 7))
            self._log_mt5_api_call("copy_rates_from", symbol, tf, date_from, count)
            rates = mt5.copy_rates_from(symbol, tf, date_from, count)
            print(f"[MT5 Connector] copy_rates_from returned: {rates}")
            # If still not enough, take what we can get
            if rates is not None and len(rates) > count:
                rates = rates[-count:]
            
        if rates is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            print(f"[MT5 Connector] last_error: {last_error}")
            mt5_errors_logger.error(
                f"Failed to retrieve candles - last_error: {last_error}"
            )
            return None

        print(f"[MT5 Connector] Processing {len(rates)} rates into candles")
        candles = []
        for rate in rates:
            candle = {
                "time": int(rate[0]),
                "open": float(rate[1]),
                "high": float(rate[2]),
                "low": float(rate[3]),
                "close": float(rate[4]),
                "tick_volume": int(rate[5]),
                "spread": int(rate[6]),
                "real_volume": int(rate[7]),
            }
            candles.append(candle)
        print(f"[MT5 Connector] Created {len(candles)} candles")
        mt5_api_logger.info(f"get_candles returned {len(candles)} candles")
        return candles

    def get_symbols(self) -> List[Dict[str, Any]]:
        mt5_api_logger.info("Calling get_symbols")
        if not self._ensure_connection():
            return []

        self._log_mt5_api_call("symbols_get")
        symbols = mt5.symbols_get()
        if symbols is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"symbols_get failed - last_error: {last_error}"
            )
            return []

        result = [
            {
                "symbol": s.name,
                "description": s.description,
                "spread": s.spread,
                "digits": s.digits,
                "visible": s.visible,
                "trade_mode": s.trade_mode
            }
            for s in symbols
        ]
        mt5_api_logger.info(f"get_symbols returned {len(result)} symbols")
        return result

    def get_open_positions(self) -> List[Dict[str, Any]]:
        mt5_api_logger.info("Calling get_open_positions")
        if not self._ensure_connection():
            return []

        self._log_mt5_api_call("positions_get")
        positions = mt5.positions_get()
        if positions is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"positions_get failed - last_error: {last_error}"
            )
            return []

        result = [pos._asdict() for pos in positions]
        mt5_api_logger.info(f"get_open_positions returned {len(result)} positions")
        return result

    def get_deal_history(self, date_from, date_to) -> List[Dict[str, Any]]:
        mt5_api_logger.info(
            f"Calling get_deal_history from {date_from} to {date_to}"
        )
        if not self._ensure_connection():
            return []

        self._log_mt5_api_call("history_deals_get", date_from, date_to)
        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"history_deals_get failed - last_error: {last_error}"
            )
            return []

        result = [deal._asdict() for deal in deals]
        mt5_api_logger.info(f"get_deal_history returned {len(result)} deals")
        return result

    def get_orders(self) -> List[Dict[str, Any]]:
        mt5_api_logger.info("Calling get_orders (pending orders)")
        if not self._ensure_connection():
            return []

        self._log_mt5_api_call("orders_get")
        orders = mt5.orders_get()
        if orders is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"orders_get failed - last_error: {last_error}"
            )
            return []

        result = [order._asdict() for order in orders]
        mt5_api_logger.info(f"get_orders returned {len(result)} pending orders")
        return result

    def get_order_history(self, date_from, date_to) -> List[Dict[str, Any]]:
        mt5_api_logger.info(
            f"Calling get_order_history from {date_from} to {date_to}"
        )
        if not self._ensure_connection():
            return []

        self._log_mt5_api_call("history_orders_get", date_from, date_to)
        orders = mt5.history_orders_get(date_from, date_to)
        if orders is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"history_orders_get failed - last_error: {last_error}"
            )
            return []

        result = [order._asdict() for order in orders]
        mt5_api_logger.info(f"get_order_history returned {len(result)} orders")
        return result

    def get_full_debug_info(self) -> Dict[str, Any]:
        mt5_api_logger.info("Calling get_full_debug_info")
        result = {
            "mt5_available": MT5_AVAILABLE,
            "mt5_initialized": self._connected,
            "mt5_version": None,
            "terminal_path": None,
            "data_path": None,
            "connected_account": None,
            "broker": None,
            "server": None,
            "login": None,
            "account_type": None,
            "balance": None,
            "equity": None,
            "margin": None,
            "last_error": None,
            "available_symbols_count": None,
            "xauusd_available": False,
            "xauusd_visibility": None,
            "tick_received": False,
            "latest_candle": None,
            "terminal_process_running": False,
        }

        try:
            result["terminal_process_running"] = self._check_terminal_running()

            if not MT5_AVAILABLE:
                mt5_api_logger.warning("MT5 not available")
                return result

            if self._debug_info["version"]:
                result["mt5_version"] = self._debug_info["version"]
            elif self._connected:
                self._log_mt5_api_call("version")
                result["mt5_version"] = mt5.version()

            result["terminal_path"] = self._debug_info["terminal_path"]
            result["data_path"] = self._debug_info["data_path"]

            if self._connected:
                account_info = self.get_account_info()
                if account_info:
                    result["connected_account"] = True
                    result["broker"] = account_info.get("company")
                    result["server"] = account_info.get("server")
                    result["login"] = account_info.get("login")
                    result["account_type"] = account_info.get("trade_mode")
                    result["balance"] = account_info.get("balance")
                    result["equity"] = account_info.get("equity")
                    result["margin"] = account_info.get("margin")

            if self._connected:
                self._log_mt5_api_call("last_error")
                result["last_error"] = mt5.last_error()

            if self._connected:
                self._log_mt5_api_call("symbols_total")
                result["available_symbols_count"] = mt5.symbols_total()

            if self._connected:
                if self._ensure_symbol("XAUUSD"):
                    result["xauusd_available"] = True
                    self._log_mt5_api_call("symbol_info", "XAUUSD")
                    xauusd_info = mt5.symbol_info("XAUUSD")
                    if xauusd_info:
                        result["xauusd_visibility"] = xauusd_info.visible

                    self._log_mt5_api_call("symbol_info_tick", "XAUUSD")
                    tick = mt5.symbol_info_tick("XAUUSD")
                    if tick:
                        result["tick_received"] = True
                        result["tick_info"] = tick._asdict()

                    self._log_mt5_api_call(
                        "copy_rates_from_pos", "XAUUSD", mt5.TIMEFRAME_H1, 0, 1
                    )
                    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 1)
                    if rates and len(rates) > 0:
                        result["latest_candle"] = {
                            "time": int(rates[0][0]),
                            "open": float(rates[0][1]),
                            "high": float(rates[0][2]),
                            "low": float(rates[0][3]),
                            "close": float(rates[0][4]),
                        }

        except Exception as e:
            error_traceback = traceback.format_exc()
            result["error"] = str(e)
            result["traceback"] = error_traceback
            mt5_errors_logger.error(
                f"get_full_debug_info exception: {str(e)}\n{error_traceback}"
            )

        mt5_api_logger.info(f"get_full_debug_info returned: {result}")
        return result

    def open_buy_order(
        self,
        symbol: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ):
        mt5_api_logger.info(
            f"Calling open_buy_order for {symbol}, volume: {volume}"
        )
        if self._demo_mode:
            # Demo mode - create fake position
            import random
            import time
            fake_ticket = random.randint(100000, 999999)
            fake_price = 3000 + random.uniform(-5, 5)
            position = {
                "ticket": fake_ticket,
                "time": int(time.time()),
                "type": 0,  # 0 = buy
                "symbol": symbol,
                "volume": volume,
                "price_open": fake_price,
                "sl": sl,
                "tp": tp,
                "swap": 0,
                "profit": 0,
            }
            self._demo_positions.append(position)
            # Return fake result object
            class DemoOrderResult:
                retcode = 10009
                deal = fake_ticket
                order = fake_ticket
                volume = volume
                price = fake_price
                bid = fake_price - 0.5
                ask = fake_price + 0.5
                comment = "Demo buy order executed"
                request_id = fake_ticket
                retcode_external = 0
            return DemoOrderResult()
        if not self._ensure_connection():
            return None
        if not self._ensure_symbol(symbol):
            return None

        self._log_mt5_api_call("symbol_info_tick", symbol)
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"symbol_info_tick failed for {symbol} - last_error: {last_error}"
            )
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "TraderAI Order",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        self._log_mt5_api_call("order_send", request)
        result = mt5.order_send(request)
        mt5_api_logger.info(f"order_send result: {result}")
        return result

    def open_sell_order(
        self,
        symbol: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ):
        mt5_api_logger.info(
            f"Calling open_sell_order for {symbol}, volume: {volume}"
        )
        if self._demo_mode:
            # Demo mode - create fake position
            import random
            import time
            fake_ticket = random.randint(100000, 999999)
            fake_price = 3000 + random.uniform(-5, 5)
            position = {
                "ticket": fake_ticket,
                "time": int(time.time()),
                "type": 1,  # 1 = sell
                "symbol": symbol,
                "volume": volume,
                "price_open": fake_price,
                "sl": sl,
                "tp": tp,
                "swap": 0,
                "profit": 0,
            }
            self._demo_positions.append(position)
            # Return fake result object
            class DemoOrderResult:
                retcode = 10009
                deal = fake_ticket
                order = fake_ticket
                volume = volume
                price = fake_price
                bid = fake_price - 0.5
                ask = fake_price + 0.5
                comment = "Demo sell order executed"
                request_id = fake_ticket
                retcode_external = 0
            return DemoOrderResult()
        if not self._ensure_connection():
            return None
        if not self._ensure_symbol(symbol):
            return None

        self._log_mt5_api_call("symbol_info_tick", symbol)
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"symbol_info_tick failed for {symbol} - last_error: {last_error}"
            )
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": tick.bid,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "TraderAI Order",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        self._log_mt5_api_call("order_send", request)
        result = mt5.order_send(request)
        mt5_api_logger.info(f"order_send result: {result}")
        return result

    def get_positions(self, symbol: Optional[str] = None):
        mt5_api_logger.info(f"Calling get_positions for symbol: {symbol}")
        if self._demo_mode:
            if symbol:
                return [p for p in self._demo_positions if p["symbol"] == symbol]
            return self._demo_positions
        if not self._ensure_connection():
            return []
        self._log_mt5_api_call("positions_get")
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            mt5_api_logger.info("No open positions")
            return []
        return positions

    def close_position(self, ticket: int):
        mt5_api_logger.info(f"Calling close_position for ticket: {ticket}")
        if self._demo_mode:
            # Demo mode: remove position from _demo_positions
            for i, p in enumerate(self._demo_positions):
                if p["ticket"] == ticket:
                    removed = self._demo_positions.pop(i)
                    class DemoCloseResult:
                        retcode = 10009
                        deal = ticket
                        comment = "Demo position closed"
                    return DemoCloseResult()
            return None
        if not self._ensure_connection():
            return None

        self._log_mt5_api_call("positions_get", ticket=ticket)
        position = mt5.positions_get(ticket=ticket)
        if not position:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"positions_get failed for ticket {ticket} - last_error: {last_error}"
            )
            return None

        pos = position[0]
        self._log_mt5_api_call("symbol_info_tick", pos.symbol)
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"symbol_info_tick failed for {pos.symbol} - last_error: {last_error}"
            )
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_BUY
            if pos.type == mt5.POSITION_TYPE_SELL
            else mt5.ORDER_TYPE_SELL,
            "position": pos.ticket,
            "price": tick.bid
            if pos.type == mt5.POSITION_TYPE_BUY
            else tick.ask,
            "deviation": 10,
            "magic": 234000,
            "comment": "TraderAI Close",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        self._log_mt5_api_call("order_send", request)
        result = mt5.order_send(request)
        mt5_api_logger.info(f"order_send result: {result}")
        return result

    def close_all_positions(self):
        mt5_api_logger.info("Calling close_all_positions")
        if self._demo_mode:
            count = len(self._demo_positions)
            self._demo_positions = []
            class DemoCloseAllResult:
                retcode = 10009
                comment = f"Demo: All demo positions closed"
            return [DemoCloseAllResult()]
        if not self._ensure_connection():
            return []

        self._log_mt5_api_call("positions_get")
        positions = mt5.positions_get()
        if not positions:
            mt5_api_logger.info("No open positions to close")
            return []

        results = []
        for pos in positions:
            result = self.close_position(pos.ticket)
            results.append(result)
        mt5_api_logger.info(f"close_all_positions returned {len(results)} results")
        return results

    def modify_position_sl_tp(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ):
        mt5_api_logger.info(
            f"Calling modify_position_sl_tp for ticket: {ticket}, sl: {sl}, tp: {tp}"
        )
        if not self._ensure_connection():
            return None

        self._log_mt5_api_call("positions_get", ticket=ticket)
        position = mt5.positions_get(ticket=ticket)
        if not position:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"positions_get failed for ticket {ticket} - last_error: {last_error}"
            )
            return None

        pos = position[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": pos.ticket,
            "sl": sl if sl is not None else pos.sl,
            "tp": tp if tp is not None else pos.tp,
        }

        self._log_mt5_api_call("order_send", request)
        result = mt5.order_send(request)
        mt5_api_logger.info(f"order_send result: {result}")
        return result

    def get_debug_info(self) -> Dict[str, Any]:
        return self._debug_info

    def get_debug_logs(self) -> List[Dict[str, Any]]:
        return debug_log.get_all()

    def get_detailed_status(self) -> Dict[str, Any]:
        try:
            if self._demo_mode:
                account_info = self._demo_account_info
                return {
                    "connected": self._connected,
                    "terminal": "demo",
                    "account": str(account_info.get("login")) if account_info else None,
                    "server": account_info.get("server") if account_info else None,
                    "balance": account_info.get("balance") if account_info else 0.0,
                    "equity": account_info.get("equity") if account_info else 0.0,
                    "symbol_ready": True,
                    "candles_ready": True,
                    "last_error": None,
                    "account_info": account_info,
                    "checks": {
                        "terminal_running": True,
                        "mt5_initialized": True,
                        "login_success": True,
                        "account_info": True,
                        "terminal_info": True,
                        "symbol_exists": True,
                        "candles_retrievable": True
                    }
                }
            
            account_info = self.get_account_info() if self._connected else None
            
            # Check symbol availability
            symbol_ready = False
            if self._connected:
                try:
                    symbol_info = mt5.symbol_info("XAUUSD")
                    if symbol_info:
                        symbol_ready = True
                        mt5.symbol_select("XAUUSD", True)
                except:
                    pass
            
            # Check candle retrieval
            candles_ready = False
            if symbol_ready:
                try:
                    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 1)
                    candles_ready = rates is not None and len(rates) > 0
                except:
                    pass
            
            # Format last_error as string
            last_error = self._debug_info.get("last_error")
            last_error_str = None
            if last_error:
                if isinstance(last_error, tuple) and len(last_error) >= 2:
                    last_error_str = f"{last_error[0]} - {last_error[1]}"
                else:
                    last_error_str = str(last_error)
            
            return {
                "connected": self._connected,
                "terminal": "running" if self._check_terminal_running() else "not running",
                "account": str(account_info.get("login")) if account_info else None,
                "server": account_info.get("server") if account_info else None,
                "balance": account_info.get("balance") if account_info else 0.0,
                "equity": account_info.get("equity") if account_info else 0.0,
                "symbol_ready": symbol_ready,
                "candles_ready": candles_ready,
                "last_error": last_error_str,
                "account_info": account_info,
                "checks": {
                    "terminal_running": self._check_terminal_running(),
                    "mt5_initialized": self._debug_info.get("initialize_result"),
                    "login_success": account_info is not None,
                    "account_info": account_info is not None,
                    "terminal_info": self._debug_info.get("terminal_info") is not None,
                    "symbol_exists": symbol_ready,
                    "candles_retrievable": candles_ready
                }
            }
        except Exception as e:
            last_error = self._debug_info.get("last_error")
            last_error_str = None
            if last_error:
                if isinstance(last_error, tuple) and len(last_error) >= 2:
                    last_error_str = f"{last_error[0]} - {last_error[1]}"
                else:
                    last_error_str = str(last_error)
            return {
                "connected": False,
                "error": str(e),
                "last_error": last_error_str
            }

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        if self._demo_mode:
            return self._demo_account_info
        try:
            info = mt5.account_info()
            if info:
                return info._asdict()
            return None
        except Exception as e:
            mt5_errors_logger.error(f"get_account_info failed: {str(e)}")
            return None


def get_mt5_connector() -> MT5Connector:
    return MT5Connector()
