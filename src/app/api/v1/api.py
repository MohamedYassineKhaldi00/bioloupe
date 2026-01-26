from __future__ import annotations

from fastapi import APIRouter

from ...api.v1.endpoints import audit, auth, health, oauth, uploads

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(uploads.router, tags=["uploads"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, tags=["oauth"])
api_router.include_router(audit.router, prefix="/admin", tags=["audit"])
