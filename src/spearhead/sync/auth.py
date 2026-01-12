import requests
from typing import Optional, Tuple
from spearhead.config import settings
from spearhead.api.oauth_store import OAuthSessionStore

def refresh_session_if_needed(store: OAuthSessionStore, session_id: str) -> Optional[str]:
    """
    Checks if session is expired; if so and has refresh token, attempts refresh.
    Returns valid access_token or None if failed.
    """
    session = store.get(session_id)
    if not session:
        return None
    
    if not session.is_expired():
        return session.access_token

    if not session.refresh_token:
        return None

    # Refresh
    try:
        res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google.oauth_client_id,
                "client_secret": settings.google.oauth_client_secret,
                "refresh_token": session.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
        if res.ok:
            data = res.json()
            new_access = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            store.update_tokens(session_id, new_access, expires_in)
            return new_access
    except Exception:
        pass
    
    return None
