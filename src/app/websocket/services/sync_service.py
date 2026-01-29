from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EventThrottler:
    """Throttles events per user."""

    def __init__(self, max_events: int, window_seconds: float):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def can_emit(self, user_id: str) -> bool:
        """Check if event can be emitted."""
        now = time.time()
        key = user_id

        timestamps = self._timestamps[key]
        timestamps[:] = [
            ts for ts in timestamps
            if now - ts < self.window_seconds
        ]

        if len(timestamps) >= self.max_events:
            return False

        timestamps.append(now)
        return True

    def cleanup_old_entries(self) -> None:
        """Remove old timestamp entries."""
        now = time.time()
        for key in list(self._timestamps.keys()):
            timestamps = self._timestamps[key]
            timestamps[:] = [
                ts for ts in timestamps
                if now - ts < self.window_seconds
            ]
            if not timestamps:
                del self._timestamps[key]


class SyncService:
    """Manages state synchronization and throttling."""

    def __init__(self):
        self.cursor_throttler = EventThrottler(
            max_events=30,
            window_seconds=1.0
        )
        self.selection_throttler = EventThrottler(
            max_events=10,
            window_seconds=1.0
        )
        self._debounce_tasks: dict[str, asyncio.Task] = {}

    def can_emit_cursor(self, user_id: str) -> bool:
        """Check if cursor event can be emitted."""
        return self.cursor_throttler.can_emit(user_id)

    def can_emit_selection(self, user_id: str) -> bool:
        """Check if selection event can be emitted."""
        return self.selection_throttler.can_emit(user_id)

    async def debounce(
        self,
        key: str,
        delay_ms: int,
        callback: Any
    ) -> None:
        """Debounce an event."""
        if key in self._debounce_tasks:
            self._debounce_tasks[key].cancel()

        async def delayed_callback():
            await asyncio.sleep(delay_ms / 1000)
            await callback()
            self._debounce_tasks.pop(key, None)

        task = asyncio.create_task(delayed_callback())
        self._debounce_tasks[key] = task

    def cleanup(self) -> None:
        """Clean up throttler state."""
        self.cursor_throttler.cleanup_old_entries()
        self.selection_throttler.cleanup_old_entries()

    def create_sync_event(
        self,
        event_type: str,
        user_id: str,
        session_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create standardized sync event."""
        return {
            "type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

    def validate_canvas_action(
        self,
        action: str,
        element_id: str,
        data: dict[str, Any]
    ) -> bool:
        """Validate canvas action data."""
        valid_actions = {"move", "resize", "delete", "create", "update"}

        if action not in valid_actions:
            logger.warning(f"Invalid canvas action: {action}")
            return False

        if not element_id or not isinstance(element_id, str):
            logger.warning("Invalid element_id for canvas action")
            return False

        if action == "move" and "position" not in data:
            logger.warning("Missing position for move action")
            return False

        if action == "resize" and "size" not in data:
            logger.warning("Missing size for resize action")
            return False

        return True

    def create_conflict_resolution_event(
        self,
        conflict_type: str,
        element_id: str,
        user_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create conflict resolution event."""
        return {
            "type": "conflict",
            "conflict_type": conflict_type,
            "element_id": element_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
