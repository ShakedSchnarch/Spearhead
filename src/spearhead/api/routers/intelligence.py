from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from spearhead.api.deps import get_intelligence_service, get_current_user, require_query_auth
from spearhead.services.intelligence import IntelligenceService
from spearhead.domain.models import User
from spearhead.data.dto import PlatoonIntelligence, BattalionIntelligence

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.get("/platoon/{platoon_name}", response_model=PlatoonIntelligence, dependencies=[Depends(require_query_auth)])
def get_platoon_intelligence(
    platoon_name: str,
    week: Optional[str] = Query(None),
    service: IntelligenceService = Depends(get_intelligence_service),
    user: User = Depends(get_current_user),
):
    """
    Get detailed readiness intelligence for a specific platoon.
    Enforces Tenant Isolation: Users can only see their own platoon (unless role is 'battalion').
    """
    # Authorization Check
    # If user.platoon is set (e.g. "Kfir") and doesn't match requested "Kfir", deny.
    # We assume empty user.platoon means "Battalion/All" or we check role. 
    # Based on USER rules: "If I am Platoon, I see only my platoon".
    
    # Normalize comparison
    user_scope = (user.platoon or "").strip().lower()
    target_scope = platoon_name.strip().lower()
    
    # If user has a specific scope (not empty) and it doesn't match target
    # AND user is not explicitly a "battalion" role (if such role exists, assuming empty scope = battalion for now)
    if user_scope and user_scope != "battalion" and user_scope != target_scope:
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied. User scope '{user.platoon}' cannot access '{platoon_name}'."
        )

    return service.get_platoon_intelligence(platoon_name, week=week)

@router.get("/battalion", response_model=BattalionIntelligence, dependencies=[Depends(require_query_auth)])
def get_battalion_overview(
    week: Optional[str] = Query(None),
    service: IntelligenceService = Depends(get_intelligence_service),
    user: User = Depends(get_current_user),
):
    """
    Get battalion-level readiness overview.
    Enforces Tenant Isolation: Platoon-level users cannot access this endpoint.
    """
    user_scope = (user.platoon or "").strip().lower()
    
    # If user is restricted to a platoon, they cannot see battalion stats
    if user_scope and user_scope != "battalion":
         raise HTTPException(
            status_code=403, 
            detail=f"Access denied. Platoon user '{user.platoon}' cannot access Battalion Overview."
        )

    return service.get_battalion_intelligence(week=week)
