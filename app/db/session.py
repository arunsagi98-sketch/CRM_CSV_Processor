"""Database session factory and FastAPI dependency."""
from sqlalchemy.orm import Session
from app.db.base import engine


def get_db():
    """FastAPI dependency — yields a DB session, closes on exit."""
    with Session(engine) as session:
        yield session
