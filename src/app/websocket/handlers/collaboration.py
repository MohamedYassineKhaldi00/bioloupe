from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import socketio
from pydantic import ValidationError

from ...schemas.presence_schemas import (
    CanvasAction,
    MaterialUpdate,
    SelectionUpdate,
)
from ..services.presence_service import PresenceService
from ..services.sync_service import SyncService

logger = logging.getLogger(__name__)


class CollaborationHandlers:
    """Handles collaboration event broadcasting."""

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

    async def handle_material_added(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast material addition to session."""
        try:
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                return

            user_id = user_data["user_id"]
            session_id = str(data["session_id"])

            await self.sio.emit(
                "material_added",
                {
                    "session_id": session_id,
                    "material_id": str(data["material_id"]),
                    "material_data": data.get("material_data", {}),
                    "added_by": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                room=f"session:{session_id}"
            )

            logger.info(
                f"Material added: user={user_id}, "
                f"material={data['material_id']}, session={session_id}"
            )

        except KeyError as e:
            logger.warning(f"Missing field in material_added: {e}")
        except Exception as e:
            logger.error(f"Material added error: {e}", exc_info=True)

    async def handle_material_updated(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast material updates."""
        try:
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                return

            user_id = user_data["user_id"]
            event = MaterialUpdate(**data)
            session_id = str(event.session_id)

            await self.sio.emit(
                "material_updated",
                {
                    "session_id": session_id,
                    "material_id": str(event.material_id),
                    "changes": event.changes,
                    "updated_by": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                room=f"session:{session_id}",
                skip_sid=sid
            )

            logger.info(
                f"Material updated: user={user_id}, "
                f"material={event.material_id}, session={session_id}"
            )

        except ValidationError as e:
            logger.warning(f"Invalid material_updated data: {e}")
        except Exception as e:
            logger.error(f"Material updated error: {e}", exc_info=True)

    async def handle_selection_change(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast selection changes with throttling."""
        try:
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                return

            user_id = user_data["user_id"]

            if not self.sync.can_emit_selection(user_id):
                return

            event = SelectionUpdate(**data)
            session_id = str(event.session_id)

            await self.presence.update_selection(
                user_id,
                session_id,
                event.selected_ids
            )

            await self.sio.emit(
                "selection_update",
                {
                    "user_id": user_id,
                    "selected_ids": event.selected_ids,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                room=f"session:{session_id}",
                skip_sid=sid
            )

        except ValidationError as e:
            logger.warning(f"Invalid selection data: {e}")
        except Exception as e:
            logger.error(f"Selection change error: {e}", exc_info=True)

    async def handle_canvas_action(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Synchronize canvas actions."""
        try:
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                return

            user_id = user_data["user_id"]
            event = CanvasAction(**data)
            session_id = str(event.session_id)

            if not self.sync.validate_canvas_action(
                event.action,
                event.element_id,
                {
                    "position": event.position,
                    "size": event.size,
                    "data": event.data,
                }
            ):
                logger.warning(
                    f"Invalid canvas action: {event.action}, "
                    f"element={event.element_id}"
                )
                return

            action_data = {
                "user_id": user_id,
                "action": event.action,
                "element_id": event.element_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if event.position:
                action_data["position"] = event.position
            if event.size:
                action_data["size"] = event.size
            if event.data:
                action_data["data"] = event.data

            await self.sio.emit(
                "canvas_update",
                action_data,
                room=f"session:{session_id}",
                skip_sid=sid
            )

            logger.info(
                f"Canvas action: user={user_id}, action={event.action}, "
                f"element={event.element_id}, session={session_id}"
            )

        except ValidationError as e:
            logger.warning(f"Invalid canvas action data: {e}")
        except Exception as e:
            logger.error(f"Canvas action error: {e}", exc_info=True)
