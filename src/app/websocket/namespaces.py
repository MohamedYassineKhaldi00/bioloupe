from __future__ import annotations

import logging
from typing import Any

import socketio

from .connection_manager import ConnectionManager
from .handlers.collaboration import CollaborationHandlers
from .handlers.crdt import CRDTHandlers
from .handlers.presence import PresenceHandlers
from .services.presence_service import PresenceService
from .services.sync_service import SyncService
from .services.yjs_service import YjsService

logger = logging.getLogger(__name__)


class SessionNamespace(socketio.AsyncNamespace):
    """Handles session-specific events."""

    def __init__(
        self,
        namespace: str,
        connection_manager: ConnectionManager,
        presence_service: PresenceService,
        sync_service: SyncService
    ):
        super().__init__(namespace)
        self.connection_manager = connection_manager
        self.presence_handlers = PresenceHandlers(
            self.server,
            presence_service,
            sync_service
        )

    async def on_join_session(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle user joining a session room."""
        return await self.presence_handlers.handle_join_session(sid, data)

    async def on_leave_session(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle user leaving a session room."""
        return await self.presence_handlers.handle_leave_session(sid, data)


class PresenceNamespace(socketio.AsyncNamespace):
    """Handles user presence and cursor tracking."""

    def __init__(
        self,
        namespace: str,
        connection_manager: ConnectionManager,
        presence_service: PresenceService,
        sync_service: SyncService
    ):
        super().__init__(namespace)
        self.connection_manager = connection_manager
        self.presence_handlers = PresenceHandlers(
            self.server,
            presence_service,
            sync_service
        )

    async def on_cursor_position(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast cursor position to session."""
        await self.presence_handlers.handle_cursor_move(sid, data)

    async def on_heartbeat(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Handle client heartbeat."""
        await self.presence_handlers.handle_heartbeat(sid, data)


class CollaborationNamespace(socketio.AsyncNamespace):
    """Handles real-time collaboration events."""

    def __init__(
        self,
        namespace: str,
        connection_manager: ConnectionManager,
        presence_service: PresenceService,
        sync_service: SyncService
    ):
        super().__init__(namespace)
        self.connection_manager = connection_manager
        self.collaboration_handlers = CollaborationHandlers(
            self.server,
            presence_service,
            sync_service
        )

    async def on_material_added(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast material addition to session."""
        await self.collaboration_handlers.handle_material_added(sid, data)

    async def on_material_updated(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast material updates."""
        await self.collaboration_handlers.handle_material_updated(sid, data)

    async def on_selection(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Broadcast selection changes."""
        await self.collaboration_handlers.handle_selection_change(sid, data)

    async def on_canvas_action(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Synchronize canvas actions."""
        await self.collaboration_handlers.handle_canvas_action(sid, data)


class CRDTNamespace(socketio.AsyncNamespace):
    """Handles Y.js CRDT collaborative editing events."""

    def __init__(
        self,
        namespace: str,
        connection_manager: ConnectionManager,
        yjs_service: YjsService
    ):
        super().__init__(namespace)
        self.connection_manager = connection_manager
        self.crdt_handlers = CRDTHandlers(self.server, yjs_service)

    async def on_yjs_sync_step1(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Handle Y.js sync step 1: client sends state vector."""
        await self.crdt_handlers.handle_yjs_sync_step1(sid, data)

    async def on_yjs_update(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Handle Y.js document update from client."""
        await self.crdt_handlers.handle_yjs_update(sid, data)

    async def on_yjs_awareness_update(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Handle Y.js awareness update (cursor, selection)."""
        await self.crdt_handlers.handle_yjs_awareness_update(sid, data)

    async def on_material_subscribe(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Subscribe to material for collaborative editing."""
        await self.crdt_handlers.handle_material_subscribe(sid, data)

    async def on_material_unsubscribe(
        self,
        sid: str,
        data: dict[str, Any]
    ) -> None:
        """Unsubscribe from material."""
        await self.crdt_handlers.handle_material_unsubscribe(sid, data)
