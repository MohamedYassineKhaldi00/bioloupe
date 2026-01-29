from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()

# Core endpoints
from app.api.v1.endpoints import users, teams
api_router.include_router(users.router)
api_router.include_router(teams.router)

# Health, auth, oauth, audit (if available)
try:
    from app.api.v1.endpoints import health, auth, oauth, audit

    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
    api_router.include_router(oauth.router, tags=["oauth"])
    api_router.include_router(audit.router, prefix="/admin", tags=["audit"])
except Exception:
    pass

# Optional endpoints (may require extra services like Qdrant/MinIO)
try:
    from app.api.v1.endpoints import sessions, materials, uploads

    api_router.include_router(sessions.router)
    api_router.include_router(materials.router)
    api_router.include_router(uploads.router)
except Exception:
    # Swallow import errors to allow app import in test environments
    pass
