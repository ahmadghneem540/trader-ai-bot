import os
# Set environment variable BEFORE importing anything that uses passlib
os.environ['PASSLIB_BCRYPT_BUG_DETECTION'] = 'skip'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config.settings import settings
from app.core.logging.logger import setup_logging, get_logger
from app.core.scheduler import get_scheduler
from app.core.database.session import SessionLocal
from app.infrastructure.database.repositories import SymbolRepository
from app.infrastructure.mt5.connector import get_mt5_connector
from app.api.routes import health, symbols, market_data, trading, auth, websockets, strategy, backtest, mt5
from app.application.services.strategy_runner import strategy_runner

setup_logging()
logger = get_logger(__name__)


def init_default_data():
    """Initialize default data in the database"""
    db = SessionLocal()
    try:
        # Check if symbols exist
        symbol_repo = SymbolRepository(db)
        existing_symbols = symbol_repo.get_all()
        if len(existing_symbols) == 0:
            # Add default symbols
            default_symbols = [
                {"name": "EURUSD", "description": "Euro/US Dollar", "digits": 5, "point": 0.00001, "contract_size": 100000, "is_active": True},
                {"name": "GBPUSD", "description": "British Pound/US Dollar", "digits": 5, "point": 0.00001, "contract_size": 100000, "is_active": True},
                {"name": "USDJPY", "description": "US Dollar/Japanese Yen", "digits": 3, "point": 0.001, "contract_size": 100000, "is_active": True},
                {"name": "USDCHF", "description": "US Dollar/Swiss Franc", "digits": 5, "point": 0.00001, "contract_size": 100000, "is_active": True},
                {"name": "AUDUSD", "description": "Australian Dollar/US Dollar", "digits": 5, "point": 0.00001, "contract_size": 100000, "is_active": True},
                {"name": "USDCAD", "description": "US Dollar/Canadian Dollar", "digits": 5, "point": 0.00001, "contract_size": 100000, "is_active": True},
                {"name": "NZDUSD", "description": "New Zealand Dollar/US Dollar", "digits": 5, "point": 0.00001, "contract_size": 100000, "is_active": True},
                {"name": "EURGBP", "description": "Euro/British Pound", "digits": 5, "point": 0.00001, "contract_size": 100000, "is_active": True},
                {"name": "EURJPY", "description": "Euro/Japanese Yen", "digits": 3, "point": 0.001, "contract_size": 100000, "is_active": True},
                {"name": "GBPJPY", "description": "British Pound/Japanese Yen", "digits": 3, "point": 0.001, "contract_size": 100000, "is_active": True},
            ]
            for symbol_data in default_symbols:
                symbol_repo.create(symbol_data)
            logger.info("Default symbols added to database")
    except Exception as e:
        logger.exception(f"Error initializing default data: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize default data
    init_default_data()
    
    mt5_connector = get_mt5_connector()
    scheduler = get_scheduler()
    try:
        mt5_connector.connect()
    except Exception as e:
        logger.warning(f"Failed to connect to MT5 on startup: {str(e)}")
    scheduler.start()

    # Add auto trading jobs - M15 and H1
    def run_m15():
        for symbol in strategy_runner.supported_symbols:
            try:
                strategy_runner.run_cycle(symbol, "M15")
            except Exception as e:
                logger.error(f"Error running M15 for {symbol}: {str(e)}")

    def run_h1():
        for symbol in strategy_runner.supported_symbols:
            try:
                strategy_runner.run_cycle(symbol, "H1")
            except Exception as e:
                logger.error(f"Error running H1 for {symbol}: {str(e)}")

    scheduler.add_job(
        run_m15,
        trigger="cron",
        cron={"minute": "*/15"},
        id="strategy_runner_m15"
    )
    scheduler.add_job(
        run_h1,
        trigger="cron",
        cron={"minute": "0"},
        id="strategy_runner_h1"
    )

    yield

    scheduler.shutdown()
    mt5_connector.disconnect()
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(symbols.router, prefix="/api/v1")
app.include_router(market_data.router, prefix="/api/v1")
app.include_router(trading.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(websockets.router, prefix="/api/v1")
app.include_router(strategy.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1/backtest")
app.include_router(mt5.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
