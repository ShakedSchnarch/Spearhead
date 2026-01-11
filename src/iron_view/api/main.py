import base64
import logging
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from iron_view.config import settings
from iron_view.ai import build_ai_client, InsightService
from iron_view.exceptions import DataSourceError
from iron_view.data.import_service import ImportService
from iron_view.data.storage import Database
from iron_view.services import QueryService, FormAnalytics
from iron_view.services.exporter import ExcelExporter
from iron_view.sync.google_sheets import GoogleSheetsProvider, SyncService

logger = logging.getLogger("iron_view.api")


def create_app(db_path: Optional[Path] = None) -> FastAPI:
    """
    Factory to build the FastAPI application.
    Allows overriding db_path (used in tests).
    """
    db = Database(db_path or settings.paths.db_path)
    import_service = ImportService(db_path=db.db_path)
    query_service = QueryService(db=db)
    ai_client = build_ai_client(settings)
    insight_service = InsightService(db=db, query_service=query_service, ai_client=ai_client)

    app = FastAPI(title="IronView API", version=settings.app.version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response

    @app.middleware("http")
    async def enforce_body_size(request: Request, call_next):
        limit_bytes = settings.security.max_upload_mb * 1024 * 1024
        header_val = request.headers.get("content-length")
        try:
            if header_val and int(header_val) > limit_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "request_too_large",
                        "detail": f"Max upload size is {settings.security.max_upload_mb}MB",
                    },
                )
        except ValueError:
            pass
        return await call_next(request)

    if settings.logging.log_requests:
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            start = time.perf_counter()
            response = None
            try:
                response = await call_next(request)
                return response
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                status = getattr(response, "status_code", "error")
                rid = getattr(request.state, "request_id", None)
                logger.info(
                    "request",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "duration_ms": round(duration_ms, 2),
                        "request_id": rid,
                    },
                )

    # Dependency providers
    def get_import_service():
        return import_service

    def get_query_service():
        return query_service

    def get_form_analytics():
        return FormAnalytics(db=db)

    def get_exporter():
        return ExcelExporter(analytics=FormAnalytics(db=db))

    def get_sync_service():
        provider = GoogleSheetsProvider(
            service_account_file=settings.google.service_account_file,
            api_key=settings.google.api_key,
            max_retries=settings.google.max_retries,
            backoff_seconds=settings.google.backoff_seconds,
        )
        return SyncService(
            import_service=import_service,
            provider=provider,
            file_ids=settings.google.file_ids,
            cache_dir=settings.google.cache_dir,
        )

    def get_insight_service():
        return insight_service

    def require_auth(
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ):
        token = settings.security.api_token
        basic_user = settings.security.basic_user
        basic_pass = settings.security.basic_pass
        if not token and not (basic_user and basic_pass):
            return

        if token and (authorization == f"Bearer {token}" or authorization == f"Token {token}" or x_api_key == token):
            return

        if authorization and authorization.startswith("Basic "):
            try:
                decoded = base64.b64decode(authorization.split(" ", 1)[1]).decode("utf-8")
                username, password = decoded.split(":", 1)
                if username == basic_user and password == basic_pass:
                    return
            except Exception:
                pass

        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Bearer"})

    def require_query_auth(
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ):
        if settings.security.require_auth_on_queries:
            return require_auth(authorization=authorization, x_api_key=x_api_key)

    # Locate built frontend assets relative to repo root (src/iron_view/api/main.py -> ../../.. = repo)
    dist_path = Path(__file__).resolve().parents[3] / "frontend-app" / "dist"
    if dist_path.exists():
        app.mount("/app", StaticFiles(directory=dist_path, html=True), name="frontend")
        @app.get("/")
        async def root_redirect():
            return RedirectResponse(url="/app", status_code=307)

    @app.post("/imports/platoon-loadout")
    async def import_platoon_loadout(
        file: UploadFile = File(...),
        svc: ImportService = Depends(get_import_service),
        _auth=Depends(require_auth),
    ):
        path = _save_temp_file(file)
        inserted = svc.import_platoon_loadout(path)
        return {"inserted": inserted}

    @app.post("/imports/battalion-summary")
    async def import_battalion_summary(
        file: UploadFile = File(...),
        svc: ImportService = Depends(get_import_service),
        _auth=Depends(require_auth),
    ):
        path = _save_temp_file(file)
        inserted = svc.import_battalion_summary(path)
        return {"inserted": inserted}

    @app.post("/imports/form-responses")
    async def import_form_responses(
        file: UploadFile = File(...),
        svc: ImportService = Depends(get_import_service),
        _auth=Depends(require_auth),
    ):
        path = _save_temp_file(file)
        inserted = svc.import_form_responses(path)
        return {"inserted": inserted}

    @app.get("/queries/tabular/totals")
    def tabular_totals(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        platoon: Optional[str] = Query(None, description="Optional platoon filter"),
        week: Optional[str] = Query(None, description="Week label YYYY-Www"),
        qs: QueryService = Depends(get_query_service),
        _auth=Depends(require_query_auth),
    ):
        return qs.tabular_totals(section=section, top_n=top_n, platoon=platoon, week=week)

    @app.get("/queries/tabular/gaps")
    def tabular_gaps(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        platoon: Optional[str] = Query(None, description="Optional platoon filter"),
        week: Optional[str] = Query(None, description="Week label YYYY-Www"),
        qs: QueryService = Depends(get_query_service),
        _auth=Depends(require_query_auth),
    ):
        return qs.tabular_gaps(section=section, top_n=top_n, platoon=platoon, week=week)[:top_n]

    @app.get("/queries/tabular/by-platoon")
    def tabular_by_platoon(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        week: Optional[str] = Query(None, description="Week label YYYY-Www"),
        qs: QueryService = Depends(get_query_service),
        _auth=Depends(require_query_auth),
    ):
        return qs.tabular_by_platoon(section=section, top_n=top_n, week=week)

    @app.get("/queries/tabular/delta")
    def tabular_delta(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        qs: QueryService = Depends(get_query_service),
        _auth=Depends(require_query_auth),
    ):
        return qs.tabular_delta(section=section, top_n=top_n)

    @app.get("/queries/tabular/variance")
    def tabular_variance(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        qs: QueryService = Depends(get_query_service),
        _auth=Depends(require_query_auth),
    ):
        return qs.tabular_variance_vs_summary(section=section, top_n=top_n)

    @app.get("/queries/trends")
    def tabular_trends(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 5,
        platoon: Optional[str] = Query(None, description="Optional platoon filter"),
        weeks: int = Query(8, description="Number of recent weeks to include"),
        qs: QueryService = Depends(get_query_service),
        _auth=Depends(require_query_auth),
    ):
        return qs.tabular_trends(section=section, top_n=top_n, platoon=platoon, window_weeks=weeks)

    @app.get("/queries/forms/summary")
    def form_summary(
        mode: str = Query("battalion", description="battalion|platoon"),
        week: Optional[str] = Query(None, description="Week label YYYY-Www"),
        platoon: Optional[str] = Query(None, description="Target platoon when mode=platoon"),
        platoon_override: Optional[str] = Query(
            None, description="Force all rows to be grouped under this platoon name"
        ),
        analytics: FormAnalytics = Depends(get_form_analytics),
        _auth=Depends(require_query_auth),
    ):
        summary = analytics.summarize(week=week, platoon_override=platoon_override, prefer_latest=True)
        serialized = analytics.serialize_summary(summary)

        if mode == "platoon":
            target = platoon_override or platoon
            if not target:
                raise HTTPException(status_code=400, detail="platoon is required when mode=platoon")
            platoon_data = serialized.get("platoons", {}).get(target)
            if not platoon_data:
                raise HTTPException(status_code=404, detail=f"No data found for platoon '{target}'")
            return {"mode": "platoon", "platoon": target, "week": serialized.get("week"), "summary": platoon_data}

        return {"mode": "battalion", **serialized}

    @app.get("/queries/forms/coverage")
    def form_coverage(
        week: Optional[str] = Query(None, description="Week label YYYY-Www; defaults to latest/current"),
        window_weeks: int = Query(4, ge=1, le=12, description="Recent weeks to compare for anomalies"),
        analytics: FormAnalytics = Depends(get_form_analytics),
        _auth=Depends(require_query_auth),
    ):
        return analytics.coverage(week=week, window_weeks=window_weeks, prefer_latest=True)

    @app.get("/insights")
    def insights(
        section: str = Query("zivud", description="Section to analyze"),
        platoon: Optional[str] = Query(None, description="Optional platoon filter"),
        top_n: int = Query(5, ge=1, le=20),
        svc: InsightService = Depends(get_insight_service),
        _auth=Depends(require_query_auth),
    ):
        return svc.generate(section=section, platoon=platoon, top_n=top_n)

    @app.get("/queries/forms/status")
    def form_status(
        qs: QueryService = Depends(get_query_service),
        _auth=Depends(require_query_auth),
    ):
        return qs.form_status_counts()

    @app.get("/exports/platoon")
    def export_platoon(
        platoon: str = Query(..., description="Platoon name to export"),
        week: Optional[str] = Query(None, description="Week label YYYY-Www; defaults to latest"),
        exporter: ExcelExporter = Depends(get_exporter),
        _auth=Depends(require_auth),
    ):
        try:
            path = exporter.export_platoon(platoon=platoon, week=week)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=path.name,
        )

    @app.get("/exports/battalion")
    def export_battalion(
        week: Optional[str] = Query(None, description="Week label YYYY-Www; defaults to latest"),
        exporter: ExcelExporter = Depends(get_exporter),
        _auth=Depends(require_auth),
    ):
        try:
            path = exporter.export_battalion(week=week)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=path.name,
        )

    @app.post("/sync/google")
    def sync_google(
        target: str = Query("all", description="all|platoon_loadout|battalion_summary|form_responses"),
        sync_service: SyncService = Depends(get_sync_service),
        _auth=Depends(require_auth),
    ):
        if not settings.google.enabled:
            raise HTTPException(status_code=400, detail="Google sync is disabled in settings.")

        if target == "all":
            return sync_service.sync_all()
        if target == "platoon_loadout":
            return {"platoon_loadout": sync_service.sync_platoon_loadout()}
        if target == "battalion_summary":
            return {"battalion_summary": sync_service.sync_battalion_summary()}
        if target == "form_responses":
            return {"form_responses": sync_service.sync_form_responses()}
        raise HTTPException(status_code=400, detail="Invalid target")

    @app.get("/sync/status")
    def sync_status(sync_service: SyncService = Depends(get_sync_service)):
        return sync_service.get_status()

    @app.get("/health")
    def health():
        return {"status": "ok", "version": settings.app.version}

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        rid = getattr(request.state, "request_id", None)
        payload = {"error": exc.detail or "error", "status_code": exc.status_code}
        if rid:
            payload["request_id"] = rid
        return JSONResponse(status_code=exc.status_code, content=payload)

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


def _save_temp_file(upload: UploadFile) -> Path:
    try:
        max_bytes = settings.security.max_upload_mb * 1024 * 1024
        suffix = Path(upload.filename or "").suffix or ".xlsx"
        prefix_raw = Path(upload.filename or "upload").stem or "upload"
        safe_prefix = prefix_raw.replace("/", "_").replace("\\", "_") + "_"
        with NamedTemporaryFile(delete=False, suffix=suffix, prefix=safe_prefix) as tmp:
            content = upload.file.read()
            if max_bytes and len(content) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large; max {settings.security.max_upload_mb}MB",
                )
            tmp.write(content)
            return Path(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")


# Module-level app for uvicorn entrypoint
app = create_app()
