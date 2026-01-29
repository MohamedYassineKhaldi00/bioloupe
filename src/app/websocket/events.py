from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_event_handlers: dict[str, list[Callable]] = {}


def register_event(event_name: str):
    """Decorator to register event handlers."""
    def decorator(func: Callable):
        if event_name not in _event_handlers:
            _event_handlers[event_name] = []
        _event_handlers[event_name].append(func)
        logger.debug(f"Registered handler for event: {event_name}")
        return func
    return decorator


async def emit_event(
    event_name: str,
    data: dict[str, Any],
    context: dict[str, Any]
) -> None:
    """Execute all handlers for an event."""
    handlers = _event_handlers.get(event_name, [])

    for handler in handlers:
        try:
            await handler(data, context)
        except Exception as e:
            logger.error(
                f"Error in event handler",
                extra={
                    "event": event_name,
                    "handler": handler.__name__,
                    "error": str(e)
                },
                exc_info=True
            )


def get_registered_events() -> list[str]:
    """Get list of all registered event names."""
    return list(_event_handlers.keys())
