"""Security headers middleware."""

from __future__ import annotations

import logging
from typing import Callable
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = self._get_csp_policy()
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response

    def _get_csp_policy(self) -> str:
        """Content Security Policy."""
        return (
            "default-src 'self'; "
            "script-src 'self' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )


class CSRFProtectionMiddleware:
    """CSRF token validation for state-changing requests."""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Validate CSRF token for state-changing requests."""
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            # Skip CSRF for API endpoints with token auth
            if request.url.path.startswith("/api/"):
                return await call_next(request)

            # Verify CSRF token
            csrf_token = request.headers.get("X-CSRF-Token")

            if not csrf_token:
                from starlette.responses import JSONResponse

                return JSONResponse(
                    {"detail": "CSRF token missing"}, status_code=403
                )

            # Validate token against session
            # This would check against stored session token
            # For now, basic validation

        return await call_next(request)


class TLSEnforcementMiddleware:
    """Enforce HTTPS in production."""

    def __init__(self, app: Callable, enforce: bool = True):
        self.app = app
        self.enforce = enforce

    async def __call__(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Redirect HTTP to HTTPS if enabled."""
        if self.enforce and request.url.scheme != "https":
            # Health checks exempt
            if request.url.path == "/health":
                return await call_next(request)

            # Redirect to HTTPS
            from starlette.responses import RedirectResponse

            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=301)

        return await call_next(request)
