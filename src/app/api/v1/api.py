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
    pass

# Embeddings endpoint (optional)
try:
    from app.api.v1.endpoints import embeddings
    api_router.include_router(embeddings.router, tags=["embeddings"])
except Exception:
    pass

try:
    from app.api.v1.endpoints import performance

    api_router.include_router(performance.router)
except Exception:
    pass

try:
    from app.search.routers import (
        global_search_router,
        publication_search_router,
        similarity_router,
    )

    api_router.include_router(global_search_router)
    api_router.include_router(publication_search_router)
    api_router.include_router(similarity_router)
except Exception:
    pass
