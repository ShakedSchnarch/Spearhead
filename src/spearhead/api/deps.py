from __future__ import annotations

import base64
from typing import Any, Generator, Optional

from fastapi import Header, HTTPException

from spearhead.ai import InsightService, build_ai_client
from spearhead.api.oauth_store import OAuthSessionStore
from spearhead.config import settings
from spearhead.data.import_service import ImportService
from spearhead.data.repositories import FormRepository, TabularRepository
from spearhead.data.storage import Database
from spearhead.domain.models import User
from spearhead.logic.scoring import ScoringEngine
from spearhead.services import FormAnalytics, QueryService
from spearhead.services.exporter import ExcelExporter
from spearhead.services.intelligence import IntelligenceService
from spearhead.v1 import FormResponseParserV2, ResponseIngestionServiceV2, ResponseQueryServiceV2, ResponseStore

# Global/Cached instances
_db_instance: Optional[Database] = None
_v1_store_instance: Optional[Any] = None
_v1_query_instance: Optional[ResponseQueryServiceV2] = None
_v1_ingest_instance: Optional[ResponseIngestionServiceV2] = None
_v1_store_backend: Optional[str] = None

# Shared session store (in-memory)
oauth_store = OAuthSessionStore(ttl_seconds=86400)


def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(settings.paths.db_path)
    return _db_instance


def get_import_service() -> Generator[ImportService, None, None]:
    db = get_db()
    yield ImportService(db_path=db.db_path)


def get_query_service() -> Generator[QueryService, None, None]:
    db = get_db()
    repo = TabularRepository(db=db)
    yield QueryService(repository=repo)


def get_form_analytics() -> Generator[FormAnalytics, None, None]:
    db = get_db()
    repo = FormRepository(db=db)
    yield FormAnalytics(repository=repo)


def get_exporter() -> Generator[ExcelExporter, None, None]:
    db = get_db()
    repo = FormRepository(db=db)
    analytics = FormAnalytics(repository=repo)
    engine = ScoringEngine()
    intel_service = IntelligenceService(repository=repo, scoring_engine=engine)
    yield ExcelExporter(analytics=analytics, intelligence=intel_service)


def get_sync_service() -> Generator["SyncService", None, None]:
    db = get_db()
    import_service = ImportService(db_path=db.db_path)

    from spearhead.sync.google_sheets import GoogleSheetsProvider, SyncService

    provider = GoogleSheetsProvider(
        service_account_file=settings.google.service_account_file,
        api_key=settings.google.api_key,
        max_retries=settings.google.max_retries,
        backoff_seconds=settings.google.backoff_seconds,
    )
    yield SyncService(
        import_service=import_service,
        provider=provider,
        file_ids=settings.google.file_ids,
        cache_dir=settings.google.cache_dir,
    )


def get_intelligence_service() -> Generator[IntelligenceService, None, None]:
    db = get_db()
    repo = FormRepository(db=db)
    engine = ScoringEngine()
    yield IntelligenceService(repository=repo, scoring_engine=engine)


def get_insight_service() -> Generator[InsightService, None, None]:
    db = get_db()
    repo = TabularRepository(db=db)
    query_service = QueryService(repository=repo)
    ai_client = build_ai_client(settings)
    yield InsightService(db=db, query_service=query_service, ai_client=ai_client)


# ----- v1 responses-only services -----
def get_v1_store() -> ResponseStore:
    global _v1_store_instance, _v1_store_backend
    backend = (settings.storage.backend or "sqlite").strip().lower()
    if _v1_store_instance is None or _v1_store_backend != backend:
        if backend == "firestore":
            from spearhead.v1.store_firestore import FirestoreResponseStore

            _v1_store_instance = FirestoreResponseStore(
                project_id=settings.storage.firestore_project_id,
                database=settings.storage.firestore_database,
                collection_prefix=settings.storage.firestore_collection_prefix,
            )
        else:
            _v1_store_instance = ResponseStore(db=get_db())
        _v1_store_backend = backend
    return _v1_store_instance


def get_v1_query_service() -> ResponseQueryServiceV2:
    global _v1_query_instance
    if _v1_query_instance is None:
        _v1_query_instance = ResponseQueryServiceV2(store=get_v1_store())
    return _v1_query_instance


def get_v1_ingestion_service() -> ResponseIngestionServiceV2:
    global _v1_ingest_instance
    if _v1_ingest_instance is None:
        _v1_ingest_instance = ResponseIngestionServiceV2(
            store=get_v1_store(),
            parser=FormResponseParserV2(),
            metrics=get_v1_query_service(),
        )
    return _v1_ingest_instance


def require_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    token = settings.security.api_token
    basic_user = settings.security.basic_user
    basic_pass = settings.security.basic_pass
    if not token and not (basic_user and basic_pass):
        return

    if token and (
        authorization == f"Bearer {token}"
        or authorization == f"Token {token}"
        or x_api_key == token
    ):
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
        require_auth(authorization=authorization, x_api_key=x_api_key)


def get_current_user(
    x_oauth_session: Optional[str] = Header(None, alias="X-OAuth-Session"),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> User:
    if not x_oauth_session:
        if settings.security.api_token or settings.security.basic_user:
            try:
                require_auth(authorization=authorization, x_api_key=x_api_key)
                return User(email="api@spearhead.local", platoon=None, role="battalion")
            except HTTPException:
                raise HTTPException(status_code=401, detail="Missing authentication")

        if settings.security.require_auth_on_queries:
            raise HTTPException(status_code=401, detail="Missing authentication")

        return User(email="guest@spearhead.local", platoon=None, role="battalion")

    session = oauth_store.get_active_session(x_oauth_session)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    role = "platoon" if session.platoon and session.platoon.lower() != "battalion" else "battalion"
    return User(
        email=session.email or "unknown",
        platoon=session.platoon,
        role=role,
    )
