"""
Security Headers Middleware
Adds comprehensive security headers to all responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Headers implemented:
    - X-Frame-Options: Prevents clickjacking
    - X-Content-Type-Options: Prevents MIME sniffing
    - Strict-Transport-Security: Forces HTTPS (production only)
    - Content-Security-Policy: Controls resource loading with nonce-based CSP
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser features

    Requires CSPNonceMiddleware to run before this middleware.
    """

    async def dispatch(self, request, call_next):
        # Process the request
        response = await call_next(request)

        # Prevent clickjacking - allow same-origin framing for PDF embeds
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # HTTPS enforcement (production only)
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy with nonce
        # blob: needed for file preview object URLs and PDF embeds
        nonce = getattr(request.state, "csp_nonce", "")
        csp_policy = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            f"style-src 'self' 'nonce-{nonce}'",
            "font-src 'self'",
            "img-src 'self' data: blob:",
            "object-src 'self' blob:",
            "media-src 'self' blob:",
            "frame-src 'self' blob:",
            "frame-ancestors 'self'",
            "base-uri 'self'",
            "form-action 'self'",
            "connect-src 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_policy)

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (Feature Policy successor)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        return response
