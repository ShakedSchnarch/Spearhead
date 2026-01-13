from dataclasses import dataclass
from time import time
from typing import Optional, Dict


@dataclass
class OAuthSession:
    access_token: str
    refresh_token: Optional[str]
    expires_at: Optional[float]
    email: Optional[str]
    platoon: Optional[str]
    view_mode: Optional[str]
    created_at: float = 0.0

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < time()


class OAuthSessionStore:
    """
    Lightweight in-memory store for OAuth sessions (access/refresh tokens) with TTL.
    Intended for single-process deployments; swap with persistent store if needed.
    """

    def __init__(self, ttl_seconds: int = 86400):  # Default 24h
        self.ttl_seconds = ttl_seconds
        self._sessions: Dict[str, OAuthSession] = {}

    def set(self, session_id: str, session: OAuthSession) -> None:
        if not session.created_at:
            session.created_at = time()
        
        # normalize expiry if not provided by provider
        if session.expires_at is None and self.ttl_seconds:
             # This is token expiry, not session expiry. 
             # Session expiry is implicit via cleanup or check against created_at?
             # Let's treat valid session as one that was created < TTL ago.
             pass
             
        self._sessions[session_id] = session
        self._purge()

    def update_tokens(self, session_id: str, access_token: str, expires_in: int, refresh_token: Optional[str] = None):
        """
        Updates an existing session with new tokens.
        """
        session = self._sessions.get(session_id)
        if session:
            session.access_token = access_token
            session.expires_at = time() + expires_in if expires_in else None
            if refresh_token:
                session.refresh_token = refresh_token
            # Refreshing tokens extends session life? Usually yes.
            session.created_at = time() 
            self._sessions[session_id] = session

    def get_active_session(self, session_id: Optional[str]) -> Optional[OAuthSession]:
        """
        Returns session only if it exists and is within global TTL of the store (24h default).
        Does NOT check token expiry (that's for the middleware to handle via refresh).
        """
        if not session_id:
            return None
            
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check Global Session TTL (e.g. force re-login every 24h)
        if time() - session.created_at > self.ttl_seconds:
            self._sessions.pop(session_id, None)
            return None
            
        return session

    def get(self, session_id: Optional[str]) -> Optional[OAuthSession]:
        # Legacy get, maps to active session check for safety
        return self.get_active_session(session_id)

    def _purge(self) -> None:
        """
        Removes sessions that have exceeded the global TTL.
        """
        now = time()
        expired = [
            sid for sid, s in self._sessions.items() 
            if (now - s.created_at > self.ttl_seconds)
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
