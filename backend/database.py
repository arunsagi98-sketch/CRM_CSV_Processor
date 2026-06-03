"""
SQLite database setup using SQLAlchemy.
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Boolean, DateTime, inspect, text
)
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "ctr_app.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class GlobalSettings(Base):
    __tablename__ = "global_settings"
    id      = Column(Integer, primary_key=True, default=1)
    min_ctr = Column(Float, default=0.37)
    max_ctr = Column(Float, default=0.55)


class CampaignRule(Base):
    __tablename__ = "campaign_rules"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    line_item_id  = Column(String, unique=True, nullable=False, index=True)
    campaign_name = Column(String, default='')
    min_ctr       = Column(Float, nullable=False)
    max_ctr       = Column(Float, nullable=False)
    min_vcr       = Column(Float, nullable=True)
    max_vcr       = Column(Float, nullable=True)
    min_viewability = Column(Float, nullable=True)
    max_viewability = Column(Float, nullable=True)
    enabled       = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class YesterdayMemory(Base):
    __tablename__ = "yesterday_memory"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    line_item_id = Column(String, nullable=False, index=True)
    clicks       = Column(Integer, nullable=False)
    ctr          = Column(String, nullable=False)
    run_date     = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)


def ensure_schema():
    """
    SQLAlchemy create_all creates missing tables, but it does not add columns to
    tables that already exist. Keep older local SQLite databases compatible with
    the current models.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "campaign_rules" in tables:
        existing = {col["name"] for col in inspector.get_columns("campaign_rules")}
        migrations = {
            "min_ctr": "ALTER TABLE campaign_rules ADD COLUMN min_ctr FLOAT NOT NULL DEFAULT 0.37",
            "max_ctr": "ALTER TABLE campaign_rules ADD COLUMN max_ctr FLOAT NOT NULL DEFAULT 0.55",
            "min_vcr": "ALTER TABLE campaign_rules ADD COLUMN min_vcr FLOAT",
            "max_vcr": "ALTER TABLE campaign_rules ADD COLUMN max_vcr FLOAT",
            "min_viewability": "ALTER TABLE campaign_rules ADD COLUMN min_viewability FLOAT",
            "max_viewability": "ALTER TABLE campaign_rules ADD COLUMN max_viewability FLOAT",
            "campaign_name": "ALTER TABLE campaign_rules ADD COLUMN campaign_name VARCHAR DEFAULT ''",
            "enabled": "ALTER TABLE campaign_rules ADD COLUMN enabled BOOLEAN DEFAULT 1",
            "created_at": "ALTER TABLE campaign_rules ADD COLUMN created_at DATETIME",
            "updated_at": "ALTER TABLE campaign_rules ADD COLUMN updated_at DATETIME",
        }
        with engine.begin() as conn:
            for column, statement in migrations.items():
                if column not in existing:
                    conn.execute(text(statement))


ensure_schema()


def get_db():
    with Session(engine) as session:
        yield session


def load_yesterday_memory(session: Session) -> dict:
    rows = session.query(YesterdayMemory).all()
    memory = {}
    for r in rows:
        memory.setdefault(r.line_item_id, []).append({'clicks': r.clicks, 'ctr': r.ctr})
    return memory


def save_today_snapshot(session: Session, snapshot: dict):
    session.query(YesterdayMemory).delete()
    today = datetime.utcnow().strftime("%d/%m/%Y")
    for line_id, entries in snapshot.items():
        for e in entries:
            session.add(YesterdayMemory(
                line_item_id=line_id,
                clicks=e['clicks'],
                ctr=e['ctr'],
                run_date=today,
            ))
    session.commit()


def get_global_settings(session: Session) -> GlobalSettings:
    row = session.query(GlobalSettings).filter_by(id=1).first()
    if not row:
        row = GlobalSettings(id=1, min_ctr=0.37, max_ctr=0.55)
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def get_campaign_rules(session: Session) -> dict:
    """
    Returns {campaign_name_lowercase: {min_ctr, max_ctr}}.
    Matching is case-insensitive. Supports comma-separated names.
    """
    rules = session.query(CampaignRule).filter_by(enabled=True).all()
    result = {}
    for r in rules:
        ctr = {
            'min_ctr': r.min_ctr,
            'max_ctr': r.max_ctr,
            'min_vcr': r.min_vcr,
            'max_vcr': r.max_vcr,
            'min_viewability': r.min_viewability,
            'max_viewability': r.max_viewability,
        }
        for part in r.line_item_id.split(','):
            name = part.strip().lower()
            if name:
                result[name] = ctr
    return result
