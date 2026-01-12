import logging
import json
import base64
import time
import requests
from urllib.parse import unquote
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from spearhead.config import settings
from spearhead.api.oauth_store import OAuthSessionStore, OAuthSession

logger = logging.getLogger("spearhead.api.system")
router = APIRouter()
oauth_store = OAuthSessionStore(ttl_seconds=3600)

@router.get("/health")
def health():
    return {"status": "ok", "version": settings.app.version}

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
        raise HTTPException(status_code=400, detail="Missing OAuth code")

    cid = settings.google.oauth_client_id
    csecret = settings.google.oauth_client_secret
    redirect_uri = settings.google.oauth_redirect_uri or "http://127.0.0.1:8000/app/"
    if not cid or not csecret:
        raise HTTPException(status_code=400, detail="OAuth client not configured on server")

    try:
        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": cid,
                "client_secret": csecret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
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

    # Parse state if provided
    platoon = ""
    view_mode = ""
    if state:
        try:
            decoded_state = json.loads(unquote(state))
            platoon = decoded_state.get("platoon", "")
            view_mode = decoded_state.get("viewMode", "")
        except Exception:
            pass

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
            platoon=platoon,
            view_mode=view_mode or (platoon and "platoon") or "battalion",
        ),
    )

    params = []
    params.append(f"token={session_id}")
    if email:
        params.append(f"email={email}")
    if platoon:
        params.append(f"platoon={platoon}")
    if view_mode:
        params.append(f"viewMode={view_mode}")
    params.append(f"session={session_id}")
    qs = "&".join(params)
    target = "/app/"
    if qs:
        target = f"/app/?{qs}"
    return RedirectResponse(url=target, status_code=307)
