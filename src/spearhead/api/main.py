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
from spearhead.api.routers import system, imports, queries, sync, intelligence

# Configure logging
logging.basicConfig(level=getattr(logging, settings.logging.level.upper(), logging.INFO))
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
    # Reverted /api prefix to match frontend expectation (root mounting)
    app.include_router(system.router)
    app.include_router(imports.router)
    app.include_router(queries.router)
    app.include_router(sync.router)
    app.include_router(intelligence.router)

    # Locate built frontend assets relative to repo root (src/spearhead/api/main.py -> ../../.. = repo)
    dist_path = Path(__file__).resolve().parents[3] / "frontend-app" / "dist"
    
    if dist_path.exists():
        # 1. Mount assets specifically at /spearhead/assets
        #    This ensures requests to /spearhead/assets/... are served from dist/assets folder
        app.mount("/spearhead/assets", StaticFiles(directory=dist_path / "assets"), name="assets")

        # 2. Redirect root to /spearhead
        @app.get("/")
        async def root_redirect():
            return RedirectResponse(url="/spearhead", status_code=307)
        
        # 3. Serve public files (like logos) if they exist at root of dist, otherwise serve index.html for SPA
        from fastapi.responses import FileResponse
        
        @app.get("/spearhead/{full_path:path}")
        async def serve_spa(full_path: str):
            # If the path points to a real file in dist (e.g. logos/Kfir_logo.JPG), serve it.
            # otherwise, serve index.html
            file_path = dist_path / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            
            return FileResponse(dist_path / "index.html")
            
        @app.get("/spearhead")
        async def serve_spa_root():
            return FileResponse(dist_path / "index.html")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Allow Starlette/FastAPI HTTP exceptions to pass through (or handle them specifically if needed)
        # But wait, exception handlers don't cascade. If I catch Exception, I catch everything.
        # So I MUST implement a specific handler for HTTPException if I want different behavior,
        # OR check isinstance here.
        from starlette.exceptions import HTTPException as StarletteHTTPException
        if isinstance(exc, StarletteHTTPException):
             return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        
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
