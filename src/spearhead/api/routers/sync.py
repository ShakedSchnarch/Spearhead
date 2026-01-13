from typing import Optional
from fastapi import APIRouter, Header, Query, Depends, HTTPException
from spearhead.config import settings
from spearhead.sync.google_sheets import SyncService
from spearhead.api.deps import get_sync_service, require_auth
from spearhead.api.routers.system import oauth_store

router = APIRouter(prefix="/sync", tags=["Sync"])

@router.post("/google")
def sync_google(
    target: str = Query("all", description="all|platoon_loadout|battalion_summary|form_responses"),
    sync_service: SyncService = Depends(get_sync_service),
    oauth_session: Optional[str] = Header(None, alias="X-OAuth-Session"),
    auth_header: Optional[str] = Header(None, alias="Authorization"),
    oauth_token: Optional[str] = Query(None, description="Optional OAuth session token"),
    _auth=Depends(require_auth),
):
    if not settings.google.enabled:
        raise HTTPException(status_code=400, detail="Google sync is disabled in settings.")

    session_token = oauth_session or oauth_token
    if not session_token and auth_header and auth_header.startswith("Bearer "):
        session_token = auth_header.split(" ", 1)[1]
    
    from spearhead.sync.auth import refresh_session_if_needed
    user_access_token = refresh_session_if_needed(oauth_store, session_token) if session_token else None

    if target == "all":
        return sync_service.sync_all(user_token=user_access_token)
    if target == "platoon_loadout":
        return {"platoon_loadout": sync_service.sync_platoon_loadout(user_token=user_access_token)}
    if target == "battalion_summary":
        return {"battalion_summary": sync_service.sync_battalion_summary(user_token=user_access_token)}
    if target == "form_responses":
        return {"form_responses": sync_service.sync_form_responses(user_token=user_access_token)}
    raise HTTPException(status_code=400, detail="Invalid target")

@router.get("/status")
def sync_status(
    sync_service: SyncService = Depends(get_sync_service),
    oauth_session: Optional[str] = Header(None, alias="X-OAuth-Session"),
):
    base_status = sync_service.get_status()
    
    # Determine Auth Mode
    auth_mode = "none"
    user_email = None
    
    if oauth_session:
        session = oauth_store.get(oauth_session)
        if session:
            auth_mode = "user"
            user_email = session.email
    elif settings.google.service_account_path:
        auth_mode = "service"
    
    return {
        **base_status,
        "auth_mode": auth_mode,
        "source": "google" if settings.google.enabled else "local",
        "user": user_email
    }
