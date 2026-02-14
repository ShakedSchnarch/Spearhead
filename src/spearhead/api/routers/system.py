import logging
import json
import base64
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode, unquote
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from spearhead.config import settings
from spearhead.api.deps import oauth_store
from spearhead.api.oauth_store import OAuthSession

logger = logging.getLogger("spearhead.api.system")
router = APIRouter()
# oauth_store is now imported from deps to share state

_DISABLED_PLATOON_TOKENS = {"palsam", "פלסם", "פלסמ", "פלס״מ", 'פלס"ם'}


def _normalize_platoon_token(value: str) -> str:
    return (
        str(value or "")
        .replace("׳", "")
        .replace("״", "")
        .replace("'", "")
        .replace('"', "")
        .replace(" ", "")
        .strip()
        .lower()
    )


def _is_disabled_platoon(value: str) -> bool:
    return _normalize_platoon_token(value) in _DISABLED_PLATOON_TOKENS

@router.get("/health")
def health():
    return {"status": "ok", "version": settings.app.version}


@router.get("/auth/google/start")
def google_oauth_start(
    state: Optional[str] = Query(None),
):
    """
    Starts Google OAuth flow by redirecting to Google authorization endpoint.
    Keeps UI simple in cloud deployments where build-time frontend env vars are not set.
    """
    cid = settings.google.oauth_client_id
    redirect_uri = settings.google.oauth_redirect_uri or "http://127.0.0.1:8000/auth/google/callback"
    if not cid:
        raise HTTPException(status_code=400, detail="OAuth client is not configured on server")

    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    if state:
        params["state"] = state

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=auth_url, status_code=307)


@router.get("/auth/google/callback")
def google_oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
):
    """
    Handles Google OAuth redirect, exchanges code for token, fetches email, and redirects to /app with token/email.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not code:
        # Happens when callback URL is opened manually from console/docs.
        return RedirectResponse(url="/spearhead/?authError=missing_oauth_code", status_code=307)

    # Parse state for context
    platoon = None
    view_mode = "battalion"  # Default if not specified
    if state:
        try:
            # Handle potential double encoding or direct JSON
            raw_state = unquote(state) if "%" in state else state
            # If still starts with %, unquote again? No, let's try strict parse
            # Sometimes frontend sends JSON string directly.
            state_data = json.loads(raw_state)
            if isinstance(state_data, dict):
                 platoon = state_data.get("platoon")
                 view_mode = state_data.get("viewMode") or "battalion"
        except Exception:
            logger.warning(f"Failed to parse OAuth state: {state}")
            pass

    cid = settings.google.oauth_client_id
    csecret = settings.google.oauth_client_secret
    redirect_uri = settings.google.oauth_redirect_uri or "http://127.0.0.1:8000/auth/google/callback"
    if not cid or not csecret:
        raise HTTPException(status_code=400, detail="OAuth client not configured on server")

    try:
        # Robust request with retries
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        token_res = session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": cid,
                "client_secret": csecret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth connection failed: {e}")

    if not token_res.ok:
        raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {token_res.text}")
    
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    id_token = token_data.get("id_token")

    email = None
    if access_token:
        try:
            userinfo = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if userinfo.ok:
                email = userinfo.json().get("email")
        except Exception:
            pass
    # Fallback: try decode id_token without verification
    if not email and id_token:
        try:
            payload_part = id_token.split(".")[1] + "=="
            payload = json.loads(base64.urlsafe_b64decode(payload_part.encode("utf-8")).decode("utf-8"))
            email = payload.get("email")
        except Exception:
            pass

    # Authorization Check
    authorized_users = settings.security.authorized_users
    if settings.security.require_auth_on_queries and not authorized_users:
        logger.error("OAuth blocked: SECURITY__AUTHORIZED_USERS is empty while auth is required.")
        raise HTTPException(status_code=403, detail="Authorized users list is not configured")

    assigned_role = authorized_users.get(email)
    if authorized_users and not assigned_role:
        logger.warning(f"Unauthorized login attempt: {email}")
        raise HTTPException(status_code=403, detail="User not authorized")

    # Determine effective platoon based on role
    # If role is a specific platoon (Kfir/Mahatz/Sufa), enforce it.
    # If role is 'battalion' or None, allow user selection (or default to view_mode).
    
    forced_platoon = None
    if assigned_role and assigned_role.lower() != "battalion":
        forced_platoon = assigned_role

    final_platoon = forced_platoon if forced_platoon else (platoon or "")
    if final_platoon and _is_disabled_platoon(final_platoon):
        return RedirectResponse(url="/spearhead/?authError=palsam_disabled", status_code=307)

    # If forced, view_mode MUST be platoon
    final_view_mode = "platoon" if forced_platoon else (view_mode or (final_platoon and "platoon") or "battalion")

    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth token exchange failed: missing access_token")

    expires_in = token_data.get("expires_in")
    expires_at = time.time() + expires_in if expires_in else None
    session_id = uuid4().hex
    oauth_store.set(
        session_id,
        OAuthSession(
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at,
            email=email,
            platoon=final_platoon,
            view_mode=final_view_mode,
        ),
    )

    params = []
    params.append(f"token={session_id}")
    if email:
        params.append(f"email={email}")
    if final_platoon:
        params.append(f"platoon={final_platoon}")
    if final_view_mode:
        params.append(f"viewMode={final_view_mode}")
    params.append(f"session={session_id}")
    qs = "&".join(params)
    target = "/spearhead/"
    if qs:
        target = f"/spearhead/?{qs}"
    return RedirectResponse(url=target, status_code=307)
