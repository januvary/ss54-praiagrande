"""
CSRF Protection Service
Implements double-submit cookie pattern for CSRF protection.

The CSRF token is stored in a persistent cookie (7 days).
The middleware sets the cookie; validation is done via dependency injection.

Templates read the token from the cookie and include it in forms.
"""

import secrets
import hmac
import hashlib
from contextlib import suppress
from typing import Optional
from fastapi import Request
from app.config import settings


def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(32)


def sign_csrf_token(token: str) -> str:
    """Sign a CSRF token with the secret key."""
    signature = hmac.new(
        settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256
    ).hexdigest()
    return f"{token}.{signature}"


def verify_csrf_signature(signed_token: str) -> Optional[str]:
    """Verify CSRF token signature and return the token if valid."""
    with suppress(ValueError):
        token, signature = signed_token.rsplit(".", 1)
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256
        ).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return token
    return None


def get_csrf_token_from_cookie(request: Request) -> Optional[str]:
    """Get and verify CSRF token from cookie."""
    signed_token = request.cookies.get("csrf_token")
    if not signed_token:
        return None
    return verify_csrf_signature(signed_token)


class CSRFMiddleware:
    """
    Simplified middleware that only sets CSRF cookie.

    Validation is now handled by the validate_csrf_token dependency
    in app/dependencies/csrf.py, which is more testable and "FastAPI-idiomatic".

    This middleware:
    1. Checks if CSRF cookie exists
    2. If not, generates and sets a new signed token
    3. Skips API routes (/api/*) which use JWT auth

    Templates should read the token from request.cookies and include it in forms.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip CSRF for API routes (Bearer token auth)
        if path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        # Check if CSRF cookie already exists
        # Create a minimal request just to read cookies
        from starlette.requests import Request

        request = Request(scope, receive)
        existing_cookie = request.cookies.get("csrf_token")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Only set cookie if it doesn't exist
                if not existing_cookie:
                    token = generate_csrf_token()
                    signed_token = sign_csrf_token(token)
                    # Use SameSite=strict for stronger CSRF protection
                    cookie_value = f"csrf_token={signed_token}; Path=/; SameSite=strict; Max-Age=604800"  # 7 days
                    if not settings.DEBUG:
                        cookie_value += "; Secure"

                    headers = list(message.get("headers", []))
                    headers.append((b"set-cookie", cookie_value.encode()))
                    message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)
