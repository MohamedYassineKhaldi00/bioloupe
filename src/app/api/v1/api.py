from __future__ import annotations

from fastapi import APIRouter

# Import the core endpoints first. Optional endpoints that rely on extra
# external packages are imported inside a try/except so tests can run without
# requiring those dependencies to be installed.
from app.api.v1.endpoints import users, teams

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(teams.router)

# Optional endpoints (may require optional third-party packages) — include if available
try:
    from app.api.v1.endpoints import sessions, materials, uploads

    api_router.include_router(sessions.router)
    api_router.include_router(materials.router)
    api_router.include_router(uploads.router)
except Exception:
    # Swallow import errors here to allow the app to be imported in test
    # environments where optional services (Qdrant, MinIO, etc.) are not present.
    pass
