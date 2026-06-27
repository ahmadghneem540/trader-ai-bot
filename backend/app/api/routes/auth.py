from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database.session import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.infrastructure.database.repositories import UserRepository, AccountRepository, RiskLimitRepository
from app.api.schemas.schemas import User, UserCreate, Token
from app.core.config.settings import settings
import logging
import random

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Registering user: {user.username}")
        user_repo = UserRepository(db)
        account_repo = AccountRepository(db)
        risk_limit_repo = RiskLimitRepository(db)
        existing_user = user_repo.get_by_username(user.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )
        hashed_password = get_password_hash(user.password)
        db_user = user_repo.create({
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_superuser": False,
        })
        # Create default account (use a random integer as login to ensure uniqueness)
        db_account = account_repo.create({
            "login": random.randint(100000, 999999),  # Random 6-digit number as login
            "server": "Demo Server",
            "account_type": "demo",
            "broker": "TraderAI Demo",
            "is_active": True,
        })
        # Create default risk limit
        risk_limit_repo.create({
            "account_id": db_account.id,
            "max_daily_loss": 100.0,
            "max_drawdown": 500.0,  # Using max_drawdown instead of max_weekly_loss
            "max_open_positions": 5,  # Using max_open_positions instead of max_open_trades
            "is_active": True,
        })
        logger.info(f"User {user.username} registered successfully with default account")
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
