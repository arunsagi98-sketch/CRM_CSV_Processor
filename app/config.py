"""
Application configuration — reads from .env via python-dotenv.
All settings have safe defaults for local development.
"""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent  # CRM/

class Settings:
    # Server
    APP_TITLE: str = "CTR Processing Tool"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # CORS — comma-separated origins
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
    ).split(",")

    # Database — SQLite by default, swap to postgres:// in prod
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{ROOT_DIR / 'data' / 'ctr_app.db'}"
    )

    # CTR defaults (used when no campaign rule exists)
    DEFAULT_MIN_CTR: float = float(os.getenv("DEFAULT_MIN_CTR", "0.37"))
    DEFAULT_MAX_CTR: float = float(os.getenv("DEFAULT_MAX_CTR", "0.55"))

    # Frontend static dir
    FRONTEND_DIR: Path = ROOT_DIR / "frontend"


settings = Settings()
