"""SQLAlchemy engine + Base — import models before calling create_all."""
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)


class Base(DeclarativeBase):
    pass
