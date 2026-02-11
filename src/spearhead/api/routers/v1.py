from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from spearhead.api.deps import (
    get_current_user,
    get_v1_ingestion_service,
    get_v1_query_service,
    require_auth,
)
from spearhead.domain.models import User
from spearhead.v1 import EventValidationError, FormEventV2, ResponseIngestionServiceV2, ResponseQueryServiceV2

router = APIRouter(prefix="/v1", tags=["v1"])


def _normalize_platoon_key(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    raw = str(name).strip()
    if not raw:
        return None
    lower = raw.lower()
    aliases = {
        "כפיר": "Kfir",
        "kfir": "Kfir",
        "kphir": "Kfir",
        "מחץ": "Mahatz",
        "mahatz": "Mahatz",
        "סופה": "Sufa",
        "sufa": "Sufa",
        "גדוד": "Battalion",
        "battalion": "Battalion",
    }
    return aliases.get(lower, raw)


def _resolve_scope(user: User, requested_platoon: Optional[str]) -> Optional[str]:
    user_scope = _normalize_platoon_key(user.platoon)
    req_scope = _normalize_platoon_key(requested_platoon)

    if user_scope and user_scope not in {"Battalion", "battalion"}:
        if req_scope and req_scope.lower() != user_scope.lower():
            raise HTTPException(status_code=403, detail="Access denied for requested platoon")
        return user_scope

    return req_scope


@router.post("/ingestion/forms/events")
def ingest_form_event(
    event: FormEventV2,
    svc: ResponseIngestionServiceV2 = Depends(get_v1_ingestion_service),
    _auth=Depends(require_auth),
):
    try:
        report = svc.ingest_event(event)
        return report.model_dump()
    except EventValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "unmapped_fields": exc.unmapped_fields})


@router.get("/metrics/overview")
def metrics_overview(
    week: Optional[str] = Query(None, alias="week"),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_platoon = _resolve_scope(user, None)
    return svc.overview(week_id=week, platoon_key=scoped_platoon)


@router.get("/metrics/platoons/{platoon}")
def metrics_platoon(
    platoon: str,
    week: Optional[str] = Query(None, alias="week"),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_platoon = _resolve_scope(user, platoon)
    if not scoped_platoon:
        raise HTTPException(status_code=400, detail="platoon is required")
    return svc.platoon_metrics(platoon_key=scoped_platoon, week_id=week)


@router.get("/metrics/tanks")
def metrics_tanks(
    platoon: Optional[str] = Query(None),
    week: Optional[str] = Query(None, alias="week"),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_platoon = _resolve_scope(user, platoon)
    if not scoped_platoon:
        raise HTTPException(status_code=400, detail="platoon is required")
    return svc.tank_metrics(platoon_key=scoped_platoon, week_id=week)


@router.get("/queries/gaps")
def query_gaps(
    week: Optional[str] = Query(None, alias="week"),
    platoon: Optional[str] = Query(None),
    group_by: str = Query("item", pattern="^(item|tank|family)$"),
    limit: int = Query(100, ge=1, le=300),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_platoon = _resolve_scope(user, platoon)
    return svc.gaps(week_id=week, platoon_key=scoped_platoon, group_by=group_by, limit=limit)


@router.get("/queries/trends")
def query_trends(
    metric: str = Query("total_gaps", pattern="^(reports|total_gaps|gap_rate|distinct_tanks)$"),
    window_weeks: int = Query(8, ge=1, le=26),
    platoon: Optional[str] = Query(None),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_platoon = _resolve_scope(user, platoon)
    return svc.trends(metric=metric, window_weeks=window_weeks, platoon_key=scoped_platoon)


@router.get("/queries/search")
def query_search(
    q: str = Query(..., min_length=2),
    week: Optional[str] = Query(None, alias="week"),
    platoon: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_platoon = _resolve_scope(user, platoon)
    return svc.search(q=q, week_id=week, platoon_key=scoped_platoon, limit=limit)


@router.get("/metadata/weeks")
def metadata_weeks(
    platoon: Optional[str] = Query(None),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_platoon = _resolve_scope(user, platoon)
    return svc.week_metadata(platoon_key=scoped_platoon)


@router.get("/views/battalion")
def view_battalion(
    week: Optional[str] = Query(None, alias="week"),
    company: Optional[str] = Query(None, alias="company"),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_company = _resolve_scope(user, company)
    return svc.battalion_sections_view(week_id=week, platoon_scope=scoped_company)


@router.get("/views/companies/{company}")
def view_company(
    company: str,
    week: Optional[str] = Query(None, alias="week"),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_company = _resolve_scope(user, company)
    if not scoped_company:
        raise HTTPException(status_code=400, detail="company is required")
    return svc.company_sections_view(company_key=scoped_company, week_id=week)


@router.get("/views/companies/{company}/sections/{section}/tanks")
def view_company_section_tanks(
    company: str,
    section: str,
    week: Optional[str] = Query(None, alias="week"),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_company = _resolve_scope(user, company)
    if not scoped_company:
        raise HTTPException(status_code=400, detail="company is required")
    try:
        return svc.company_section_tanks_view(company_key=scoped_company, section=section, week_id=week)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/views/companies/{company}/tanks")
def view_company_tanks(
    company: str,
    week: Optional[str] = Query(None, alias="week"),
    svc: ResponseQueryServiceV2 = Depends(get_v1_query_service),
    user: User = Depends(get_current_user),
):
    scoped_company = _resolve_scope(user, company)
    if not scoped_company:
        raise HTTPException(status_code=400, detail="company is required")
    return svc.company_tanks_view(company_key=scoped_company, week_id=week)
