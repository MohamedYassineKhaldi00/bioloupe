from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        process_id = str(uuid.uuid4())
        request.state.process_id = process_id
        
        start_time = time.time()
        
        log_data = {
            "process_id": process_id,
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
        }
        
        logger.info("Request started", extra=log_data)
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        log_data.update({
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        })
        
        logger.info("Request completed", extra=log_data)
        
        response.headers["X-Process-ID"] = process_id
        
        return response


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[JSONLogHandler()],
    )


class JSONLogHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        log_entry = {
            "timestamp": self.format_time(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if hasattr(record, "process_id"):
            log_entry["process_id"] = record.process_id
        
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName", 
                          "levelname", "levelno", "lineno", "module", "msecs", 
                          "pathname", "process", "processName", "relativeCreated", 
                          "thread", "threadName", "exc_info", "exc_text", "stack_info"]:
                log_entry[key] = value
        
        print(json.dumps(log_entry, default=str))
    
    def format_time(self, record: logging.LogRecord) -> str:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
