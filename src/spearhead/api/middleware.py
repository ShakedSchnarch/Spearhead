import time
import logging
from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse
from spearhead.config import settings

logger = logging.getLogger("spearhead.api")

async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid4().hex
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    return response

async def enforce_body_size(request: Request, call_next):
    limit_bytes = settings.security.max_upload_mb * 1024 * 1024
    header_val = request.headers.get("content-length")
    try:
        if header_val and int(header_val) > limit_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "request_too_large",
                    "detail": f"Max upload size is {settings.security.max_upload_mb}MB",
                },
            )
    except ValueError:
        pass
    return await call_next(request)

async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        status = getattr(response, "status_code", "error")
        rid = getattr(request.state, "request_id", None)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": round(duration_ms, 2),
                "request_id": rid,
            },
        )
