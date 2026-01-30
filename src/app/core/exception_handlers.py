from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..core.exceptions import (
    BioLoupeException,
    CacheException,
    DatabaseException,
    RateLimitExceeded,
    StorageException,
    VectorDBException,
)

logger = logging.getLogger(__name__)


async def bioloupe_exception_handler(request: Request, exc: BioLoupeException) -> JSONResponse:
    logger.error(
        "BioLoupe exception",
        extra={
            "error": str(exc),
            "status_code": exc.status_code,
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "bioloupe_error"}
    )


async def database_exception_handler(request: Request, exc: DatabaseException) -> JSONResponse:
    logger.error(
        "Database exception",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database service unavailable", "type": "database_error"}
    )


async def cache_exception_handler(request: Request, exc: CacheException) -> JSONResponse:
    logger.warning(
        "Cache exception",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Cache service unavailable", "type": "cache_error"}
    )


async def storage_exception_handler(request: Request, exc: StorageException) -> JSONResponse:
    logger.error(
        "Storage exception",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Storage service unavailable", "type": "storage_error"}
    )


async def vector_db_exception_handler(request: Request, exc: VectorDBException) -> JSONResponse:
    logger.error(
        "Vector DB exception",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Vector search service unavailable", "type": "vector_db_error"}
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning(
        "Rate limit exception",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": exc.detail, "type": "rate_limit"},
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError | ValidationError
) -> JSONResponse:
    logger.warning(
        "Validation error",
        extra={
            "errors": str(exc.errors()) if hasattr(exc, 'errors') else str(exc),
            "path": request.url.path,
        }
    )
    
    errors = exc.errors() if hasattr(exc, 'errors') else [{"msg": str(exc)}]
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors, "type": "validation_error"}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": "internal_error"}
    )
