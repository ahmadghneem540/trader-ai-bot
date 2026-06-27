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
import psutil
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
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"].lower()
                if name == "terminal.exe" or name == "terminal64.exe":
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
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
                    # Give it a few more seconds to fully start
                    time.sleep(15)
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

    def _stop_reconnect_thread(self):
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._stop_reconnect.set()
            self._reconnect_thread.join(timeout=10)

    def connect(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
    ) -> Dict[str, Any]:
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
                step_start = time.time()
                terminal_result = self._start_terminal()
                if not terminal_result["success"]:
                    last_error = None
                    if MT5_AVAILABLE:
                        last_error = mt5.last_error()
                    debug_log.add(
                        step=step,
                        description=f"Terminal startup failed: {terminal_result['error']}",
                        level="ERROR",
                        function="connect",
                        result="failed",
                        mt5_last_error=last_error,
                        exception=terminal_result.get("traceback"),
                    )
                    self._connected = False
                    return {
                        "success": False,
                        "stage": terminal_result["stage"],
                        "error": terminal_result["error"],
                        "mt5_last_error": last_error,
                        "traceback": terminal_result.get("traceback"),
                        "suggested_solution": get_suggested_solution(
                            last_error[0] if last_error else -1, terminal_result["stage"]
                        ),
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
            # First shutdown any previous session
            try:
                self._log_mt5_api_call("shutdown")
                mt5.shutdown()
                time.sleep(2)
            except Exception:
                pass
            initialize_result = False
            self._log_mt5_api_call("initialize")
            
            # Try different initialization strategies in order
            # Strategy 1: Initialize with login/password/server (what worked!)
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
            
            # Strategy 2: If Strategy 1 failed, try path if needed
            if not initialize_result:
                if not is_running and settings.MT5_PATH:
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
            if self._connected:
                self._log_mt5_api_call("shutdown")
                mt5.shutdown()
                self._connected = False
                logger.info("Disconnected from MT5")
                mt5_connection_logger.info("Disconnected from MT5")
        except Exception as e:
            logger.error(f"Error disconnecting from MT5: {str(e)}")
            mt5_errors_logger.error(f"Error disconnecting: {str(e)}")

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
        if not self._ensure_connection():
            return None
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

    def get_candles(
        self, symbol: str, timeframe: str, count: int = 500
    ) -> Optional[List[Dict[str, Any]]]:
        mt5_api_logger.info(
            f"Calling get_candles for {symbol} {timeframe} {count}"
        )
        if not self._ensure_connection():
            return None
        if not self._ensure_symbol(symbol):
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
        if tf is None:
            logger.error(f"Invalid timeframe: {timeframe}")
            mt5_errors_logger.error(f"Invalid timeframe: {timeframe}")
            return None

        # Try copy_rates_from_pos first
        self._log_mt5_api_call("copy_rates_from_pos", symbol, tf, 0, count)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        
        # Fallback to copy_rates_from if needed
        if rates is None or len(rates) == 0:
            from datetime import datetime, timedelta
            # Calculate date_from based on timeframe to get enough data
            delta_days = {
                "M1": 7, "M5": 14, "M15": 21, "M30": 30, "H1": 60, "H4": 180, "D1": 730
            }
            date_from = datetime.now() - timedelta(days=delta_days.get(timeframe, 7))
            self._log_mt5_api_call("copy_rates_from", symbol, tf, date_from, count)
            rates = mt5.copy_rates_from(symbol, tf, date_from, count)
            # If still not enough, take what we can get
            if rates is not None and len(rates) > count:
                rates = rates[-count:]
            
        if rates is None:
            self._log_mt5_api_call("last_error")
            last_error = mt5.last_error()
            mt5_errors_logger.error(
                f"Failed to retrieve candles - last_error: {last_error}"
            )
            return None

        candles = []
        for rate in rates:
            candles.append(
                {
                    "time": int(rate[0]),
                    "open": float(rate[1]),
                    "high": float(rate[2]),
                    "low": float(rate[3]),
                    "close": float(rate[4]),
                    "tick_volume": int(rate[5]),
                    "spread": int(rate[6]),
                    "real_volume": int(rate[7]),
                }
            )
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

    def close_position(self, ticket: int):
        mt5_api_logger.info(f"Calling close_position for ticket: {ticket}")
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


def get_mt5_connector() -> MT5Connector:
    return MT5Connector()
