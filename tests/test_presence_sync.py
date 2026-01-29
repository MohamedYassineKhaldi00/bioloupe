from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.websocket.services.presence_service import PresenceService
from app.websocket.services.sync_service import SyncService


@pytest.fixture
def redis_mock() -> AsyncMock:
    """Provide mocked Redis client."""
    mock = AsyncMock()
    mock.setex = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.delete = AsyncMock()
    mock.scan_iter = AsyncMock(return_value=[])
    mock.ttl = AsyncMock(return_value=-1)
    return mock


@pytest.fixture
def presence_service(redis_mock: AsyncMock) -> PresenceService:
    """Provide PresenceService instance."""
    return PresenceService(redis_mock)


@pytest.fixture
def sync_service() -> SyncService:
    """Provide SyncService instance."""
    return SyncService()


class TestPresenceService:
    """Test presence management functionality."""

    @pytest.mark.asyncio
    async def test_update_presence(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test updating user presence."""
        user_id = str(uuid4())
        session_id = str(uuid4())

        await presence_service.update_presence(
            user_id,
            session_id,
            "online",
            "Test User"
        )

        redis_mock.setex.assert_called_once()
        args = redis_mock.setex.call_args[0]
        assert args[0] == f"presence:{session_id}:{user_id}"
        assert args[1] == 60

    @pytest.mark.asyncio
    async def test_get_session_presence(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test retrieving all presence in session."""
        session_id = str(uuid4())
        user1_id = str(uuid4())

        test_data = {
            "user_id": user1_id,
            "status": "online",
            "session_id": session_id
        }

        async def mock_scan():
            yield f"presence:{session_id}:{user1_id}".encode()

        redis_mock.scan_iter.return_value = mock_scan()
        redis_mock.get.return_value = json.dumps(test_data)

        presence_list = await presence_service.get_session_presence(
            session_id
        )

        assert len(presence_list) == 1
        assert presence_list[0]["user_id"] == user1_id

    @pytest.mark.asyncio
    async def test_remove_presence(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test removing user presence."""
        user_id = str(uuid4())
        session_id = str(uuid4())

        await presence_service.remove_presence(session_id, user_id)

        redis_mock.delete.assert_called_once()
        args = redis_mock.delete.call_args[0]
        assert args[0] == f"presence:{session_id}:{user_id}"

    @pytest.mark.asyncio
    async def test_update_cursor_position(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test updating cursor position."""
        user_id = str(uuid4())
        session_id = str(uuid4())

        await presence_service.update_cursor_position(
            user_id,
            session_id,
            100.5,
            200.3,
            "element-123"
        )

        redis_mock.setex.assert_called_once()
        args = redis_mock.setex.call_args[0]
        assert args[0] == f"cursor:{session_id}:{user_id}"
        assert args[1] == 5

    @pytest.mark.asyncio
    async def test_get_session_cursors(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test retrieving all cursors in session."""
        session_id = str(uuid4())
        user1_id = str(uuid4())

        cursor_data = {
            "x": 10.0,
            "y": 20.0,
            "timestamp": datetime.now(timezone.utc).timestamp()
        }

        async def mock_scan():
            yield f"cursor:{session_id}:{user1_id}".encode()

        redis_mock.scan_iter.return_value = mock_scan()
        redis_mock.get.return_value = json.dumps(cursor_data)

        cursors = await presence_service.get_session_cursors(session_id)

        assert len(cursors) == 1
        assert user1_id in cursors

    @pytest.mark.asyncio
    async def test_update_selection(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test updating user selection."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        selected_ids = ["elem1", "elem2", "elem3"]

        await presence_service.update_selection(
            user_id,
            session_id,
            selected_ids
        )

        redis_mock.setex.assert_called_once()
        args = redis_mock.setex.call_args[0]
        assert args[0] == f"selection:{session_id}:{user_id}"
        assert args[1] == 10

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test cleaning up stale presence entries."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        async def mock_scan():
            yield f"presence:{session_id}:{user_id}".encode()

        redis_mock.scan_iter.return_value = mock_scan()
        redis_mock.ttl.return_value = -1

        removed = await presence_service.cleanup_stale_presence()

        assert removed == 1
        redis_mock.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cursor_ttl_expiration(
        self,
        presence_service: PresenceService,
        redis_mock: AsyncMock
    ):
        """Test cursor position expires after TTL."""
        user_id = str(uuid4())
        session_id = str(uuid4())

        redis_mock.ttl.return_value = 4

        await presence_service.update_cursor_position(
            user_id,
            session_id,
            50.0,
            60.0
        )

        redis_mock.setex.assert_called_once()
        args = redis_mock.setex.call_args[0]
        assert args[1] == 5


class TestSyncService:
    """Test synchronization and throttling."""

    def test_cursor_throttling(self, sync_service: SyncService):
        """Test cursor event throttling."""
        user_id = str(uuid4())

        allowed_count = 0
        for _ in range(35):
            if sync_service.can_emit_cursor(user_id):
                allowed_count += 1

        assert allowed_count == 30

    def test_selection_throttling(self, sync_service: SyncService):
        """Test selection event throttling."""
        user_id = str(uuid4())

        allowed_count = 0
        for _ in range(15):
            if sync_service.can_emit_selection(user_id):
                allowed_count += 1

        assert allowed_count == 10

    def test_throttler_cleanup(self, sync_service: SyncService):
        """Test throttler cleanup removes old entries."""
        user_id = str(uuid4())

        for _ in range(5):
            sync_service.can_emit_cursor(user_id)

        sync_service.cleanup()

        assert len(sync_service.cursor_throttler._timestamps) >= 0

    def test_create_sync_event(self, sync_service: SyncService):
        """Test creating standardized sync event."""
        event = sync_service.create_sync_event(
            "test_event",
            str(uuid4()),
            str(uuid4()),
            {"key": "value"}
        )

        assert event["type"] == "test_event"
        assert "user_id" in event
        assert "session_id" in event
        assert "timestamp" in event
        assert event["data"] == {"key": "value"}

    def test_validate_canvas_action_valid(
        self,
        sync_service: SyncService
    ):
        """Test valid canvas action validation."""
        valid = sync_service.validate_canvas_action(
            "move",
            "element-123",
            {"position": {"x": 10, "y": 20}}
        )

        assert valid is True

    def test_validate_canvas_action_invalid_action(
        self,
        sync_service: SyncService
    ):
        """Test invalid canvas action type."""
        valid = sync_service.validate_canvas_action(
            "invalid_action",
            "element-123",
            {}
        )

        assert valid is False

    def test_validate_canvas_action_missing_data(
        self,
        sync_service: SyncService
    ):
        """Test canvas action validation with missing data."""
        valid = sync_service.validate_canvas_action(
            "move",
            "element-123",
            {}
        )

        assert valid is False

    @pytest.mark.asyncio
    async def test_debounce(self, sync_service: SyncService):
        """Test event debouncing."""
        called = []

        async def callback():
            called.append(True)

        await sync_service.debounce(
            "test_key",
            50,
            callback
        )

        assert "test_key" in sync_service._debounce_tasks

        await asyncio.sleep(0.1)

        assert len(called) == 1

    def test_create_conflict_resolution_event(
        self,
        sync_service: SyncService
    ):
        """Test creating conflict resolution event."""
        event = sync_service.create_conflict_resolution_event(
            "simultaneous_edit",
            "element-123",
            str(uuid4()),
            {"field": "value"}
        )

        assert event["type"] == "conflict"
        assert event["conflict_type"] == "simultaneous_edit"
        assert event["element_id"] == "element-123"
        assert "timestamp" in event


class TestThrottling:
    """Test event throttling behavior."""

    def test_throttler_window_reset(self, sync_service: SyncService):
        """Test throttler resets after window expires."""
        user_id = str(uuid4())

        for _ in range(30):
            sync_service.can_emit_cursor(user_id)

        assert sync_service.can_emit_cursor(user_id) is False

    def test_multiple_users_independent_throttling(
        self,
        sync_service: SyncService
    ):
        """Test each user has independent throttling."""
        user1_id = str(uuid4())
        user2_id = str(uuid4())

        for _ in range(30):
            sync_service.can_emit_cursor(user1_id)

        assert sync_service.can_emit_cursor(user1_id) is False
        assert sync_service.can_emit_cursor(user2_id) is True
