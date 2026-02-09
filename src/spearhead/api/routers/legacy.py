from fastapi import APIRouter, Response

router = APIRouter(tags=["legacy"])

DEPRECATION_HEADERS = {
    "Deprecation": "true",
    "X-API-Deprecated": "true",
    "Sunset": "2026-03-01",
    "Link": '</v1>; rel="successor-version"',
}


def _gone(message: str) -> Response:
    return Response(
        content=message,
        status_code=410,
        headers=DEPRECATION_HEADERS,
        media_type="text/plain",
    )


@router.get("/exports/platoon")
def exports_platoon():
    return _gone("Deprecated. Use /v1/queries/* and /v1/metrics/* endpoints.")


@router.get("/exports/battalion")
def exports_battalion():
    return _gone("Deprecated. Use /v1/queries/* and /v1/metrics/* endpoints.")


@router.post("/imports/platoon-loadout")
def import_platoon_loadout():
    return _gone("Deprecated. Use /v1/ingestion/forms/events.")


@router.post("/imports/battalion-summary")
def import_battalion_summary():
    return _gone("Deprecated. Use /v1/ingestion/forms/events.")


@router.post("/imports/form-responses")
def import_form_responses():
    return _gone("Deprecated. Use /v1/ingestion/forms/events.")
