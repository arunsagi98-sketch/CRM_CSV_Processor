"""Pydantic request/response schemas for campaign rules."""
from typing import Optional
from pydantic import BaseModel, field_validator


class CampaignRuleCreate(BaseModel):
    line_item_id:    str
    campaign_name:   Optional[str] = ""
    min_ctr:         Optional[float] = None
    max_ctr:         Optional[float] = None
    min_vcr:         Optional[float] = None
    max_vcr:         Optional[float] = None
    min_viewability: Optional[float] = None
    max_viewability: Optional[float] = None
    enabled:         Optional[bool] = True

    @field_validator("min_ctr", "max_ctr", "min_vcr", "max_vcr", "min_viewability", "max_viewability")
    @classmethod
    def validate_percent(cls, v):
        if v is not None and not (0 < v < 100):
            raise ValueError("Percent values must be between 0 and 100")
        return v


class CampaignRuleResponse(BaseModel):
    id:              int
    campaign_id:     str       # = line_item_id
    campaign_name:   str
    min_ctr:         Optional[float]
    max_ctr:         Optional[float]
    min_vcr:         Optional[float]
    max_vcr:         Optional[float]
    min_viewability: Optional[float]
    max_viewability: Optional[float]
    enabled:         bool
    created_at:      Optional[str]

    model_config = {"from_attributes": True}
