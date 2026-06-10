"""Aggregates all v1 endpoint routers under /api/v1."""
from fastapi import APIRouter
from app.api.v1.endpoints import campaigns, process, settings, memory

api_router = APIRouter(prefix="/api")

api_router.include_router(settings.router)
api_router.include_router(campaigns.router)
api_router.include_router(process.router)
api_router.include_router(memory.router)
