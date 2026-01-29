from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import socketio
from pydantic import ValidationError

from ...schemas.crdt_schemas import (
    MaterialSubscribeEvent,
    MaterialUnsubscribeEvent,
    YjsAwarenessUpdateEvent,
    YjsSyncStep1Event,
    YjsUpdateEvent,
)
from ..services.yjs_service import YjsService

logger = logging.getLogger(__name__)


class CRDTHandlers:
    """Handles Y.js CRDT synchronization and updates."""

    def __init__(
        self,
        sio: socketio.AsyncServer,
        yjs_service: YjsService
    ):
        self.sio = sio
        self.yjs = yjs_service

    async def get_user_from_session(
        self,
        sid: str
    ) -> dict[str, Any] | None:
        """Get user data from socket session."""
        session_data = await self.sio.get_session(sid)
        if not session_data or not session_data.get("authenticated"):
            return None
        return session_data

    async def verify_material_access(
        self,
        user_id: str,
        material_id: str
    ) -> bool:
        """Verify user has access to material."""
        # TODO: Implement actual permission check
        # For now, allow all authenticated users
        return True

    async def verify_material_write_permission(
        self,
        user_id: str,
        material_id: str
    ) -> bool:
        """Verify user has write permission."""
        # TODO: Implement actual permission check
        return True

    async def handle_yjs_sync_step1(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Client sends state vector, server responds with updates."""
        try:
            event = YjsSyncStep1Event(**data)
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                await self._send_error(
                    sid,
                    "Authentication required",
                    "AUTH_REQUIRED"
                )
                return

            user_id = user_data["user_id"]
            material_id = str(event.material_id)

            has_access = await self.verify_material_access(
                user_id,
                material_id
            )
            if not has_access:
                await self._send_error(
                    sid,
                    "Access denied",
                    "ACCESS_DENIED"
                )
                return

            client_state_vector = bytes.fromhex(event.state_vector)
            missing_updates = await self.yjs.get_missing_updates(
                material_id,
                client_state_vector
            )

            await self.sio.emit(
                "yjs:sync_step2",
                {
                    "material_id": material_id,
                    "update": missing_updates.hex()
                },
                room=sid
            )

            logger.info(
                f"Y.js sync step1: user={user_id}, "
                f"material={material_id}"
            )

        except ValidationError as e:
            await self._send_error(
                sid,
                f"Invalid sync_step1 data: {e}",
                "VALIDATION_ERROR"
            )
        except Exception as e:
            logger.error(f"Sync step1 error: {e}", exc_info=True)
            await self._send_error(sid, "Sync failed", "SYNC_ERROR")

    async def handle_yjs_update(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Client sends document update."""
        try:
            event = YjsUpdateEvent(**data)
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                await self._send_error(
                    sid,
                    "Authentication required",
                    "AUTH_REQUIRED"
                )
                return

            user_id = user_data["user_id"]
            material_id = str(event.material_id)

            has_permission = await self.verify_material_write_permission(
                user_id,
                material_id
            )
            if not has_permission:
                await self._send_error(
                    sid,
                    "Write permission denied",
                    "PERMISSION_DENIED"
                )
                return

            update = bytes.fromhex(event.update)
            await self.yjs.apply_update(material_id, update)

            await self.sio.emit(
                "yjs:update",
                {
                    "material_id": material_id,
                    "update": event.update,
                    "origin": user_id
                },
                room=f"material:{material_id}",
                skip_sid=sid
            )

            logger.info(
                f"Y.js update: user={user_id}, material={material_id}"
            )

        except ValidationError as e:
            await self._send_error(
                sid,
                f"Invalid update data: {e}",
                "VALIDATION_ERROR"
            )
        except Exception as e:
            logger.error(f"Update error: {e}", exc_info=True)
            await self._send_error(sid, "Update failed", "UPDATE_ERROR")

    async def handle_yjs_awareness_update(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast awareness update (cursor, selection)."""
        try:
            event = YjsAwarenessUpdateEvent(**data)
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                return

            user_id = user_data["user_id"]
            material_id = str(event.material_id)

            await self.sio.emit(
                "yjs:awareness_update",
                {
                    "material_id": material_id,
                    "awareness_update": event.awareness_update,
                    "user_id": user_id
                },
                room=f"material:{material_id}",
                skip_sid=sid
            )

        except ValidationError as e:
            logger.warning(f"Invalid awareness update: {e}")
        except Exception as e:
            logger.error(f"Awareness error: {e}", exc_info=True)

    async def handle_material_subscribe(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Client subscribes to material for collaborative editing."""
        try:
            event = MaterialSubscribeEvent(**data)
            user_data = await self.get_user_from_session(sid)
            if not user_data:
                await self._send_error(
                    sid,
                    "Authentication required",
                    "AUTH_REQUIRED"
                )
                return

            user_id = user_data["user_id"]
            material_id = str(event.material_id)

            has_access = await self.verify_material_access(
                user_id,
                material_id
            )
            if not has_access:
                await self._send_error(
                    sid,
                    "Access denied",
                    "ACCESS_DENIED"
                )
                return

            await self.sio.enter_room(sid, f"material:{material_id}")

            state_vector = await self.yjs.get_state_vector(material_id)
            await self.sio.emit(
                "yjs:sync_step1",
                {
                    "material_id": material_id,
                    "state_vector": state_vector.hex()
                },
                room=sid
            )

            logger.info(
                f"Material subscribe: user={user_id}, "
                f"material={material_id}"
            )

        except ValidationError as e:
            await self._send_error(
                sid,
                f"Invalid subscribe data: {e}",
                "VALIDATION_ERROR"
            )
        except Exception as e:
            logger.error(f"Subscribe error: {e}", exc_info=True)
            await self._send_error(
                sid,
                "Subscribe failed",
                "SUBSCRIBE_ERROR"
            )

    async def handle_material_unsubscribe(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Client unsubscribes from material."""
        try:
            event = MaterialUnsubscribeEvent(**data)
            material_id = str(event.material_id)

            await self.sio.leave_room(sid, f"material:{material_id}")

            logger.info(f"Material unsubscribe: material={material_id}")

        except ValidationError as e:
            logger.warning(f"Invalid unsubscribe data: {e}")
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}", exc_info=True)

    async def _send_error(
        self,
        sid: str,
        message: str,
        code: str
    ) -> None:
        """Send error event to client."""
        await self.sio.emit(
            "error",
            {
                "type": "crdt_error",
                "message": message,
                "code": code
            },
            room=sid
        )
