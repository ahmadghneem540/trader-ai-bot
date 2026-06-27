import logging
import sys
from pathlib import Path
from structlog import configure, stdlib, processors
from app.core.config.settings import settings


def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_dir = Path(settings.LOG_FILE_PATH).parent
    log_dir.mkdir(exist_ok=True)

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    file_handler = logging.FileHandler(settings.LOG_FILE_PATH, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Structlog configuration
    configure(
        processors=[
            processors.TimeStamper(fmt="iso"),
            processors.add_log_level,
            stdlib.render_to_log_kwargs,
            processors.JSONRenderer(),
        ],
        wrapper_class=stdlib.BoundLogger,
        context_class=dict,
        logger_factory=stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def get_mt5_logger() -> logging.Logger:
    logger = logging.getLogger("mt5.connection")
    # Add file handler for MT5 connection logs
    log_dir = Path(settings.LOG_FILE_PATH).parent
    mt5_log_path = log_dir / "mt5.log"
    file_handler = logging.FileHandler(mt5_log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_mt5_errors_logger() -> logging.Logger:
    logger = logging.getLogger("mt5.errors")
    log_dir = Path(settings.LOG_FILE_PATH).parent
    mt5_errors_log_path = log_dir / "mt5_errors.log"
    file_handler = logging.FileHandler(mt5_errors_log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_mt5_api_logger() -> logging.Logger:
    logger = logging.getLogger("mt5.api")
    log_dir = Path(settings.LOG_FILE_PATH).parent
    mt5_api_log_path = log_dir / "mt5_api.log"
    file_handler = logging.FileHandler(mt5_api_log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_mt5_debug_logger() -> logging.Logger:
    logger = logging.getLogger("mt5.debug")
    log_dir = Path(settings.LOG_FILE_PATH).parent
    mt5_debug_log_path = log_dir / "mt5_debug.log"
    file_handler = logging.FileHandler(mt5_debug_log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
