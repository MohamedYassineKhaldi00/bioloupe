from __future__ import annotations

import logging
import uuid
from typing import Any

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import decode_token
from ..db.base import async_session_maker
from ..models.user import User

logger = logging.getLogger(__name__)


async def authenticate_websocket(
    auth_data: dict[str, Any]
) -> tuple[str, User]:
    """
    Authenticate WebSocket connection using JWT token.

    Returns:
        tuple: (user_id_str, user_object)

    Raises:
        ConnectionRefusedError: If authentication fails
    """
    token = auth_data.get("token")
    if not token:
        logger.warning("WebSocket auth failed: No token")
        raise ConnectionRefusedError("Authentication token required")

    try:
        payload = decode_token(token)
    except JWTError as e:
        logger.warning(f"WebSocket auth failed: Invalid token - {e}")
        raise ConnectionRefusedError("Invalid authentication token")

    token_type = payload.get("type")
    if token_type != "access":
        logger.warning(f"WebSocket auth failed: Wrong token type {token_type}")
        raise ConnectionRefusedError("Invalid token type")

    user_id_str = payload.get("sub")
    if not user_id_str:
        logger.warning("WebSocket auth failed: No subject in token")
        raise ConnectionRefusedError("Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        logger.warning(f"WebSocket auth failed: Invalid UUID {user_id_str}")
        raise ConnectionRefusedError("Invalid user ID")

    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"WebSocket auth failed: User not found {user_id}")
            raise ConnectionRefusedError("User not found")

        if not user.is_active:
            logger.warning(f"WebSocket auth failed: User inactive {user_id}")
            raise ConnectionRefusedError("User is not active")

    logger.info(f"WebSocket authenticated: user_id={user_id}")
    return user_id_str, user


async def verify_session_access(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID
) -> bool:
    """Verify that user has access to the session."""
    from ..models.session import SessionParticipant

    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == user_id
        )
    )
    participant = result.scalar_one_or_none()
    return participant is not None
