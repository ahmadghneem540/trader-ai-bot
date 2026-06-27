# TraderAI Verification Checklist

## Prerequisites
- Python 3.12 installed
- Docker and Docker Compose installed
- MetaTrader 5 terminal (optional - for Windows only, required for live trading)

---

## Step 1: Verify Project Structure
Ensure the following structure exists:
```
trader_ai/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config/
│   │   │   ├── database/
│   │   │   ├── exceptions/
│   │   │   ├── logging/
│   │   │   └── scheduler.py
│   │   ├── domain/
│   │   │   └── models/
│   │   ├── infrastructure/
│   │   │   ├── database/
│   │   │   ├── mt5/
│   │   │   └── market_data/
│   │   ├── application/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   ├── schemas/
│   │   │   └── middleware/
│   │   └── tests/
│   ├── alembic/
│   ├── .env
│   ├── .env.example
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .gitignore
├── README.md
├── TECHNICAL_SPECIFICATION.md
└── VERIFICATION.md
```

---

## Step 2: Start Services with Docker Compose
Run this from the project root to start all services:
```bash
docker-compose up -d --build
```

Wait for all containers to start up. Check status:
```bash
docker-compose ps
```
You should see 3 containers running: traderai-postgres, traderai-backend, traderai-frontend

---

## Step 3: Verify Database Initialization
1. Check that PostgreSQL container is running and healthy
2. Set up local environment to run Alembic:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```
3. Generate and run migrations:
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```
This will create all required database tables.

---

## Step 4: Verify Backend API & Docs
1. Visit http://localhost:8000/docs - you should see Swagger UI
2. Visit http://localhost:8000/redoc - you should see ReDoc UI
3. Check health endpoint: http://localhost:8000/api/v1/health
Should return JSON with status, database, mt5, version

---

## Step 5: Verify Frontend Dashboard
1. Visit http://localhost:3000 - you should see the login page
2. Register a new user:
   - Fill out username, email, password
   - Click Register
3. Login with your credentials
4. Explore the dashboard tabs:
   - Overview: Account info, MT5 status, bot status
   - Positions: Open positions
   - Market Watch: Symbol list
   - Strategy: Strategy configuration
   - Logs: Activity logs
   - Strategy Tester: Backtest strategies!

---

## Step 6: Verify Phase 4 Features - Strategy Tester & Backtesting
1. From the dashboard, click "Strategy Tester"
2. Select a Strategy (EMATrendStrategy is default available)
3. Select a Symbol (you need to sync symbols first via /api/v1/symbols/sync in docs!)
4. Select Timeframe, Start Date, End Date, Initial Balance
5. Click "Run Backtest"
6. Wait a few seconds and refresh to see backtest status
7. When status is "completed", click "View" to see detailed results
8. From Swagger UI, try these endpoints:
   - GET /api/v1/backtest/strategies/list
   - POST /api/v1/backtest/run
   - GET /api/v1/backtest/results
   - GET /api/v1/backtest/{backtest_id}
   - GET /api/v1/backtest/{backtest_id}/trades

---

## Step 7: Verify Logs
Check container logs to ensure no errors:
```bash
docker-compose logs -f
```

---

## Step 7: Verify Phase 2 Features (Optional - Requires MT5 on Windows)
If you're on Windows and have MetaTrader 5 installed:
1. Update backend/.env with:
   - MT5_LOGIN: Your MT5 account login number
   - MT5_PASSWORD: Your MT5 account password
   - MT5_SERVER: Your MT5 broker server
   - MT5_PATH: (optional) Path to terminal64.exe if not in default location
2. Restart backend container:
```bash
docker-compose restart backend
```
3. Go to http://localhost:8000/docs and use the /api/v1/health/mt5/connect endpoint
4. Now you can use all MT5 features:
   - Sync symbols
   - Fetch candles
   - Execute trades (use demo account!)
   - View positions
   - View account overview

---

## Step 8: Verify Phase 5 - Auto Trading (Demo Only)
If you're on Windows and have MetaTrader 5 demo account installed:
1. Ensure safety mode is ON (default - configures `safety_mode: true`)
2. From Dashboard, go to Strategy tab and configure risk parameters
3. From Dashboard Overview tab, click "Start Bot"
4. Verify:
   - Bot status becomes Active
   - Logs appear in Logs tab
   - Auto-trades only on demo account (no real trading!)
5. Supported symbols: XAUUSD, EURUSD, GBPUSD, USDJPY
6. Scheduled runs: every 15 mins (M15) and every hour (H1)

---

## Completed Items
- ✅ Project Structure following DDD & Clean Code
- ✅ FastAPI Backend (with Swagger/Redoc docs)
- ✅ PostgreSQL Database with SQLAlchemy 2.x
- ✅ Alembic Migrations
- ✅ Structured Logging
- ✅ Configuration Management
- ✅ MT5 Connector
- ✅ Symbol Service
- ✅ Historical & Live Market Data Collection
- ✅ APScheduler for background tasks
- ✅ Trading Service (buy, sell, close, modify SL/TP)
- ✅ Trade Journal (orders/positions in DB)
- ✅ REST API Endpoints for all features
- ✅ JWT Authentication
- ✅ Strategy Configuration API
- ✅ Logs API
- ✅ React Dashboard
- ✅ WebSocket endpoints (for realtime data)
- ✅ Docker & Docker Compose
- ✅ Strategy Engine (StrategyBase, EMATrendStrategy)
- ✅ Indicators (SMA, EMA, RSI, MACD, ATR)
- ✅ Backtesting Engine
- ✅ Performance Analytics
- ✅ Backtest Database Models & Repositories
- ✅ Backtest API Endpoints
- ✅ Strategy Tester UI
- ✅ Backtest Results UI
- ✅ Auto Trading Engine (Demo Only)
- ✅ Risk Management (Daily/Weekly Loss Limits, Max Trades, Consecutive Losses)
- ✅ Trailing Stop & Breakeven
- ✅ Bot Scheduler (M15/H1)
- ✅ Dashboard Real-time Monitoring

## Missing Items
- ⏳ Unit Tests
- ⏳ Integration Tests
- ⏳ Full WebSocket integration in frontend
- ⏳ AI Engine
- ⏳ News Analyzer
- ⏳ Telegram Notifications
- ⏳ Report Export (CSV/PDF)

---

## Commands to Run & Test Everything
```bash
# Start all services
docker-compose up -d --build

# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop services and remove volumes (DELETES ALL DATA!)
docker-compose down -v

# Run backend locally (after setting up venv)
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run frontend locally (after setting up venv and npm install)
cd frontend
npm start
```