import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from spearhead.api.middleware import add_request_id, enforce_body_size, log_requests
from spearhead.api.routers import legacy, system, v1
from spearhead.config import settings
from spearhead.exceptions import DataSourceError

logging.basicConfig(level=getattr(logging, settings.logging.level.upper(), logging.INFO))
logger = logging.getLogger("spearhead.api")


def _reset_cached_dependencies() -> None:
    import spearhead.api.deps as deps

    deps._db_instance = None
    deps._v1_store_instance = None
    deps._v1_query_instance = None
    deps._v1_ingest_instance = None
    deps._v1_company_asset_ingest_instance = None
    deps._v1_store_backend = None


def _include_legacy_routes(app: FastAPI) -> None:
    from spearhead.api.routers import imports, intelligence, queries

    app.include_router(imports.router)
    app.include_router(queries.router)
    app.include_router(intelligence.router)


def _mount_frontend(app: FastAPI) -> None:
    dist_path = Path(__file__).resolve().parents[3] / "frontend-app" / "dist"
    if not dist_path.exists():
        return

    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/spearhead/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/")
    async def root_redirect():
        return RedirectResponse(url="/spearhead", status_code=307)

    @app.get("/spearhead")
    async def serve_spa_root():
        return FileResponse(dist_path / "index.html")

    @app.get("/spearhead/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")


def create_app(db_path: Optional[Path] = None) -> FastAPI:
    if db_path:
        settings.paths.db_path = db_path
        _reset_cached_dependencies()

    app = FastAPI(title="Spearhead API", version=settings.app.version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(add_request_id)
    app.middleware("http")(enforce_body_size)
    if settings.logging.log_requests:
        app.middleware("http")(log_requests)

    app.include_router(system.router)
    app.include_router(v1.router)
    if settings.app.enable_legacy_routes:
        _include_legacy_routes(app)
    else:
        app.include_router(legacy.router)

    _mount_frontend(app)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
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


app = create_app()
