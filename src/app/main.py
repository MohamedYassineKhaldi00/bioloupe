from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .api.v1.api import api_router
from .core.config import get_settings
from .core.events import shutdown_event, startup_event
from .core.exception_handlers import (
    bioloupe_exception_handler,
    cache_exception_handler,
    database_exception_handler,
    generic_exception_handler,
    storage_exception_handler,
    validation_exception_handler,
    vector_db_exception_handler,
)
from .core.exceptions import (
    BioLoupeException,
    CacheException,
    DatabaseException,
    StorageException,
    VectorDBException,
)
from .core.middleware import RequestIDMiddleware, TimingMiddleware
from .middleware.logging_middleware import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()


def create_app() -> FastAPI:
    configure_logging()
    
    settings = get_settings()
    
    app = FastAPI(
        title="BioLoupe API",
        description="Collaborative biotech research platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/openapi.json",
    )
    
    configure_middleware(app)
    configure_exception_handlers(app)
    configure_routes(app)
    
    logger.info("FastAPI application configured", extra={"environment": settings.environment})
    
    return app


def configure_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TimingMiddleware)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def configure_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BioLoupeException, bioloupe_exception_handler)
    app.add_exception_handler(DatabaseException, database_exception_handler)
    app.add_exception_handler(CacheException, cache_exception_handler)
    app.add_exception_handler(StorageException, storage_exception_handler)
    app.add_exception_handler(VectorDBException, vector_db_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


def configure_routes(app: FastAPI) -> None:
    app.include_router(api_router, prefix="/api/v1")
    
    return app


app = create_app()
