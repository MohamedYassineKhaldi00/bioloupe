from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import socketio
from pydantic import ValidationError

from ...schemas.presence_schemas import (
    CursorPosition,
    HeartbeatRequest,
    HeartbeatResponse,
)
from ..services.presence_service import PresenceService
from ..services.sync_service import SyncService

logger = logging.getLogger(__name__)


class PresenceHandlers:
    """Handles presence-related WebSocket events."""

    def __init__(
        self,
        sio: socketio.AsyncServer,
        presence_service: PresenceService,
        sync_service: SyncService
    ):
        self.sio = sio
        self.presence = presence_service
        self.sync = sync_service

    async def get_user_from_session(
        self,
        sid: str
    ) -> dict[str, Any] | None:
        """Get user data from socket session."""
        session_data = await self.sio.get_session(sid)
        if not session_data or not session_data.get("authenticated"):
            return None
        return session_data

    async def handle_join_session(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle user joining a session room."""
        try:
            session_id = str(data["session_id"])
            user_data = await self.get_user_from_session(sid)

            if not user_data:
                logger.warning(
                    f"Unauthenticated join attempt: sid={sid}"
                )
                return {
                    "success": False,
                    "error": "Not authenticated"
                }

            user_id = user_data["user_id"]
            full_name = user_data.get("full_name", "Unknown")

            await self.sio.enter_room(sid, f"session:{session_id}")

            await self.presence.update_presence(
                user_id,
                session_id,
                "online",
                full_name
            )

            participants = await self.presence.get_session_presence(
                session_id
            )
            cursors = await self.presence.get_session_cursors(
                session_id
            )

            await self.sio.emit(
                "user_joined",
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "full_name": full_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                room=f"session:{session_id}",
                skip_sid=sid
            )

            await self.sio.emit(
                "session_state",
                {
                    "session_id": session_id,
                    "participants": participants,
                    "cursors": cursors,
                },
                room=sid
            )

            logger.info(
                f"User joined: sid={sid}, user={user_id}, session={session_id}"
            )

            return {
                "success": True,
                "participants": participants,
                "cursors": cursors,
            }

        except KeyError as e:
            logger.warning(f"Missing field in join_session: {e}")
            return {"success": False, "error": f"Missing field: {e}"}
        except Exception as e:
            logger.error(
                f"Join session error: {e}",
                exc_info=True
            )
            return {"success": False, "error": "Internal error"}

    async def handle_leave_session(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle user leaving a session room."""
        try:
            session_id = str(data["session_id"])
            user_data = await self.get_user_from_session(sid)

            if not user_data:
                return {"success": False, "error": "Not authenticated"}

            user_id = user_data["user_id"]

            await self.sio.leave_room(sid, f"session:{session_id}")

            await self.presence.update_presence(
                user_id,
                session_id,
                "offline"
            )

            await self.sio.emit(
                "user_left",
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                room=f"session:{session_id}"
            )

            logger.info(
                f"User left: sid={sid}, user={user_id}, session={session_id}"
            )

            return {"success": True}

        except KeyError as e:
            logger.warning(f"Missing field in leave_session: {e}")
            return {"success": False, "error": f"Missing field: {e}"}
        except Exception as e:
            logger.error(f"Leave session error: {e}", exc_info=True)
            return {"success": False, "error": "Internal error"}

    async def handle_cursor_move(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Handle cursor position updates with throttling."""
        try:
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                return

            user_id = user_data["user_id"]

            if not self.sync.can_emit_cursor(user_id):
                return

            event = CursorPosition(**data)
            session_id = str(event.session_id)

            await self.presence.update_cursor_position(
                user_id,
                session_id,
                event.x,
                event.y,
                event.element_id
            )

            await self.sio.emit(
                "cursor_update",
                {
                    "user_id": user_id,
                    "x": event.x,
                    "y": event.y,
                    "element_id": event.element_id,
                },
                room=f"session:{session_id}",
                skip_sid=sid
            )

        except ValidationError as e:
            logger.warning(f"Invalid cursor data: {e}")
        except Exception as e:
            logger.error(f"Cursor move error: {e}", exc_info=True)

    async def handle_heartbeat(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Handle client heartbeat."""
        try:
            heartbeat = HeartbeatRequest(**data)
            user_data = await self.get_user_from_session(sid)

            if user_data and heartbeat.session_id:
                session_id = str(heartbeat.session_id)
                user_id = user_data["user_id"]
                full_name = user_data.get("full_name")

                await self.presence.update_presence(
                    user_id,
                    session_id,
                    "online",
                    full_name
                )

            response = HeartbeatResponse(
                timestamp=datetime.now(timezone.utc)
            )

            await self.sio.emit(
                "heartbeat_ack",
                response.model_dump(mode="json"),
                room=sid
            )

        except ValidationError as e:
            logger.warning(f"Invalid heartbeat data: {e}")
        except Exception as e:
            logger.error(f"Heartbeat error: {e}", exc_info=True)
