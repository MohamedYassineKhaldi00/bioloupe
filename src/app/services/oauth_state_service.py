from __future__ import annotations

import secrets
from ...app.db.redis_client import get_redis


STATE_TTL_SECONDS = 600


async def generate_oauth_state() -> str:
    state = secrets.token_urlsafe(32)
    redis = get_redis()
    key = f"oauth:state:{state}"
    await redis.set(key, "1", ex=STATE_TTL_SECONDS)
    return state


async def validate_oauth_state(state: str) -> bool:
    redis = get_redis()
    key = f"oauth:state:{state}"
    result = await redis.get(key)
    if result:
        await redis.delete(key)
        return True
    return False
