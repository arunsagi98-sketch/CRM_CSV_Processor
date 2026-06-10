"""Campaign rule CRUD endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.campaign import CampaignRule
from app.schemas.campaign import CampaignRuleCreate, CampaignRuleResponse

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _to_response(r: CampaignRule) -> dict:
    return {
        "id":              r.id,
        "campaign_id":     r.line_item_id,
        "campaign_name":   r.campaign_name,
        "min_ctr":         r.min_ctr,
        "max_ctr":         r.max_ctr,
        "min_vcr":         r.min_vcr,
        "max_vcr":         r.max_vcr,
        "min_viewability": r.min_viewability,
        "max_viewability": r.max_viewability,
        "enabled":         r.enabled,
        "created_at":      r.created_at.isoformat() if r.created_at else None,
    }


@router.get("", response_model=list[CampaignRuleResponse])
def list_campaigns(db: Session = Depends(get_db)):
    rules = db.query(CampaignRule).order_by(CampaignRule.created_at.desc()).all()
    return [_to_response(r) for r in rules]


@router.post("", response_model=CampaignRuleResponse)
def upsert_campaign(payload: CampaignRuleCreate, db: Session = Depends(get_db)):
    if payload.min_ctr and payload.max_ctr and payload.min_ctr >= payload.max_ctr:
        raise HTTPException(400, "min_ctr must be less than max_ctr")
    if payload.min_vcr and payload.max_vcr and payload.min_vcr > payload.max_vcr:
        raise HTTPException(400, "min_vcr must be <= max_vcr")
    if payload.min_viewability and payload.max_viewability and payload.min_viewability > payload.max_viewability:
        raise HTTPException(400, "min_viewability must be <= max_viewability")

    rule = db.query(CampaignRule).filter_by(line_item_id=payload.line_item_id).first()
    if rule:
        rule.campaign_name   = payload.campaign_name or ""
        rule.min_ctr         = payload.min_ctr          # None = use global fallback
        rule.max_ctr         = payload.max_ctr          # None = use global fallback
        rule.min_vcr         = payload.min_vcr
        rule.max_vcr         = payload.max_vcr
        rule.min_viewability = payload.min_viewability
        rule.max_viewability = payload.max_viewability
        rule.enabled         = payload.enabled if payload.enabled is not None else True
        rule.updated_at      = datetime.utcnow()
    else:
        rule = CampaignRule(
            line_item_id    = payload.line_item_id,
            campaign_name   = payload.campaign_name or "",
            min_ctr         = payload.min_ctr,           # None = use global fallback
            max_ctr         = payload.max_ctr,           # None = use global fallback
            min_vcr         = payload.min_vcr,
            max_vcr         = payload.max_vcr,
            min_viewability = payload.min_viewability,
            max_viewability = payload.max_viewability,
            enabled         = payload.enabled if payload.enabled is not None else True,
        )
        db.add(rule)

    db.commit()
    db.refresh(rule)
    return _to_response(rule)


@router.delete("/by-id/{rule_id}")
def delete_campaign(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(CampaignRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(404, "Campaign rule not found")
    db.delete(rule)
    db.commit()
    return {"deleted": rule_id}


@router.patch("/by-id/{rule_id}/toggle")
def toggle_campaign(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(CampaignRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(404, "Campaign rule not found")
    rule.enabled    = not rule.enabled
    rule.updated_at = datetime.utcnow()
    db.commit()
    return {"id": rule_id, "enabled": rule.enabled}
