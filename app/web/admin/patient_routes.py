"""
Admin Patient Routes - Patient listing and management
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.template_helpers import render_template
from app.repositories.patient_repository import (
    get_all_patients_paginated,
    get_patient_by_id,
)
from app.repositories.user_repository import update_user_email
from app.repositories.email_history_repository import (
    log_email_change,
    get_email_history,
)
from app.schemas.patient import PatientBrief
from app.dependencies.csrf import validate_csrf_token

router = APIRouter(prefix="/admin", tags=["Admin Patients"])


@router.get("/patients", response_class=HTMLResponse)
async def admin_patient_list(
    request: Request,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista todos os pacientes com filtragem e paginação opcionais."""

    patients, total = get_all_patients_paginated(
        db, search=search, page=page, per_page=per_page
    )

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    patient_list = []

    for patient in patients:
        patient_data = PatientBrief.model_validate(patient).model_dump()
        patient_list.append(patient_data)

    return render_template(
        request,
        "admin/patient_list.html",
        {
            "patients": patient_list,
            "search": search,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
        is_admin=True,
    )


@router.get("/patients/{patient_id}/change-email", response_class=HTMLResponse)
async def admin_patient_change_email(
    request: Request,
    patient_id: UUID,
    db: Session = Depends(get_db),
):
    """Página de alteração de email do usuário."""

    patient = get_patient_by_id(db, patient_id)

    if not patient:
        return RedirectResponse(
            url="/admin/patients?error=Paciente+não+encontrado", status_code=302
        )

    if not patient.user:
        return RedirectResponse(
            url="/admin/patients?error=Usuário+não+encontrado", status_code=302
        )

    email_history = get_email_history(db, patient.user.id)

    return render_template(
        request,
        "admin/patient_email_change.html",
        {
            "patient": patient,
            "current_email": patient.user.email,
            "email_history": email_history,
        },
        is_admin=True,
    )


@router.post("/patients/{patient_id}/change-email")
async def admin_patient_change_email_post(
    request: Request,
    patient_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    new_email: str = Form(...),
    confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    """Processa a alteração de email do usuário."""

    patient = get_patient_by_id(db, patient_id)

    if not patient or not patient.user:
        return RedirectResponse(
            url="/admin/patients?error=Paciente+ou+usuário+não+encontrado",
            status_code=302,
        )

    if confirm != "confirm":
        return RedirectResponse(
            url=f"/admin/patients/{patient_id}/change-email?error=Confirmação+não+marcada",
            status_code=302,
        )

    old_email = patient.user.email

    try:
        update_user_email(db, patient.user.id, new_email)
        log_email_change(db, patient.user.id, old_email, new_email)
        db.commit()
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin/patients/{patient_id}/change-email?error={e}",
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            url=f"/admin/patients/{patient_id}/change-email?error=Erro+ao+alterar+email",
            status_code=302,
        )

    return RedirectResponse(
        url=f"/admin/patients/{patient_id}/change-email?success=Email+alterado+com+sucesso",
        status_code=302,
    )
