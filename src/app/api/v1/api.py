from __future__ import annotations

from fastapi import APIRouter
from app.core.config import get_settings

api_router = APIRouter()
settings = get_settings()

# Core endpoints - always enabled
from app.api.v1.endpoints import users
api_router.include_router(users.router, tags=["users"])

# Authentication endpoints
try:
    from app.api.v1.endpoints import health, auth, oauth
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(auth.router, prefix="/auth", tags=["auth"]) 
    api_router.include_router(oauth.router, tags=["oauth"])
except Exception as e:
    print(f"Auth endpoints failed to load: {e}")

# Research endpoints
try:
    from app.api.v1.endpoints import teams, sessions, materials
    api_router.include_router(teams.router, tags=["teams"])
    api_router.include_router(sessions.router, tags=["sessions"])
    api_router.include_router(materials.router, tags=["materials"])
except Exception as e:
    print(f"Research endpoints failed to load: {e}")

# Data endpoints
try:
    from app.api.v1.endpoints import variants
    api_router.include_router(variants.router, tags=["variants"])
except Exception as e:
    print(f"Variants endpoint failed to load: {e}")

# Admin endpoints
try:
    from app.api.v1.endpoints import audit
    api_router.include_router(audit.router, prefix="/admin", tags=["audit"])
except Exception as e:
    print(f"Admin endpoints failed to load: {e}")

# Performance monitoring
try:
    from app.api.v1.endpoints import performance
    api_router.include_router(performance.router, tags=["performance"])
except Exception as e:
    print(f"Performance endpoint failed to load: {e}")

# Upload endpoint
if not settings.disable_minio:
    try:
        from app.api.v1.endpoints import uploads
        api_router.include_router(uploads.router, tags=["uploads"])
    except Exception as e:
        print(f"Upload endpoint failed to load: {e}")

# Embedding endpoint
if not settings.disable_embeddings:
    try:
        from app.api.v1.endpoints import embeddings
        api_router.include_router(embeddings.router, tags=["embeddings"])
    except Exception as e:
        print(f"Embeddings endpoint failed to load: {e}")

# Search endpoints
if not settings.disable_vector_search:
    try:
        from app.search.routers import (
            global_search_router,
            publication_search_router,
            similarity_router,
        )
        api_router.include_router(global_search_router, tags=["search"])
        api_router.include_router(publication_search_router, tags=["search"])
        api_router.include_router(similarity_router, tags=["search"])
    except Exception as e:
        print(f"Search endpoints failed to load: {e}")

# AI/Hypothesis generation endpoint - temporarily disabled due to LiteLLM compatibility
# try:
#     from app.api.v1.endpoints import hypotheses
#     api_router.include_router(hypotheses.router, tags=["hypotheses"])
# except Exception as e:
#     print(f"Hypotheses endpoint failed to load: {e}")
