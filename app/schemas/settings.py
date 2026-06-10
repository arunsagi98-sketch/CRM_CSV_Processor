"""Pydantic schemas for global settings."""
from pydantic import BaseModel, field_validator


class GlobalSettingsSchema(BaseModel):
    min_ctr: float
    max_ctr: float

    @field_validator("min_ctr", "max_ctr")
    @classmethod
    def validate_ctr(cls, v):
        if not (0 < v < 100):
            raise ValueError("CTR must be between 0 and 100 (percent)")
        return v
