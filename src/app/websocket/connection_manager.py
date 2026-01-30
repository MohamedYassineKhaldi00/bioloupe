from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and presence tracking."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._presence_ttl = 60

    def _sid_key(self, sid: str) -> str:
        return f"ws:sid:{sid}"

    def _user_session_key(self, user_id: str, session_id: str) -> str:
        return f"ws:user:{user_id}:session:{session_id}"

    def _session_participants_key(self, session_id: str) -> str:
        return f"ws:session:{session_id}:participants"

    def _presence_key(self, session_id: str, user_id: str) -> str:
        return f"ws:presence:{session_id}:{user_id}"

    async def connect_user(
        self,
        sid: str,
        user_id: str,
        session_id: str,
        full_name: str
    ) -> None:
        """Register user connection."""
        connection_data = {
            "user_id": user_id,
            "session_id": session_id,
            "full_name": full_name,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        await self.redis.setex(
            self._sid_key(sid),
            self._presence_ttl * 2,
            json.dumps(connection_data)
        )

        await self.redis.setex(
            self._user_session_key(user_id, session_id),
            self._presence_ttl * 2,
            sid
        )

        await self.redis.sadd(
            self._session_participants_key(session_id),
            sid
        )

        await self._update_presence(session_id, user_id, full_name, "online")

        logger.info(
            f"User connected: sid={sid}, user_id={user_id}, session_id={session_id}"
        )

    async def disconnect_user(self, sid: str) -> dict[str, Any] | None:
        """Remove user connection and return connection data."""
        data_json = await self.redis.get(self._sid_key(sid))
        if not data_json:
            return None

        data = json.loads(data_json)
        user_id = data["user_id"]
        session_id = data["session_id"]

        await self.redis.delete(self._sid_key(sid))
        await self.redis.delete(
            self._user_session_key(user_id, session_id)
        )
        await self.redis.srem(
            self._session_participants_key(session_id),
            sid
        )
        await self.redis.delete(
            self._presence_key(session_id, user_id)
        )

        logger.info(
            f"User disconnected: sid={sid}, user_id={user_id}, session_id={session_id}"
        )

        return data

    async def get_session_participants(
        self,
        session_id: str
    ) -> list[dict[str, Any]]:
        """Get all participants in a session."""
        sids = await self.redis.smembers(
            self._session_participants_key(session_id)
        )

        participants = []
        for sid in sids:
            data_json = await self.redis.get(self._sid_key(sid))
            if data_json:
                data = json.loads(data_json)
                presence = await self._get_presence(
                    session_id,
                    data["user_id"]
                )
                participants.append({
                    "sid": sid,
                    "user_id": data["user_id"],
                    "full_name": data["full_name"],
                    "connected_at": data["connected_at"],
                    "status": presence.get("status", "online"),
                    "last_seen": presence.get("last_seen"),
                })

        return participants

    async def is_user_in_session(
        self,
        user_id: str,
        session_id: str
    ) -> bool:
        """Check if user is connected to session."""
        sid = await self.redis.get(
            self._user_session_key(user_id, session_id)
        )
        return sid is not None

    async def get_connection_data(self, sid: str) -> dict[str, Any] | None:
        """Get connection data for a session ID."""
        data_json = await self.redis.get(self._sid_key(sid))
        if not data_json:
            return None
        return json.loads(data_json)

    async def refresh_presence(
        self,
        session_id: str,
        user_id: str,
        full_name: str
    ) -> None:
        """Refresh user presence TTL."""
        await self._update_presence(
            session_id,
            user_id,
            full_name,
            "online"
        )

    async def _update_presence(
        self,
        session_id: str,
        user_id: str,
        full_name: str,
        status: str
    ) -> None:
        """Update presence data in Redis."""
        presence_data = {
            "user_id": user_id,
            "full_name": full_name,
            "status": status,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }

        await self.redis.setex(
            self._presence_key(session_id, user_id),
            self._presence_ttl,
            json.dumps(presence_data)
        )

    async def _get_presence(
        self,
        session_id: str,
        user_id: str
    ) -> dict[str, Any]:
        """Get presence data from Redis."""
        data_json = await self.redis.get(
            self._presence_key(session_id, user_id)
        )
        if not data_json:
            return {
                "status": "offline",
                "last_seen": datetime.now(timezone.utc).isoformat()
            }
        return json.loads(data_json)
