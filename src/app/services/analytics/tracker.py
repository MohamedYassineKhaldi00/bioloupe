"""Analytics event tracking service."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    """Track analytics events for platform usage."""

    def __init__(self, db: Any, redis_client: Any | None = None):
        self.db = db
        self.redis = redis_client

    async def track_event(
        self,
        user_id: str,
        event_name: str,
        properties: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> None:
        """Track analytics event."""
        event_id = str(uuid4())
        event_timestamp = timestamp or datetime.utcnow()

        # Store in database
        event_data = {
            "id": event_id,
            "user_id": user_id,
            "event_name": event_name,
            "properties": properties,
            "timestamp": event_timestamp,
        }

        # Placeholder: would save to analytics_events table
        logger.info(f"Analytics event tracked: {event_name}", extra=event_data)

        # Push to Redis for real-time analytics
        if self.redis:
            await self._push_to_redis(event_data)

    async def _push_to_redis(self, event_data: dict[str, Any]) -> None:
        """Push event to Redis for real-time processing."""
        try:
            await self.redis.lpush(
                "analytics:events",
                json.dumps(
                    {
                        "user_id": event_data["user_id"],
                        "event": event_data["event_name"],
                        "properties": event_data["properties"],
                        "timestamp": event_data["timestamp"].isoformat(),
                    }
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to push to Redis: {e}")

    async def track_page_view(
        self, user_id: str, path: str, session_id: str | None = None
    ) -> None:
        """Track page view event."""
        await self.track_event(
            user_id=user_id,
            event_name="page_view",
            properties={"path": path, "session_id": session_id},
        )

    async def track_feature_usage(
        self, user_id: str, feature: str, action: str, metadata: dict[str, Any]
    ) -> None:
        """Track feature usage event."""
        await self.track_event(
            user_id=user_id,
            event_name="feature_usage",
            properties={"feature": feature, "action": action, **metadata},
        )

    async def track_session_event(
        self, user_id: str, session_id: str, action: str
    ) -> None:
        """Track session-related event."""
        await self.track_event(
            user_id=user_id,
            event_name=f"session_{action}",
            properties={"session_id": session_id},
        )

    async def track_material_event(
        self, user_id: str, material_id: str, action: str, material_type: str
    ) -> None:
        """Track material-related event."""
        await self.track_event(
            user_id=user_id,
            event_name=f"material_{action}",
            properties={"material_id": material_id, "material_type": material_type},
        )
