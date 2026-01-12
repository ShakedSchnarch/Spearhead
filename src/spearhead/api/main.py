import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from spearhead.config import settings
from spearhead.exceptions import DataSourceError
from spearhead.data.storage import Database
from spearhead.api.middleware import add_request_id, enforce_body_size, log_requests
from spearhead.api.deps import get_db

# Routers
from spearhead.api.routers import system, imports, queries, sync

logger = logging.getLogger("spearhead.api")

def create_app(db_path: Optional[Path] = None) -> FastAPI:
    """
    Factory to build the FastAPI application.
    Allows overriding db_path (used in tests via global settings update or dependency override).
    """
    # If db_path is provided, we might want to update the settings or the global dependency.
    # For simplicity in this refactor, if db_path is custom, we assume the caller
    # handles dependency overrides or we set it in settings before calling.
    # However, to maintain compatibility with existing tests that pass db_path:
    if db_path:
        settings.paths.db_path = db_path
        # Force re-init of DB if needed in deps.py
        import spearhead.api.deps as deps
        deps._db_instance = None # reset global instance

    app = FastAPI(title="IronView API", version=settings.app.version)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom Middleware
    app.middleware("http")(add_request_id)
    app.middleware("http")(enforce_body_size)
    if settings.logging.log_requests:
        app.middleware("http")(log_requests)

    # Include Routers
    app.include_router(system.router)
    app.include_router(imports.router)
    app.include_router(queries.router)
    app.include_router(sync.router)

    # Locate built frontend assets relative to repo root (src/spearhead/api/main.py -> ../../.. = repo)
    dist_path = Path(__file__).resolve().parents[3] / "frontend-app" / "dist"
    if dist_path.exists():
        app.mount("/app", StaticFiles(directory=dist_path, html=True), name="frontend")
        @app.get("/")
        async def root_redirect():
            return RedirectResponse(url="/app", status_code=307)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None)
        logger.exception("Unhandled error", extra={"path": str(request.url), "request_id": rid})
        payload = {"error": "internal_error", "detail": "Unexpected server error"}
        if rid:
            payload["request_id"] = rid
        return JSONResponse(status_code=500, content=payload)

    @app.exception_handler(DataSourceError)
    async def datasource_exception_handler(request: Request, exc: DataSourceError):
        rid = getattr(request.state, "request_id", None)
        payload = {"error": "invalid_source", "detail": str(exc)}
        if rid:
            payload["request_id"] = rid
        return JSONResponse(status_code=422, content=payload)

    return app

# Module-level app for uvicorn entrypoint
app = create_app()
