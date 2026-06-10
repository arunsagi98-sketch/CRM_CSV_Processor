"""Yesterday-memory helpers — persist CTR snapshots across daily runs."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.campaign import YesterdayMemory


def load_yesterday_memory(session: Session) -> dict:
    rows = session.query(YesterdayMemory).all()
    memory: dict = {}
    for r in rows:
        memory.setdefault(r.line_item_id, []).append({"clicks": r.clicks, "ctr": r.ctr})
    return memory


def save_today_snapshot(session: Session, snapshot: dict) -> None:
    session.query(YesterdayMemory).delete()
    today = datetime.utcnow().strftime("%d/%m/%Y")
    for line_id, entries in snapshot.items():
        for e in entries:
            session.add(YesterdayMemory(
                line_item_id=line_id,
                clicks=e["clicks"],
                ctr=e["ctr"],
                run_date=today,
            ))
    session.commit()
