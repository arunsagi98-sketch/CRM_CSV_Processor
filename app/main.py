"""
FastAPI application factory.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.v1.router import api_router
from app.db.init_db import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"http://localhost:\d+",
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Matched-Rules", "X-File-Campaign-Names"],
    )

    # API routes
    app.include_router(api_router)

    # Initialise DB (create tables, run column migrations)
    @app.on_event("startup")
    def on_startup():
        init_db()

    # Serve frontend static files (if directory exists)
    if settings.FRONTEND_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(settings.FRONTEND_DIR)), name="static")

        @app.get("/")
        def serve_frontend():
            return FileResponse(str(settings.FRONTEND_DIR / "index.html"))

    return app


app = create_app()
