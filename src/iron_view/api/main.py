from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from iron_view.config import settings
from iron_view.data.import_service import ImportService
from iron_view.data.storage import Database
from iron_view.services import QueryService
from iron_view.sync.google_sheets import GoogleSheetsProvider, SyncService


def create_app(db_path: Optional[Path] = None) -> FastAPI:
    """
    Factory to build the FastAPI application.
    Allows overriding db_path (used in tests).
    """
    db = Database(db_path or settings.paths.db_path)
    import_service = ImportService(db_path=db.db_path)
    query_service = QueryService(db=db)

    app = FastAPI(title="IronView API", version=settings.app.version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Dependency providers
    def get_import_service():
        return import_service

    def get_query_service():
        return query_service

    def get_sync_service():
        provider = GoogleSheetsProvider(
            service_account_file=settings.google.service_account_file,
            api_key=settings.google.api_key,
        )
        return SyncService(
            import_service=import_service,
            provider=provider,
            file_ids=settings.google.file_ids,
        )

    dist_path = Path(__file__).resolve().parents[2] / "frontend-app" / "dist"
    if dist_path.exists():
        app.mount("/app", StaticFiles(directory=dist_path, html=True), name="frontend")

    @app.post("/imports/platoon-loadout")
    async def import_platoon_loadout(
        file: UploadFile = File(...),
        svc: ImportService = Depends(get_import_service),
    ):
        path = _save_temp_file(file)
        inserted = svc.import_platoon_loadout(path)
        return {"inserted": inserted}

    @app.post("/imports/battalion-summary")
    async def import_battalion_summary(
        file: UploadFile = File(...),
        svc: ImportService = Depends(get_import_service),
    ):
        path = _save_temp_file(file)
        inserted = svc.import_battalion_summary(path)
        return {"inserted": inserted}

    @app.post("/imports/form-responses")
    async def import_form_responses(
        file: UploadFile = File(...),
        svc: ImportService = Depends(get_import_service),
    ):
        path = _save_temp_file(file)
        inserted = svc.import_form_responses(path)
        return {"inserted": inserted}

    @app.get("/queries/tabular/totals")
    def tabular_totals(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        qs: QueryService = Depends(get_query_service),
    ):
        return qs.tabular_totals(section=section, top_n=top_n)

    @app.get("/queries/tabular/gaps")
    def tabular_gaps(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        qs: QueryService = Depends(get_query_service),
    ):
        return qs.tabular_gaps(section=section, top_n=top_n)[:top_n]

    @app.get("/queries/tabular/by-platoon")
    def tabular_by_platoon(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        qs: QueryService = Depends(get_query_service),
    ):
        return qs.tabular_by_platoon(section=section, top_n=top_n)

    @app.get("/queries/tabular/delta")
    def tabular_delta(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        qs: QueryService = Depends(get_query_service),
    ):
        return qs.tabular_delta(section=section, top_n=top_n)

    @app.get("/queries/tabular/variance")
    def tabular_variance(
        section: str = Query(..., description="Section name, e.g., zivud or ammo"),
        top_n: int = 20,
        qs: QueryService = Depends(get_query_service),
    ):
        return qs.tabular_variance_vs_summary(section=section, top_n=top_n)

    @app.get("/queries/forms/status")
    def form_status(qs: QueryService = Depends(get_query_service)):
        return qs.form_status_counts()

    @app.post("/sync/google")
    def sync_google(
        target: str = Query("all", description="all|platoon_loadout|battalion_summary|form_responses"),
        sync_service: SyncService = Depends(get_sync_service),
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

    @app.get("/health")
    def health():
        return {"status": "ok", "version": settings.app.version}

    return app


def _save_temp_file(upload: UploadFile) -> Path:
    try:
        with NamedTemporaryFile(delete=False, suffix=Path(upload.filename).suffix or ".xlsx") as tmp:
            content = upload.file.read()
            tmp.write(content)
            return Path(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")


# Module-level app for uvicorn entrypoint
app = create_app()
