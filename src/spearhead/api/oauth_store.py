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

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < time()


class OAuthSessionStore:
    """
    Lightweight in-memory store for OAuth sessions (access/refresh tokens) with TTL.
    Intended for single-process deployments; swap with persistent store if needed.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._sessions: Dict[str, OAuthSession] = {}

    def set(self, session_id: str, session: OAuthSession) -> None:
        # normalize expiry if not provided by provider
        if session.expires_at is None and self.ttl_seconds:
            session.expires_at = time() + self.ttl_seconds
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
            self._sessions[session_id] = session

    def get(self, session_id: Optional[str]) -> Optional[OAuthSession]:
        if not session_id:
            return None
        self._purge()
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        # We return the session even if expired if it has a refresh token?
        # Typically the router middleware checks expiry and attempts refresh.
        # But for 'get' in a store, typically we just return what we have.
        # The is_expired() check in get() was destructive. 
        # Better design: if I have a refresh token, I shouldn't auto-pop on generic expiry check, 
        # unless I am also purging absolutely dead sessions.
        
        # Let's keep logic: if expired and NO refresh token -> pop.
        # If expired and YES refresh token -> return it, caller handles refresh.
        if session.is_expired():
            if not session.refresh_token:
                self._sessions.pop(session_id, None)
                return None
            # Has refresh token, return it so we can refresh
            return session
            
        return session

    def _purge(self) -> None:
        # Purge only if expired AND no refresh token, or if expired > some long retention (e.g. 1 day)?
        # For simplicity: purge if expired and no refresh token.
        expired = [
            sid for sid, s in self._sessions.items() 
            if s.is_expired() and not s.refresh_token
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
