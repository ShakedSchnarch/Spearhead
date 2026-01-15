from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import FileResponse
from spearhead.services import QueryService, FormAnalytics
from spearhead.services.exporter import ExcelExporter
from spearhead.ai import InsightService
from spearhead.data.dto import GapReport, TrendPoint
from spearhead.api.deps import (
    get_query_service,
    get_form_analytics,
    get_insight_service,
    get_exporter,
    require_query_auth,
    require_auth,
    get_current_user,
)
from spearhead.domain.models import User

router = APIRouter()

# --- Tabular Queries ---
@router.get("/queries/tabular/totals")
def tabular_totals(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    top_n: int = 20,
    platoon: Optional[str] = Query(None, description="Optional platoon filter"),
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    qs: QueryService = Depends(get_query_service),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        # Auto-scope restricted users
        platoon = user.platoon
    return qs.tabular_totals(section=section, top_n=top_n, platoon=platoon, week=week)

@router.get("/queries/tabular/gaps")
def tabular_gaps(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    top_n: int = 20,
    platoon: Optional[str] = Query(None, description="Optional platoon filter"),
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    qs: QueryService = Depends(get_query_service),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        platoon = user.platoon
    return qs.tabular_gaps(section=section, top_n=top_n, platoon=platoon, week=week)[:top_n]

@router.get("/queries/tabular/by-family")
def tabular_by_family(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    platoon: Optional[str] = Query(None, description="Optional platoon filter"),
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    top_n: int = Query(50, ge=1, le=200),
    qs: QueryService = Depends(get_query_service),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        platoon = user.platoon
    return qs.tabular_by_family(section=section, platoon=platoon, week=week, top_n=top_n)

@router.get("/queries/tabular/gaps-by-platoon")
def tabular_gaps_by_platoon(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    top_n: int = Query(100, ge=1, le=500),
    qs: QueryService = Depends(get_query_service),
    _auth=Depends(require_query_auth),
):
    return qs.tabular_gaps_by_platoon(section=section, week=week, top_n=top_n)

@router.get("/queries/tabular/search")
def tabular_search(
    q: str = Query(..., description="Free text to search (item/column/value)"),
    section: Optional[str] = Query(None, description="Optional section filter (zivud|ammo|summary_zivud|summary_ammo)"),
    platoon: Optional[str] = Query(None, description="Optional platoon filter"),
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    limit: int = Query(50, ge=1, le=200),
    qs: QueryService = Depends(get_query_service),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        platoon = user.platoon
    return qs.tabular_search(q=q, section=section, platoon=platoon, week=week, limit=limit)

@router.get("/queries/tabular/by-platoon")
def tabular_by_platoon(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    top_n: int = 20,
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    qs: QueryService = Depends(get_query_service),
    _auth=Depends(require_query_auth),
):
    return qs.tabular_by_platoon(section=section, top_n=top_n, week=week)

@router.get("/queries/tabular/delta")
def tabular_delta(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    top_n: int = 20,
    qs: QueryService = Depends(get_query_service),
    _auth=Depends(require_query_auth),
):
    return qs.tabular_delta(section=section, top_n=top_n)

@router.get("/queries/tabular/variance")
def tabular_variance(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    top_n: int = 20,
    qs: QueryService = Depends(get_query_service),
    _auth=Depends(require_query_auth),
):
    return qs.tabular_variance_vs_summary(section=section, top_n=top_n)

@router.get("/queries/trends")
def tabular_trends(
    section: str = Query(..., description="Section name, e.g., zivud or ammo"),
    top_n: int = 5,
    platoon: Optional[str] = Query(None, description="Optional platoon filter"),
    weeks: int = Query(8, description="Number of recent weeks to include"),
    qs: QueryService = Depends(get_query_service),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        platoon = user.platoon
    return qs.tabular_trends(section=section, top_n=top_n, platoon=platoon, window_weeks=weeks)

# --- Forms Analytics ---
@router.get("/queries/forms/summary")
def form_summary(
    mode: str = Query("battalion", description="battalion|platoon"),
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    platoon: Optional[str] = Query(None, description="Target platoon when mode=platoon"),
    platoon_override: Optional[str] = Query(
        None, description="Force all rows to be grouped under this platoon name"
    ),
    analytics: FormAnalytics = Depends(get_form_analytics),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        # Enforce platoon mode and target
        mode = "platoon"
        platoon = user.platoon
        platoon_override = user.platoon
            
    summary = analytics.summarize(week=week, platoon_override=platoon_override, prefer_latest=True)
    serialized = analytics.serialize_summary(summary)

    if mode == "platoon":
        target = platoon_override or platoon
        if not target:
            raise HTTPException(status_code=400, detail="platoon is required when mode=platoon")
        
        # Robust lookup
        platoon_data = serialized.get("platoons", {}).get(target)
        if not platoon_data:
            # Instead of 404, return empty structure to prevent UI crash
            return {
                "mode": "platoon", 
                "platoon": target, 
                "week": serialized.get("week"), 
                "summary": None, 
                "note": "No data found"
            }
        
        return {"mode": "platoon", "platoon": target, "week": serialized.get("week"), "summary": platoon_data}

    return {"mode": "battalion", **serialized}

@router.get("/queries/forms/coverage")
def form_coverage(
    week: Optional[str] = Query(None, description="Week label YYYY-Www; defaults to latest/current"),
    window_weeks: int = Query(4, ge=1, le=12, description="Recent weeks to compare for anomalies"),
    analytics: FormAnalytics = Depends(get_form_analytics),
    user: User = Depends(get_current_user),
):
    # Coverage is battalion-wide usually. 
    # If restricted, we might want to filtered coverage? 
    # Update: Now we support filtered coverage via analytics.coverage(platoon=...)
    platoon_filter = None
    if user.platoon:
         platoon_filter = user.platoon
         # raise HTTPException(status_code=403, detail="Battalion coverage view restricted")
    
    return analytics.coverage(week=week, window_weeks=window_weeks, prefer_latest=True, platoon=platoon_filter)

@router.get("/queries/forms/status")
def form_status(
    qs: QueryService = Depends(get_query_service),
    _auth=Depends(require_query_auth),
):
    return qs.form_status_counts()

@router.get("/queries/forms/gaps", response_model=list[GapReport])
def form_gaps_detailed(
    week: Optional[str] = Query(None, description="Week label YYYY-Www"),
    platoon: Optional[str] = Query(None, description="Optional platoon filter"),
    analytics: FormAnalytics = Depends(get_form_analytics),
    _auth=Depends(require_query_auth),
):
    return analytics.get_gaps(week=week, platoon=platoon)

# --- Insights ---
@router.get("/insights")
def insights(
    section: str = Query("zivud", description="Section to analyze"),
    platoon: Optional[str] = Query(None, description="Optional platoon filter"),
    top_n: int = Query(5, ge=1, le=20),
    svc: InsightService = Depends(get_insight_service),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        platoon = user.platoon
    return svc.generate(section=section, platoon=platoon, top_n=top_n)

# --- Exports ---
@router.get("/exports/platoon")
def export_platoon(
    platoon: str = Query(..., description="Platoon name to export"),
    week: str = Query(..., description="Week label YYYY-Www (Required)"),
    exporter: ExcelExporter = Depends(get_exporter),
    user: User = Depends(get_current_user),
):
    if user.platoon and platoon != user.platoon:
        raise HTTPException(status_code=403, detail="Platoon export restricted")

    try:
        path = exporter.export_platoon(platoon=platoon, week=week)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )

@router.get("/exports/battalion")
def export_battalion(
    week: str = Query(..., description="Week label YYYY-Www (Required)"),
    exporter: ExcelExporter = Depends(get_exporter),
    user: User = Depends(get_current_user),
):
    if user.platoon:
        raise HTTPException(status_code=403, detail="Battalion export restricted")

    try:
        path = exporter.export_battalion(week=week)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )
