from __future__ import annotations

import uuid
from typing import Optional

from ..services.cache_service import CacheService


class PermissionCacheManager:
    def __init__(self, cache_service: CacheService) -> None:
        self._cache = cache_service

    async def invalidate_team_membership(
        self, team_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> None:
        if user_id:
            await self._cache.delete(f"team_role:{team_id}:{user_id}")
        else:
            await self._cache.invalidate_prefix(f"team_role:{team_id}:")

    async def invalidate_session_permission(
        self, session_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> None:
        if user_id:
            await self._cache.delete(f"session_permission:{session_id}:{user_id}")
        else:
            await self._cache.invalidate_prefix(
                f"session_permission:{session_id}:"
            )

    async def invalidate_all_team_sessions(
        self, team_id: uuid.UUID
    ) -> None:
        await self._cache.invalidate_prefix(f"team_role:{team_id}:")

    async def invalidate_user_permissions(
        self, user_id: uuid.UUID
    ) -> None:
        await self._cache.invalidate_prefix("team_role:")
        await self._cache.invalidate_prefix("session_permission:")
