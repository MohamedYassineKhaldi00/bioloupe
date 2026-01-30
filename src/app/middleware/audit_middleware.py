from __future__ import annotations

import asyncio
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.base import async_session_maker
from app.models.audit_log import AuditAction, ResourceType
from app.services.audit_service import log_audit_background

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = getattr(request.state, "process_id", "unknown")

        ip_address = self._extract_ip_address(request)
        user_agent = request.headers.get("user-agent")

        response = await call_next(request)

        if self._should_audit(request, response):
            asyncio.create_task(
                self._log_request(
                    request, response, correlation_id, ip_address, user_agent
                )
            )

        return response

    def _extract_ip_address(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"

    def _should_audit(self, request: Request, response: Response) -> bool:
        if request.url.path.startswith("/api/v1/admin/audit-logs"):
            return False

        if request.url.path in ["/health", "/api/v1/health"]:
            return False

        if response.status_code == 401 or response.status_code == 403:
            return True

        if request.url.path.startswith("/api/v1/auth"):
            return True

        if request.url.path.startswith("/api/v1/oauth"):
            return True

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            return True

        return False

    async def _log_request(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        ip_address: str,
        user_agent: str | None,
    ) -> None:
        try:
            user_id = None
            if hasattr(request.state, "user"):
                user_id = getattr(request.state.user, "id", None)

            action = self._determine_action(request, response)
            resource_type, resource_id = self._extract_resource(request)
            success = response.status_code < 400

            details = {
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
            }

            asyncio.create_task(
                log_audit_background(
                    db_session_maker=async_session_maker,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=success,
                    correlation_id=correlation_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    user_id=user_id,
                    details=details,
                )
            )
        except Exception as exc:
            logger.error(f"Failed to queue audit log: {exc}", exc_info=True)

    def _determine_action(
        self, request: Request, response: Response
    ) -> AuditAction:
        path = request.url.path.lower()

        if "/login" in path:
            return (
                AuditAction.LOGIN_SUCCESS
                if response.status_code < 400
                else AuditAction.LOGIN_FAILURE
            )

        if "/logout" in path:
            return AuditAction.LOGOUT

        if "/refresh" in path:
            return AuditAction.TOKEN_REFRESH

        if "/oauth" in path and "link" in path:
            return AuditAction.OAUTH_LINK

        if "/password" in path:
            return AuditAction.PASSWORD_CHANGE

        if response.status_code == 403:
            return AuditAction.PERMISSION_DENIED

        if "/download" in path or "/export" in path:
            return AuditAction.MATERIAL_DOWNLOAD

        if request.method == "POST":
            if "/team" in path:
                return AuditAction.TEAM_CREATED
            if "/session" in path:
                return AuditAction.SESSION_CREATED
            if "/material" in path:
                return AuditAction.MATERIAL_CREATED

        if request.method in ["PUT", "PATCH"]:
            if "/team" in path:
                return AuditAction.TEAM_UPDATED
            if "/session" in path:
                return AuditAction.SESSION_UPDATED
            if "/material" in path:
                return AuditAction.MATERIAL_UPDATED

        if request.method == "DELETE":
            if "/team" in path:
                return AuditAction.TEAM_DELETED
            if "/session" in path:
                return AuditAction.SESSION_DELETED
            if "/material" in path:
                return AuditAction.MATERIAL_DELETED

        return AuditAction.SENSITIVE_DATA_ACCESS

    def _extract_resource(self, request: Request) -> tuple[ResourceType, str]:
        path = request.url.path.lower()
        parts = [p for p in path.split("/") if p]

        if "team" in path:
            resource_id = self._find_uuid_in_parts(parts)
            return ResourceType.TEAM, resource_id

        if "session" in path:
            resource_id = self._find_uuid_in_parts(parts)
            return ResourceType.SESSION, resource_id

        if "material" in path:
            resource_id = self._find_uuid_in_parts(parts)
            return ResourceType.MATERIAL, resource_id

        if "user" in path:
            resource_id = self._find_uuid_in_parts(parts)
            return ResourceType.USER, resource_id

        if "oauth" in path:
            resource_id = self._find_uuid_in_parts(parts)
            return ResourceType.OAUTH_ACCOUNT, resource_id

        return ResourceType.SYSTEM, "system"

    def _find_uuid_in_parts(self, parts: list[str]) -> str:
        for part in parts:
            if len(part) == 36 and part.count("-") == 4:
                return part
        return "unknown"
