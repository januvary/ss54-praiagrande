"""
CSRF Validation Dependency

Provides FastAPI dependency for CSRF token validation.
Moves validation logic from middleware to dependency injection pattern,
making it more testable and "FastAPI-idiomatic".
"""

import secrets
from fastapi import HTTPException, Request, status


async def validate_csrf_token(request: Request) -> None:
    """
    Dependency that validates CSRF token for unsafe methods.

    This dependency validates that the CSRF token in the request (from form
    or header) matches the signed token in the cookie. Uses the double-submit
    cookie pattern for security.

    Safe methods (GET, HEAD, OPTIONS) are automatically exempt.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 403 if CSRF validation fails

    Usage:
        @router.post("/submit")
        async def submit_form(
            request: Request,
            csrf_protected: None = Depends(validate_csrf_token)
        ):
            ...
    """
    # Skip validation for safe methods
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return

    # Get signed token from cookie
    signed_cookie_token = request.cookies.get("csrf_token")

    # Get token from request (header or form)
    request_token = None

    # Check header first (for AJAX/HTMX requests)
    request_token = request.headers.get("X-CSRF-Token")

    # If not in header, check form body
    if not request_token:
        content_type = request.headers.get("content-type", "")
        if (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            try:
                form = await request.form()
                token_value = form.get("csrf_token")
                if isinstance(token_value, str):
                    request_token = token_value
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to parse form for CSRF token: {e}"
                )

    # Validate tokens exist
    if not signed_cookie_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF cookie missing. Please refresh the page.",
        )

    if not request_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing from request.",
        )

    # Compare signed tokens
    # Both tokens should be in format: "token.signature"
    if not secrets.compare_digest(signed_cookie_token, request_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid."
        )
