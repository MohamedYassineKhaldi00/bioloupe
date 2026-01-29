"""
Tests for WebSocket infrastructure.
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from socketio import AsyncClient

from app.schemas.websocket_schemas import (
    CursorPositionEvent,
    HeartbeatEvent,
    JoinSessionEvent,
)
from app.websocket.auth_middleware import authenticate_websocket
from app.websocket.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test ConnectionManager functionality."""

    @pytest.fixture
    def redis_mock(self):
        mock = AsyncMock()
        mock.setex = AsyncMock()
        mock.get = AsyncMock()
        mock.delete = AsyncMock()
        mock.sadd = AsyncMock()
        mock.srem = AsyncMock()
        mock.smembers = AsyncMock()
        return mock

    @pytest.fixture
    def manager(self, redis_mock):
        return ConnectionManager(redis_mock)

    async def test_connect_user(self, manager, redis_mock):
        """Test user connection tracking."""
        sid = "test-sid"
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        full_name = "Test User"

        await manager.connect_user(sid, user_id, session_id, full_name)

        assert redis_mock.setex.call_count == 3
        assert redis_mock.sadd.call_count == 1

    async def test_disconnect_user(self, manager, redis_mock):
        """Test user disconnection cleanup."""
        sid = "test-sid"
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        conn_data = {
            "user_id": user_id,
            "session_id": session_id,
            "full_name": "Test User",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        redis_mock.get.return_value = json.dumps(conn_data)

        result = await manager.disconnect_user(sid)

        assert result == conn_data
        assert redis_mock.delete.call_count == 3
        assert redis_mock.srem.call_count == 1

    async def test_get_session_participants(self, manager, redis_mock):
        """Test retrieving session participants."""
        session_id = str(uuid.uuid4())
        sid1 = "sid-1"
        sid2 = "sid-2"

        redis_mock.smembers.return_value = {sid1, sid2}

        conn_data_1 = {
            "user_id": str(uuid.uuid4()),
            "session_id": session_id,
            "full_name": "User 1",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        presence_data_1 = {
            "status": "online",
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }

        redis_mock.get.side_effect = [
            json.dumps(conn_data_1),
            json.dumps(presence_data_1),
            None,
        ]

        participants = await manager.get_session_participants(session_id)

        assert len(participants) == 1
        assert participants[0]["user_id"] == conn_data_1["user_id"]
        assert participants[0]["status"] == "online"


class TestWebSocketSchemas:
    """Test WebSocket event schemas."""

    def test_join_session_event(self):
        """Test JoinSessionEvent validation."""
        session_id = uuid.uuid4()
        event = JoinSessionEvent(session_id=session_id)

        assert event.session_id == session_id

    def test_cursor_position_event(self):
        """Test CursorPositionEvent validation."""
        event = CursorPositionEvent(
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            x=100.5,
            y=200.3,
            element_id="canvas-1"
        )

        assert event.x == 100.5
        assert event.y == 200.3
        assert event.element_id == "canvas-1"

    def test_heartbeat_event(self):
        """Test HeartbeatEvent validation."""
        now = datetime.now(timezone.utc)
        event = HeartbeatEvent(timestamp=now)

        assert event.timestamp == now


class TestAuthMiddleware:
    """Test WebSocket authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_no_token(self):
        """Test auth fails without token."""
        with pytest.raises(ConnectionRefusedError) as exc:
            await authenticate_websocket({})

        assert "token required" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self):
        """Test auth fails with invalid token."""
        with pytest.raises(ConnectionRefusedError) as exc:
            await authenticate_websocket({"token": "invalid"})

        assert "invalid" in str(exc.value).lower()


class TestWebSocketIntegration:
    """Integration tests for WebSocket server."""

    @pytest.mark.asyncio
    async def test_connect_without_auth(self):
        """Test connection fails without auth."""
        # This would require running test server
        # Placeholder for integration test
        pass

    @pytest.mark.asyncio
    async def test_join_session_flow(self):
        """Test complete join session flow."""
        # This would require running test server
        # Placeholder for integration test
        pass
