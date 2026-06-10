"""SQLAlchemy ORM models."""
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from app.db.base import Base


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id      = Column(Integer, primary_key=True, default=1)
    min_ctr = Column(Float, default=0.37)
    max_ctr = Column(Float, default=0.55)


class CampaignRule(Base):
    __tablename__ = "campaign_rules"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    line_item_id    = Column(String, unique=True, nullable=False, index=True)
    campaign_name   = Column(String, default="")
    min_ctr         = Column(Float, nullable=True)
    max_ctr         = Column(Float, nullable=True)
    min_vcr         = Column(Float, nullable=True)
    max_vcr         = Column(Float, nullable=True)
    min_viewability = Column(Float, nullable=True)
    max_viewability = Column(Float, nullable=True)
    enabled         = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class YesterdayMemory(Base):
    __tablename__ = "yesterday_memory"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    line_item_id = Column(String, nullable=False, index=True)
    clicks       = Column(Integer, nullable=False)
    ctr          = Column(String, nullable=False)
    run_date     = Column(String, nullable=False)
