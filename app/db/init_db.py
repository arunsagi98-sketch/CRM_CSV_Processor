"""
Create tables and run column-level migrations for existing SQLite DBs.
Call init_db() once at application startup.
"""
from pathlib import Path
from sqlalchemy import inspect, text

from app.config import settings
from app.db.base import Base, engine

# Import all models so Base.metadata knows about them
from app.models import campaign  # noqa: F401


def _ensure_data_dir() -> None:
    """Create the data/ directory for SQLite if it doesn't exist."""
    if "sqlite" in settings.DATABASE_URL:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def _run_column_migrations() -> None:
    """
    SQLAlchemy create_all does NOT add columns to existing tables.
    This ensures older local DBs stay in sync without a full migration tool.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "campaign_rules" in tables:
        existing = {col["name"] for col in inspector.get_columns("campaign_rules")}
        migrations = {
            "min_ctr":        "ALTER TABLE campaign_rules ADD COLUMN min_ctr FLOAT",
            "max_ctr":        "ALTER TABLE campaign_rules ADD COLUMN max_ctr FLOAT",
            "min_vcr":        "ALTER TABLE campaign_rules ADD COLUMN min_vcr FLOAT",
            "max_vcr":        "ALTER TABLE campaign_rules ADD COLUMN max_vcr FLOAT",
            "min_viewability":"ALTER TABLE campaign_rules ADD COLUMN min_viewability FLOAT",
            "max_viewability":"ALTER TABLE campaign_rules ADD COLUMN max_viewability FLOAT",
            "campaign_name":  "ALTER TABLE campaign_rules ADD COLUMN campaign_name VARCHAR DEFAULT ''",
            "enabled":        "ALTER TABLE campaign_rules ADD COLUMN enabled BOOLEAN DEFAULT 1",
            "created_at":     "ALTER TABLE campaign_rules ADD COLUMN created_at DATETIME",
            "updated_at":     "ALTER TABLE campaign_rules ADD COLUMN updated_at DATETIME",
        }
        with engine.begin() as conn:
            for col, sql in migrations.items():
                if col not in existing:
                    conn.execute(text(sql))


def init_db() -> None:
    _ensure_data_dir()
    Base.metadata.create_all(bind=engine)
    _run_column_migrations()
