from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exceptions import InvitationExpired, InvitationInvalid
from app.db.redis_client import get_redis
from app.models import TeamRole


@dataclass(frozen=True)
class InvitationPayload:
    team_id: str
    email: str
    role: TeamRole
    invited_by: str


class InvitationService:
    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis or get_redis()
        self._settings = get_settings()

    async def create_invitation(self, payload: InvitationPayload) -> str:
        token = secrets.token_urlsafe(32)
        key = f"team_invite:{token}"
        ttl = self._settings.invitation_token_ttl_hours * 3600
        await self._redis.set(key, json.dumps(payload.__dict__), ex=ttl)
        return token

    async def consume_invitation(self, token: str) -> InvitationPayload:
        key = f"team_invite:{token}"
        data = await self._redis.get(key)
        if not data:
            raise InvitationExpired()
        await self._redis.delete(key)
        try:
            payload = json.loads(data)
            return InvitationPayload(
                team_id=payload["team_id"],
                email=payload["email"],
                role=TeamRole(payload["role"]),
                invited_by=payload["invited_by"],
            )
        except Exception as exc:
            raise InvitationInvalid() from exc
