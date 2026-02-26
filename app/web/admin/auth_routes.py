"""
Admin Authentication Routes - Login/logout functionality
"""

import logging

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.csrf import validate_csrf_token
from app.utils.security_utils import sanitize_redirect
from app.utils.ip_utils import get_client_ip
from app.utils.template_config import templates
from app.services.rate_limit_service import check_admin_login_rate_limit
from app.middleware.admin_auth import (
    set_admin_session_cookie,
    clear_admin_session_cookie,
    verify_admin_session_token,
    ADMIN_SESSION_COOKIE_NAME,
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Auth"])


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """
    Admin login page.

    If already logged in, redirect to admin dashboard.
    If password not configured, redirect directly to dashboard.
    """
    if not settings.ADMIN_PASSWORD_HASH:
        return RedirectResponse(url="/admin", status_code=302)

    session_token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)
    if session_token and verify_admin_session_token(session_token):
        return RedirectResponse(url="/admin", status_code=302)

    csrf_token = request.cookies.get("csrf_token", "")
    next_url = sanitize_redirect(request.query_params.get("next", "/admin"), "/admin")

    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {
            "csrf_token": csrf_token,
            "next_url": next_url,
            "error": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def admin_login_submit(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    password: str = Form(...),
    next: str = Form("/admin"),
):
    """
    Process admin login form submission.

    Rate limited: 5 attempts per IP per 15 minutes.
    """
    import bcrypt

    safe_next = sanitize_redirect(next, "/admin")

    client_ip = get_client_ip(request)
    allowed, retry_after = check_admin_login_rate_limit(client_ip)

    if not allowed:
        csrf_token = request.cookies.get("csrf_token", "")
        minutes = (retry_after // 60 + 1) if retry_after else 1
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {
                "csrf_token": csrf_token,
                "next_url": safe_next,
                "error": f"Muitas tentativas. Tente novamente em {minutes} minuto(s).",
            },
            status_code=429,
        )

    try:
        if settings.ADMIN_PASSWORD_HASH and bcrypt.checkpw(
            password.encode(), settings.ADMIN_PASSWORD_HASH.encode()
        ):
            response = RedirectResponse(url=safe_next, status_code=302)
            return set_admin_session_cookie(response)
    except Exception as e:
        logger.error(f"Error verifying admin password: {e}")

    csrf_token = request.cookies.get("csrf_token", "")
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {
            "csrf_token": csrf_token,
            "next_url": safe_next,
            "error": "Senha incorreta.",
        },
        status_code=401,
    )


@router.post("/logout")
async def admin_logout(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
):
    """Clear admin session and redirect to login page."""
    response = RedirectResponse(url="/admin/login", status_code=302)
    return clear_admin_session_cookie(response)
