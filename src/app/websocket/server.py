from __future__ import annotations

import asyncio
import logging
from typing import Any

import socketio
from pydantic import ValidationError

from ..core.config import get_settings
from ..db.redis_client import get_redis
from ..schemas.websocket_schemas import ErrorEvent, HeartbeatEvent
from .auth_middleware import authenticate_websocket
from .connection_manager import ConnectionManager
from .namespaces import (
    CollaborationNamespace,
    CRDTNamespace,
    PresenceNamespace,
    SessionNamespace,
)
from .services.presence_service import PresenceService
from .services.sync_service import SyncService
from .services.yjs_service import YjsService

logger = logging.getLogger(__name__)

settings = get_settings()

redis_client = get_redis()
connection_manager = ConnectionManager(redis_client)
presence_service = PresenceService(redis_client)
sync_service = SyncService()
yjs_service = YjsService(redis_client)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.environment == "development"
    and "*"
    or settings.environment,
    logger=True,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=30,
)

ws_app = socketio.ASGIApp(
    socketio_server=sio,
    socketio_path="/ws/socket.io"
)

session_ns = SessionNamespace(
    "/sessions",
    connection_manager,
    presence_service,
    sync_service
)
presence_ns = PresenceNamespace(
    "/presence",
    connection_manager,
    presence_service,
    sync_service
)
collaboration_ns = CollaborationNamespace(
    "/collaboration",
    connection_manager,
    presence_service,
    sync_service
)
crdt_ns = CRDTNamespace(
    "/crdt",
    connection_manager,
    yjs_service
)

sio.register_namespace(session_ns)
sio.register_namespace(presence_ns)
sio.register_namespace(collaboration_ns)
sio.register_namespace(crdt_ns)


_cleanup_task: asyncio.Task | None = None
_yjs_save_task: asyncio.Task | None = None
_yjs_cleanup_task: asyncio.Task | None = None


async def start_background_tasks() -> None:
    """Start background tasks."""
    global _cleanup_task, _yjs_save_task, _yjs_cleanup_task
    _cleanup_task = asyncio.create_task(_presence_cleanup_loop())
    _yjs_save_task = asyncio.create_task(_yjs_save_loop())
    _yjs_cleanup_task = asyncio.create_task(_yjs_cleanup_loop())
    logger.info("Background tasks started")


async def stop_background_tasks() -> None:
    """Stop background tasks."""
    global _cleanup_task, _yjs_save_task, _yjs_cleanup_task

    tasks = [_cleanup_task, _yjs_save_task, _yjs_cleanup_task]
    for task in tasks:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    _cleanup_task = None
    _yjs_save_task = None
    _yjs_cleanup_task = None
    logger.info("Background tasks stopped")


async def _presence_cleanup_loop() -> None:
    """Background task to clean up stale presence."""
    while True:
        try:
            await asyncio.sleep(30)
            removed = await presence_service.cleanup_stale_presence()
            sync_service.cleanup()

            if removed > 0:
                logger.info(
                    f"Presence cleanup: removed {removed} stale entries"
                )

        except asyncio.CancelledError:
            logger.info("Presence cleanup task cancelled")
            break
        except Exception as e:
            logger.error(
                f"Presence cleanup error: {e}",
                exc_info=True
            )


async def _yjs_save_loop() -> None:
    """Background task to persist Y.js documents."""
    while True:
        try:
            await asyncio.sleep(30)
            count = await yjs_service.save_all_documents()

            if count > 0:
                logger.debug(f"Saved {count} Y.js documents")

        except asyncio.CancelledError:
            logger.info("Y.js save task cancelled")
            await yjs_service.save_all_documents()
            break
        except Exception as e:
            logger.error(
                f"Y.js save error: {e}",
                exc_info=True
            )


async def _yjs_cleanup_loop() -> None:
    """Background task to cleanup inactive Y.js documents."""
    while True:
        try:
            await asyncio.sleep(300)
            removed = await yjs_service.cleanup_inactive_documents()

            if removed > 0:
                logger.info(
                    f"Cleaned up {removed} inactive Y.js documents"
                )

        except asyncio.CancelledError:
            logger.info("Y.js cleanup task cancelled")
            break
        except Exception as e:
            logger.error(
                f"Y.js cleanup error: {e}",
                exc_info=True
            )


@sio.event
async def connect(
    sid: str,
    environ: dict[str, Any],
    auth: dict[str, Any] | None
) -> bool:
    """Handle WebSocket connection with authentication."""
    try:
        if not auth:
            logger.warning(f"Connection rejected: No auth data, sid={sid}")
            return False

        user_id_str, user = await authenticate_websocket(auth)

        logger.info(
            f"WebSocket connected: sid={sid}, user_id={user_id_str}"
        )

        await sio.save_session(
            sid,
            {
                "user_id": user_id_str,
                "full_name": user.full_name,
                "authenticated": True,
            }
        )

        return True

    except ConnectionRefusedError as e:
        logger.warning(f"Connection refused: {e}, sid={sid}")
        return False
    except Exception as e:
        logger.error(
            f"Connection error: {e}, sid={sid}",
            exc_info=True
        )
        return False


@sio.event
async def disconnect(sid: str) -> None:
    """Handle WebSocket disconnection."""
    try:
        session_data = await sio.get_session(sid)
        user_id = session_data.get("user_id") if session_data else None

        conn_data = await connection_manager.disconnect_user(sid)

        if conn_data:
            session_id = conn_data["session_id"]
            await sio.emit(
                "user_disconnected",
                {
                    "user_id": conn_data["user_id"],
                    "session_id": session_id,
                },
                room=f"session:{session_id}",
            )

        logger.info(
            f"WebSocket disconnected: sid={sid}, user_id={user_id}"
        )

    except Exception as e:
        logger.error(
            f"Disconnect error: {e}, sid={sid}",
            exc_info=True
        )


@sio.event
async def heartbeat(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    """Handle client heartbeat to maintain connection."""
    try:
        HeartbeatEvent(**data)

        session_data = await sio.get_session(sid)
        if not session_data:
            return {"success": False, "error": "Not authenticated"}

        conn_data = await connection_manager.get_connection_data(sid)
        if conn_data:
            await connection_manager.refresh_presence(
                conn_data["session_id"],
                conn_data["user_id"],
                conn_data["full_name"]
            )

        return {"success": True, "timestamp": data.get("timestamp")}

    except ValidationError:
        return {"success": False, "error": "Invalid heartbeat data"}


@sio.event
async def join_session(
    sid: str,
    data: dict[str, Any]
) -> dict[str, Any]:
    """Handle user joining a session."""
    try:
        session_data = await sio.get_session(sid)
        if not session_data:
            return {"success": False, "error": "Not authenticated"}

        session_id = str(data.get("session_id"))
        user_id = session_data["user_id"]
        full_name = session_data["full_name"]

        await connection_manager.connect_user(
            sid,
            user_id,
            session_id,
            full_name
        )

        await sio.enter_room(sid, f"session:{session_id}")

        participants = await connection_manager.get_session_participants(
            session_id
        )

        await sio.emit(
            "user_joined",
            {
                "session_id": session_id,
                "user_id": user_id,
                "full_name": full_name,
            },
            room=f"session:{session_id}",
            skip_sid=sid
        )

        logger.info(f"User joined session: sid={sid}, session_id={session_id}")

        return {
            "success": True,
            "participants": participants
        }

    except Exception as e:
        logger.error(f"Join session error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@sio.event
async def leave_session(
    sid: str,
    data: dict[str, Any]
) -> dict[str, Any]:
    """Handle user leaving a session."""
    try:
        conn_data = await connection_manager.disconnect_user(sid)

        if conn_data:
            session_id = conn_data["session_id"]
            await sio.leave_room(sid, f"session:{session_id}")

            await sio.emit(
                "user_left",
                {
                    "session_id": session_id,
                    "user_id": conn_data["user_id"],
                },
                room=f"session:{session_id}"
            )

        return {"success": True}

    except Exception as e:
        logger.error(f"Leave session error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def send_error(
    sid: str,
    message: str,
    code: str | None = None
) -> None:
    """Send error event to client."""
    error_event = ErrorEvent(
        message=message,
        code=code
    )
    await sio.emit("error", error_event.model_dump(), to=sid)
