"""
Admin Session Authentication Middleware

Provides session-based authentication for the admin panel.
Uses signed cookies with HMAC (same pattern as CSRF tokens).

Flow:
1. Admin submits password to /admin/login
2. If valid, session cookie is set
3. Middleware checks session cookie for all /admin/* routes
4. If session invalid/expired, redirect to login page

Security:
- Session cookie is HMAC-signed (tamper-proof)
- Session includes timestamp (expiration enforced)
- Cookie is HttpOnly, Secure, SameSite=strict
- IP whitelist is checked BEFORE this middleware (defense in depth)
"""

import hmac
import hashlib
import time
from urllib.parse import quote
from fastapi import Request
from fastapi.responses import RedirectResponse
from app.config import settings

ADMIN_SESSION_COOKIE_NAME = "admin_session"


def create_admin_session_token() -> str:
    """
    Create a signed admin session token.

    Token format: timestamp.signature
    - timestamp: Unix timestamp when session was created
    - signature: HMAC-SHA256 of timestamp using SECRET_KEY

    Returns:
        Signed session token
    """
    timestamp = str(int(time.time()))
    signature = hmac.new(
        settings.SECRET_KEY.encode(), timestamp.encode(), hashlib.sha256
    ).hexdigest()
    return f"{timestamp}.{signature}"


def verify_admin_session_token(token: str) -> bool:
    """
    Verify admin session token and check expiration.

    Args:
        token: Signed session token

    Returns:
        True if valid and not expired, False otherwise
    """
    if not token:
        return False

    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False

        timestamp_str, signature = parts

        # Verify signature
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode(), timestamp_str.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return False

        # Check expiration
        timestamp = int(timestamp_str)
        max_age_seconds = settings.ADMIN_SESSION_DAYS * 24 * 60 * 60
        if time.time() - timestamp > max_age_seconds:
            return False

        return True

    except (ValueError, TypeError, AttributeError):
        return False


class AdminAuthMiddleware:
    """
    Middleware that enforces session authentication for admin routes.

    Must be added AFTER AdminWhitelistMiddleware in the middleware stack
    so IP check happens first (fail fast for external requests).

    Routes that bypass authentication:
    - /admin/login (GET/POST)
    - /admin/logout (POST)

    All other /admin/* routes require valid session cookie.
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = {"/admin/login", "/admin/logout"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Only check /admin/* routes
        if not path.startswith("/admin"):
            await self.app(scope, receive, send)
            return

        # Allow public paths (login, logout)
        if path in self.PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        # Check if admin password is configured
        # If not configured, allow access (IP whitelist is still enforced)
        if not settings.ADMIN_PASSWORD_HASH:
            await self.app(scope, receive, send)
            return

        # Check session cookie
        request = Request(scope, receive)
        session_token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)

        if session_token and verify_admin_session_token(session_token):
            # Valid session, proceed
            await self.app(scope, receive, send)
            return

        # Invalid or missing session - redirect to login
        # Include original path for redirect after login
        login_url = f"/admin/login?next={quote(path)}"
        response = RedirectResponse(url=login_url, status_code=302)

        # Send redirect response
        await response(scope, receive, send)


def set_admin_session_cookie(response: RedirectResponse) -> RedirectResponse:
    """
    Set admin session cookie on a response.

    Args:
        response: Response to add cookie to

    Returns:
        The same response with cookie set
    """
    token = create_admin_session_token()
    max_age = settings.ADMIN_SESSION_DAYS * 24 * 60 * 60

    cookie_value = (
        f"{ADMIN_SESSION_COOKIE_NAME}={token}; "
        f"Path=/admin; "
        f"HttpOnly; "
        f"SameSite=strict; "
        f"Max-Age={max_age}"
    )

    if not settings.DEBUG:
        cookie_value += "; Secure"

    response.headers.append("set-cookie", cookie_value)
    return response


def clear_admin_session_cookie(response: RedirectResponse) -> RedirectResponse:
    """
    Clear admin session cookie on a response.

    Args:
        response: Response to add cookie to

    Returns:
        The same response with cookie cleared
    """
    cookie_value = (
        f"{ADMIN_SESSION_COOKIE_NAME}=; "
        f"Path=/admin; "
        f"HttpOnly; "
        f"SameSite=strict; "
        f"Max-Age=0"
    )

    if not settings.DEBUG:
        cookie_value += "; Secure"

    response.headers.append("set-cookie", cookie_value)
    return response
