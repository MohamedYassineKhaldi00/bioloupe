from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock

from src.app.services.permission_cache_manager import PermissionCacheManager
from src.app.services.cache_service import CacheService


@pytest.fixture
def mock_cache_service() -> AsyncMock:
    return AsyncMock(spec=CacheService)


@pytest.fixture
def cache_manager(mock_cache_service: AsyncMock) -> PermissionCacheManager:
    return PermissionCacheManager(mock_cache_service)


class TestPermissionCacheManager:
    @pytest.mark.asyncio
    async def test_invalidate_team_membership_specific_user(
        self, cache_manager: PermissionCacheManager,
        mock_cache_service: AsyncMock
    ) -> None:
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await cache_manager.invalidate_team_membership(team_id, user_id)

        mock_cache_service.delete.assert_called_once_with(
            f"team_role:{team_id}:{user_id}"
        )

    @pytest.mark.asyncio
    async def test_invalidate_team_membership_all_users(
        self, cache_manager: PermissionCacheManager,
        mock_cache_service: AsyncMock
    ) -> None:
        team_id = uuid.uuid4()

        await cache_manager.invalidate_team_membership(team_id)

        mock_cache_service.invalidate_prefix.assert_called_once_with(
            f"team_role:{team_id}:"
        )

    @pytest.mark.asyncio
    async def test_invalidate_session_permission_specific_user(
        self, cache_manager: PermissionCacheManager,
        mock_cache_service: AsyncMock
    ) -> None:
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await cache_manager.invalidate_session_permission(session_id, user_id)

        mock_cache_service.delete.assert_called_once_with(
            f"session_permission:{session_id}:{user_id}"
        )

    @pytest.mark.asyncio
    async def test_invalidate_session_permission_all_users(
        self, cache_manager: PermissionCacheManager,
        mock_cache_service: AsyncMock
    ) -> None:
        session_id = uuid.uuid4()

        await cache_manager.invalidate_session_permission(session_id)

        mock_cache_service.invalidate_prefix.assert_called_once_with(
            f"session_permission:{session_id}:"
        )

    @pytest.mark.asyncio
    async def test_invalidate_all_team_sessions(
        self, cache_manager: PermissionCacheManager,
        mock_cache_service: AsyncMock
    ) -> None:
        team_id = uuid.uuid4()

        await cache_manager.invalidate_all_team_sessions(team_id)

        mock_cache_service.invalidate_prefix.assert_called_once_with(
            f"team_role:{team_id}:"
        )

    @pytest.mark.asyncio
    async def test_invalidate_user_permissions(
        self, cache_manager: PermissionCacheManager,
        mock_cache_service: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()

        await cache_manager.invalidate_user_permissions(user_id)

        assert mock_cache_service.invalidate_prefix.call_count == 2
        calls = mock_cache_service.invalidate_prefix.call_args_list
        assert calls[0][0][0] == "team_role:"
        assert calls[1][0][0] == "session_permission:"
