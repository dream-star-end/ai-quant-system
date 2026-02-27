"""
应用配置管理 - 使用环境变量和 .env 文件
"""
import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    APP_NAME: str = "AI Quant System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    API_PREFIX: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://dfinmeixhukxccsaefto.supabase.co")
    SUPABASE_KEY: str = os.getenv(
        "SUPABASE_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmaW5tZWl4aHVreGNjc2FlZnRvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ3NzcxNDgsImV4cCI6MjA4MDM1MzE0OH0.1KkRTv4U7lEKVFYpMcEpyJZtAp3mLIMKucSS6_9cAog",
    )

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # Exchange defaults
    DEFAULT_CRYPTO_EXCHANGE: str = os.getenv("DEFAULT_CRYPTO_EXCHANGE", "binance")

    # DeepSeek LLM
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_MAX_TOKENS: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
    DEEPSEEK_TEMPERATURE: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))

    # AI Model (local)
    MODEL_DIR: str = str(BASE_DIR / "models" / "saved")
    PREDICTION_CONFIDENCE_THRESHOLD: float = 0.6

    # Risk Management defaults
    MAX_POSITION_SIZE_PCT: float = float(os.getenv("MAX_POSITION_SIZE_PCT", "0.1"))
    MAX_PORTFOLIO_DRAWDOWN_PCT: float = float(os.getenv("MAX_PORTFOLIO_DRAWDOWN_PCT", "0.2"))
    DEFAULT_STOP_LOSS_PCT: float = float(os.getenv("DEFAULT_STOP_LOSS_PCT", "0.05"))
    DEFAULT_TAKE_PROFIT_PCT: float = float(os.getenv("DEFAULT_TAKE_PROFIT_PCT", "0.15"))
    COMMISSION_RATE: float = float(os.getenv("COMMISSION_RATE", "0.001"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = str(BASE_DIR / "logs")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
