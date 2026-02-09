from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from spearhead.config import settings
from spearhead.data.import_service import ImportService
from spearhead.api.deps import get_import_service, require_auth

router = APIRouter(prefix="/imports", tags=["Imports"])

def _save_temp_file(upload: UploadFile) -> Path:
    try:
        max_bytes = settings.security.max_upload_mb * 1024 * 1024
        suffix = Path(upload.filename or "").suffix or ".xlsx"
        prefix_raw = Path(upload.filename or "upload").stem or "upload"
        safe_prefix = prefix_raw.replace("/", "_").replace("\\", "_") + "_"
        with NamedTemporaryFile(delete=False, suffix=suffix, prefix=safe_prefix) as tmp:
            content = upload.file.read()
            if max_bytes and len(content) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large; max {settings.security.max_upload_mb}MB",
                )
            tmp.write(content)
            return Path(tmp.name)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

@router.post("/platoon-loadout")
async def import_platoon_loadout(
    file: UploadFile = File(...),
    _auth=Depends(require_auth),
):
    raise HTTPException(
        status_code=410,
        detail="Endpoint deprecated: use /v1/ingestion/forms/events (responses-only mode).",
        headers={"X-API-Deprecated": "true", "X-API-Remove-After": "2026-03-31"},
    )

@router.post("/battalion-summary")
async def import_battalion_summary(
    file: UploadFile = File(...),
    _auth=Depends(require_auth),
):
    raise HTTPException(
        status_code=410,
        detail="Endpoint deprecated: use /v1/ingestion/forms/events (responses-only mode).",
        headers={"X-API-Deprecated": "true", "X-API-Remove-After": "2026-03-31"},
    )

@router.post("/form-responses")
async def import_form_responses(
    file: UploadFile = File(...),
    svc: ImportService = Depends(get_import_service),
    _auth=Depends(require_auth),
):
    path = _save_temp_file(file)
    inserted = svc.import_form_responses(path)
    return {"inserted": inserted}
