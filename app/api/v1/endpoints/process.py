"""File processing endpoint — upload xlsx/csv, download processed CSV."""
import csv
import io
from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd

from app.db.session import get_db
from app.models.campaign import GlobalSettings, CampaignRule
from app.services.processor import process_rows, OUTPUT_COLUMNS
from app.services.memory import load_yesterday_memory, save_today_snapshot

router = APIRouter(prefix="/process", tags=["process"])


def _get_global_settings(db: Session) -> GlobalSettings:
    row = db.query(GlobalSettings).filter_by(id=1).first()
    if not row:
        row = GlobalSettings(id=1, min_ctr=0.37, max_ctr=0.55)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _get_campaign_rules(db: Session) -> dict:
    rules = db.query(CampaignRule).filter_by(enabled=True).all()
    result = {}
    for r in rules:
        ctr = {
            "min_ctr": r.min_ctr, "max_ctr": r.max_ctr,
            "min_vcr": r.min_vcr, "max_vcr": r.max_vcr,
            "min_viewability": r.min_viewability,
            "max_viewability": r.max_viewability,
        }
        for part in r.line_item_id.split(","):
            key = part.strip().lower()
            if key:
                result[key] = ctr
    return result


@router.post("")
async def process_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("xlsx", "xls", "csv"):
        raise HTTPException(400, "Only .xlsx, .xls, or .csv files are supported")

    contents = await file.read()
    try:
        df = (
            pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
            if ext == "csv"
            else pd.read_excel(io.BytesIO(contents), dtype=str, keep_default_na=False)
        )
    except Exception as e:
        raise HTTPException(400, f"Could not parse file: {e}")

    df = df.fillna("").replace({"nan": "", "NaN": "", "None": "", "NaT": ""})
    rows = df.to_dict(orient="records")

    yesterday   = load_yesterday_memory(db)
    global_s    = _get_global_settings(db)
    camp_rules  = _get_campaign_rules(db)

    file_campaign_names = sorted({
        str(r.get("Campaign", "")).strip().lower()
        for r in rows if r.get("Campaign")
    })
    matched_ids = sorted(set(file_campaign_names) & set(camp_rules.keys()))

    output_rows, snapshot = process_rows(
        rows,
        yesterday_memory=yesterday,
        global_min_ctr=global_s.min_ctr,
        global_max_ctr=global_s.max_ctr,
        campaign_ctr_rules=camp_rules,
    )
    save_today_snapshot(db, snapshot)

    # Build CSV output
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    for row in output_rows:
        writer.writerow({col: (row.get(col) if row.get(col) is not None else "") for col in OUTPUT_COLUMNS})
    csv_bytes = io.BytesIO(buf.getvalue().encode("utf-8-sig"))  # utf-8-sig adds BOM for Excel compatibility

    out_name = f"processed_{filename.rsplit('.', 1)[0]}.csv"

    return StreamingResponse(
        csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "X-Matched-Rules": ",".join(matched_ids),
            "X-File-Campaign-Names": ",".join(file_campaign_names[:20]),
            "Access-Control-Expose-Headers": "X-Matched-Rules, X-File-Campaign-Names, Content-Disposition",
        },
    )
