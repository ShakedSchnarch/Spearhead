from typing import Optional, Generator
from pathlib import Path
from fastapi import Header, HTTPException
import base64

from spearhead.config import settings
from spearhead.data.storage import Database
from spearhead.data.import_service import ImportService
from spearhead.services import QueryService, FormAnalytics
from spearhead.services.exporter import ExcelExporter
from spearhead.ai import build_ai_client, InsightService
from spearhead.sync.google_sheets import GoogleSheetsProvider, SyncService
from spearhead.api.oauth_store import OAuthSessionStore
from spearhead.domain.models import User

# Global/Cached instances
_db_instance: Optional[Database] = None
# Shared Session Store (In-Memory)
oauth_store = OAuthSessionStore(ttl_seconds=86400) # 24h explicitly

def get_db() -> Database:
    """
    Returns the shared Database instance.
    For tests, override this dependency or set settings.paths.db_path before first call.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(settings.paths.db_path)
    return _db_instance

def get_import_service() -> Generator[ImportService, None, None]:
    db = get_db()
    yield ImportService(db_path=db.db_path)

def get_query_service() -> Generator[QueryService, None, None]:
    db = get_db()
    yield QueryService(db=db)

def get_form_analytics() -> Generator[FormAnalytics, None, None]:
    db = get_db()
    yield FormAnalytics(db=db)

def get_exporter() -> Generator[ExcelExporter, None, None]:
    db = get_db()
    analytics = FormAnalytics(db=db)
    yield ExcelExporter(analytics=analytics)

def get_sync_service() -> Generator[SyncService, None, None]:
    db = get_db()
    # Note: ImportService is needed here. We create a fresh one or could reuse if we passed it.
    # SyncService depends on ImportService.
    # To keep it simple, we instantiate ImportService(db_path=db.db_path)
    import_service = ImportService(db_path=db.db_path)
    
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

def get_insight_service() -> Generator[InsightService, None, None]:
    db = get_db()
    # Re-use query service
    query_service = QueryService(db=db)
    ai_client = build_ai_client(settings)
    yield InsightService(db=db, query_service=query_service, ai_client=ai_client)

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
        require_auth(authorization=authorization, x_api_key=x_api_key)


def get_current_user(
    x_oauth_session: Optional[str] = Header(None, alias="X-OAuth-Session")
) -> User:
    """
    Resolves the authenticated user from the session ID.
    Enforces strict access control.
    """
    if not x_oauth_session:
        # For development/debug without auth, checking settings? 
        # No, "Sterile Auth" means we require it.
        # But maybe we allow basic auth fallback? For now, strict session.
        raise HTTPException(status_code=401, detail="Missing authentication")

    session = oauth_store.get_active_session(x_oauth_session)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return User(
        email=session.email or "unknown",
        platoon=session.platoon, # This is the enforced/sterile platoon
        role="viewer" # basic default
    )
