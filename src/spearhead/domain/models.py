from typing import Optional
from pydantic import BaseModel, Field

class User(BaseModel):
    """
    Represents an authenticated user in the system.
    """
    email: str
    platoon: Optional[str] = None # If None/Empty -> Battalion/Admin access. If set -> scoped to that platoon.
    role: str = "viewer" # viewer, editor, admin

    @property
    def is_battalion(self) -> bool:
        return not self.platoon or self.platoon == "battalion"
