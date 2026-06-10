"""Yesterday-memory inspection & management endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.campaign import YesterdayMemory

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/summary")
def memory_summary(db: Session = Depends(get_db)):
    rows = db.query(YesterdayMemory).all()
    by_id: dict = {}
    for r in rows:
        by_id.setdefault(r.line_item_id, []).append({"clicks": r.clicks, "ctr": r.ctr})
    return {"line_items": len(by_id), "total_entries": len(rows), "data": by_id}


@router.delete("")
def clear_memory(db: Session = Depends(get_db)):
    db.query(YesterdayMemory).delete()
    db.commit()
    return {"cleared": True}
