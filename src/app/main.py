from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="BioLoupe API", version="1.0.0")

    # Lazily import routers to avoid importing heavy modules (models, DB clients)
    # at module import time which makes unit testing harder.
    from app.api.v1.api import api_router

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
