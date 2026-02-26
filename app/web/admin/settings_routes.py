"""
Admin Settings Routes - Settings management
"""

import logging

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.csrf import validate_csrf_token
from app.utils.template_helpers import render_template
from app.repositories.setting_repository import set_setting, get_email_config
from app.services.settings_service import SettingsService
from app.services.storage_service import get_storage_checker
from app.scheduler import reload_scheduler_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Settings"])


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, db: Session = Depends(get_db)):
    """Display and edit email and scheduler settings."""
    email_config = get_email_config(db)
    scheduler_config = SettingsService.get_all_scheduler_config(db)

    app_config = {
        "app_name": SettingsService.get_app_name(db),
        "frontend_url": SettingsService.get_frontend_url(db),
        "allowed_origins": SettingsService.get_allowed_origins(db),
    }

    data_retention_config = {
        "data_retention_years": SettingsService.get_data_retention_years(db),
        "data_retention_enabled": SettingsService.get_data_retention_enabled(db),
    }

    context = email_config | scheduler_config | app_config | data_retention_config

    return render_template(
        request,
        "admin/settings.html",
        context,
        is_admin=True,
    )


@router.post("/settings", response_class=HTMLResponse)
async def admin_settings_save(
    request: Request,
    drs_renovacao_email: str = Form(...),
    drs_solicitacao_email: str = Form(...),
    emails_from_email: str = Form(...),
    emails_from_name: str = Form(...),
    scheduler_enabled: bool = Form(False),
    scheduler_timezone: str = Form("America/Sao_Paulo"),
    batch_send_hour: int = Form(9, ge=0, le=23),
    batch_send_enabled: bool = Form(False),
    drs_followup_hour: int = Form(10, ge=0, le=23),
    drs_followup_enabled: bool = Form(False),
    auto_expire_hour: int = Form(8, ge=0, le=23),
    auto_expire_enabled: bool = Form(False),
    batch_interval_days: int = Form(14, ge=1, le=365),
    drs_deadline_days: str = Form("30,60"),
    auth_expiry_days: int = Form(180, ge=1, le=730),
    auth_expiry_warning_days: int = Form(30, ge=1, le=180),
    nutricao_expiry_days: int = Form(120, ge=1, le=730),
    app_name: str = Form("SS-54"),
    frontend_url: str = Form("http://localhost:8080"),
    allowed_origins: str = Form("http://localhost:8080"),
    data_retention_years: int = Form(5, ge=1, le=50),
    data_retention_enabled: bool = Form(False),
    db: Session = Depends(get_db),
    _: bool = Depends(validate_csrf_token),
):
    """
    Save email and scheduler settings to database.
    """
    from pydantic import EmailStr, TypeAdapter, ValidationError

    try:
        TypeAdapter(EmailStr).validate_python(drs_renovacao_email)
        TypeAdapter(EmailStr).validate_python(drs_solicitacao_email)
        TypeAdapter(EmailStr).validate_python(emails_from_email)
    except ValidationError:
        email_config = get_email_config(db)
        return render_template(
            request,
            "admin/settings.html",
            email_config
            | {
                "error": "Formato de email inválido. Por favor, verifique os endereços informados."
            },
            is_admin=True,
        )

    set_setting(db, "DRS_RENOVACAO_EMAIL", drs_renovacao_email)
    set_setting(db, "DRS_SOLICITACAO_EMAIL", drs_solicitacao_email)
    set_setting(db, "EMAILS_FROM_EMAIL", emails_from_email)
    set_setting(db, "EMAILS_FROM_NAME", emails_from_name)

    set_setting(db, "SCHEDULER_ENABLED", "true" if scheduler_enabled else "false")
    set_setting(db, "SCHEDULER_TIMEZONE", scheduler_timezone)
    set_setting(db, "BATCH_SEND_HOUR", str(batch_send_hour))
    set_setting(db, "BATCH_SEND_ENABLED", "true" if batch_send_enabled else "false")
    set_setting(db, "DRS_FOLLOWUP_HOUR", str(drs_followup_hour))
    set_setting(db, "DRS_FOLLOWUP_ENABLED", "true" if drs_followup_enabled else "false")
    set_setting(db, "AUTO_EXPIRE_HOUR", str(auto_expire_hour))
    set_setting(db, "AUTO_EXPIRE_ENABLED", "true" if auto_expire_enabled else "false")
    set_setting(db, "BATCH_INTERVAL_DAYS", str(batch_interval_days))
    set_setting(db, "DRS_DEADLINE_DAYS", drs_deadline_days)
    set_setting(db, "AUTH_EXPIRY_DAYS", str(auth_expiry_days))
    set_setting(db, "AUTH_EXPIRY_WARNING_DAYS", str(auth_expiry_warning_days))
    set_setting(db, "NUTRICAO_EXPIRY_DAYS", str(nutricao_expiry_days))

    set_setting(db, "APP_NAME", app_name)
    set_setting(db, "FRONTEND_URL", frontend_url)
    set_setting(db, "ALLOWED_ORIGINS", allowed_origins)

    set_setting(db, "DATA_RETENTION_YEARS", str(data_retention_years))
    set_setting(
        db, "DATA_RETENTION_ENABLED", "true" if data_retention_enabled else "false"
    )

    reload_scheduler_settings()

    email_config = get_email_config(db)
    scheduler_config = SettingsService.get_all_scheduler_config(db)
    app_config = {
        "app_name": SettingsService.get_app_name(db),
        "frontend_url": SettingsService.get_frontend_url(db),
        "allowed_origins": SettingsService.get_allowed_origins(db),
    }
    data_retention_config = {
        "data_retention_years": SettingsService.get_data_retention_years(db),
        "data_retention_enabled": SettingsService.get_data_retention_enabled(db),
    }

    return render_template(
        request,
        "admin/settings.html",
        email_config
        | scheduler_config
        | app_config
        | data_retention_config
        | {"success": "Configurações salvas com sucesso! O agendador foi atualizado."},
        is_admin=True,
    )


@router.get("/api/storage-health", response_class=JSONResponse)
async def get_storage_health():
    """
    Get current storage health status.

    Returns storage metrics including:
    - Availability
    - Mount type (nfs, local, etc.)
    - Disk usage
    - Read/write latency
    """
    checker = get_storage_checker()
    if checker is None:
        return JSONResponse(
            status_code=503,
            content={
                "available": False,
                "error": "Storage health checker not initialized",
            },
        )

    health = checker.check(force=True)
    return JSONResponse(content=health.to_dict())
