"""Global CTR settings endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.campaign import GlobalSettings
from app.schemas.settings import GlobalSettingsSchema

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create(db: Session) -> GlobalSettings:
    row = db.query(GlobalSettings).filter_by(id=1).first()
    if not row:
        row = GlobalSettings(id=1, min_ctr=0.37, max_ctr=0.55)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=GlobalSettingsSchema)
def read_settings(db: Session = Depends(get_db)):
    s = _get_or_create(db)
    return {"min_ctr": s.min_ctr, "max_ctr": s.max_ctr}


@router.put("", response_model=GlobalSettingsSchema)
def update_settings(payload: GlobalSettingsSchema, db: Session = Depends(get_db)):
    if payload.min_ctr >= payload.max_ctr:
        raise HTTPException(400, "min_ctr must be less than max_ctr")
    s = _get_or_create(db)
    s.min_ctr = payload.min_ctr
    s.max_ctr = payload.max_ctr
    db.commit()
    return {"min_ctr": s.min_ctr, "max_ctr": s.max_ctr}
