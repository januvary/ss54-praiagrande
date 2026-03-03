"""
Authentication routes for SS-54 web application.
Handles login, logout, and magic link verification.
"""

from contextlib import suppress

from typing import Optional

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    get_current_user_optional,
)
from app.dependencies.csrf import validate_csrf_token
from app.models.user import User
from app.repositories.user_repository import get_user_by_id
from app.repositories.patient_repository import get_patients_for_user
from app.services import auth_service
from app.services.rate_limit_service import (
    check_login_rate_limit,
    check_token_verification_rate_limit,
)
from app.utils.uuid_utils import ensure_uuid
from app.utils.response_utils import set_cookie
from app.utils.template_helpers import render_template

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    action: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user_optional),
):
    if user:
        if action == "new":
            redirect_url = "/novo"
        elif action == "renew":
            redirect_url = "/renovar"
        else:
            redirect_url = "/dashboard"
        return RedirectResponse(url=redirect_url, status_code=302)

    return render_template(request, "pages/login.html", {"action": action})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    email: str = Form(...),
    action: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"

    ip_allowed, ip_retry_after = check_login_rate_limit(client_ip, "ip")
    if not ip_allowed:
        ip_retry_after = ip_retry_after or 60
        return render_template(
            request,
            "pages/login.html",
            {
                "action": action,
                "error": f"Muitas tentativas. Tente novamente em {ip_retry_after // 60} minutos.",
            },
        )

    email_allowed, email_retry_after = check_login_rate_limit(email, "email")
    if not email_allowed:
        email_retry_after = email_retry_after or 60
        return render_template(
            request,
            "pages/login.html",
            {
                "action": action,
                "error": f"Muitas tentativas para este email. Tente novamente em {email_retry_after // 60} minutos.",
            },
        )

    user, is_new_user = auth_service.initiate_login(db, email, action=action)

    return render_template(
        request, "pages/check_email.html", {"email": email, "is_new_user": is_new_user}
    )


@router.get("/auth/verify", response_class=HTMLResponse)
@router.get("/verify", response_class=HTMLResponse)
async def verify_token(request: Request, db: Session = Depends(get_db)):
    existing_token = request.cookies.get("auth_token")
    if existing_token:
        user_id = auth_service.verify_jwt_token(existing_token)
        if user_id:
            with suppress(ValueError):
                user_uuid = ensure_uuid(user_id)
                user = get_user_by_id(db, user_uuid)
                if user:
                    patients = get_patients_for_user(db, user.id)
                    redirect_url = "/dashboard" if patients else "/select-patient"
                    return RedirectResponse(url=redirect_url, status_code=302)

    return render_template(
        request,
        "pages/verify_confirm.html",
        {"token": None, "action": None},  # nosec B105
    )


@router.post("/auth/confirm-login", response_class=HTMLResponse)
async def confirm_login(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    token: str = Form(...),
    action: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"

    allowed, retry_after = check_token_verification_rate_limit(client_ip)
    if not allowed:
        retry_after = retry_after or 60
        return render_template(
            request,
            "pages/verify.html",
            {
                "success": False,
                "error_message": f"Muitas tentativas. Aguarde {retry_after // 60 + 1} minuto(s).",
            },
        )

    result = auth_service.complete_login(db, token)

    if not result:
        return render_template(
            request,
            "pages/verify.html",
            {"success": False, "error_message": "Este link expirou ou já foi usado."},
        )

    user = result["user"]
    action_param = action or result.get("action")

    jwt_token = auth_service.create_jwt_token(str(user.id))

    if result["needs_patient_setup"]:
        redirect_url = "/select-patient"
    elif action_param == "new":
        redirect_url = "/novo"
    elif action_param == "renew":
        redirect_url = "/renovar"
    else:
        redirect_url = "/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=303)
    return set_cookie(response, "auth_token", jwt_token)


@router.post("/logout")
async def logout(csrf_protected: None = Depends(validate_csrf_token)):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("auth_token")
    return response
