from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class PresenceService:
    """Manages user presence and cursor positions."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._presence_ttl = 60
        self._cursor_ttl = 5

    def _presence_key(self, session_id: str, user_id: str) -> str:
        return f"presence:{session_id}:{user_id}"

    def _cursor_key(self, session_id: str, user_id: str) -> str:
        return f"cursor:{session_id}:{user_id}"

    def _selection_key(self, session_id: str, user_id: str) -> str:
        return f"selection:{session_id}:{user_id}"

    async def update_presence(
        self,
        user_id: str,
        session_id: str,
        status: str = "online",
        full_name: str | None = None
    ) -> None:
        """Update user presence in session."""
        presence_data = {
            "user_id": user_id,
            "status": status,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
        }
        if full_name:
            presence_data["full_name"] = full_name

        key = self._presence_key(session_id, user_id)
        await self.redis.setex(
            key,
            self._presence_ttl,
            json.dumps(presence_data)
        )

        logger.debug(
            f"Presence updated: user={user_id}, session={session_id}, status={status}"
        )

    async def get_session_presence(
        self,
        session_id: str
    ) -> list[dict[str, Any]]:
        """Get all users currently in session."""
        pattern = f"presence:{session_id}:*"
        presence_list = []

        async for key in self.redis.scan_iter(match=pattern):
            data_json = await self.redis.get(key)
            if data_json:
                try:
                    presence_list.append(json.loads(data_json))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in presence key: {key}")

        return presence_list

    async def remove_presence(
        self,
        session_id: str,
        user_id: str
    ) -> None:
        """Remove user presence from session."""
        key = self._presence_key(session_id, user_id)
        await self.redis.delete(key)

        logger.debug(
            f"Presence removed: user={user_id}, session={session_id}"
        )

    async def update_cursor_position(
        self,
        user_id: str,
        session_id: str,
        x: float,
        y: float,
        element_id: str | None = None
    ) -> None:
        """Update cursor position (ephemeral)."""
        cursor_data = {
            "x": x,
            "y": y,
            "element_id": element_id,
            "timestamp": datetime.now(timezone.utc).timestamp(),
        }

        key = self._cursor_key(session_id, user_id)
        await self.redis.setex(
            key,
            self._cursor_ttl,
            json.dumps(cursor_data)
        )

    async def get_session_cursors(
        self,
        session_id: str
    ) -> dict[str, dict[str, Any]]:
        """Get all cursor positions for session."""
        pattern = f"cursor:{session_id}:*"
        cursors = {}

        async for key in self.redis.scan_iter(match=pattern):
            user_id = key.decode().split(":")[-1]
            data_json = await self.redis.get(key)
            if data_json:
                try:
                    cursors[user_id] = json.loads(data_json)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in cursor key: {key}")

        return cursors

    async def update_selection(
        self,
        user_id: str,
        session_id: str,
        selected_ids: list[str]
    ) -> None:
        """Update user's selected elements."""
        selection_data = {
            "selected_ids": selected_ids,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        key = self._selection_key(session_id, user_id)
        await self.redis.setex(
            key,
            10,
            json.dumps(selection_data)
        )

    async def get_session_selections(
        self,
        session_id: str
    ) -> dict[str, list[str]]:
        """Get all selections for session."""
        pattern = f"selection:{session_id}:*"
        selections = {}

        async for key in self.redis.scan_iter(match=pattern):
            user_id = key.decode().split(":")[-1]
            data_json = await self.redis.get(key)
            if data_json:
                try:
                    data = json.loads(data_json)
                    selections[user_id] = data["selected_ids"]
                except (json.JSONDecodeError, KeyError):
                    logger.warning(f"Invalid JSON in selection key: {key}")

        return selections

    async def cleanup_stale_presence(
        self,
        max_age_seconds: int = 60
    ) -> int:
        """Clean up stale presence entries."""
        removed_count = 0
        pattern = "presence:*"

        async for key in self.redis.scan_iter(match=pattern):
            ttl = await self.redis.ttl(key)
            if ttl == -1 or ttl == -2:
                await self.redis.delete(key)
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} stale presence entries")

        return removed_count
