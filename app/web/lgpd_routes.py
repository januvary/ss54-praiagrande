"""
LGPD data subject rights routes for SS-54 web application.
Handles user data access, export, and correction (LGPD Art. 18).
"""

from typing import Tuple

from fastapi import APIRouter, Request, Depends, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user_cookie
from app.dependencies.csrf import validate_csrf_token
from app.models.user import User
from app.models.patient import Patient
from app.repositories.activity_repository import get_paginated_activities
from app.repositories.patient_repository import get_patient_for_owner
from app.services.data_subject_service import (
    get_user_data_report,
    can_delete_user_account,
    export_user_data_zip,
    update_user_phone,
    update_patient_info,
)
from app.utils.uuid_utils import validate_uuid
from app.utils.date_utils import parse_brazilian_date
from app.utils.template_helpers import render_template
from app.utils.serialization import serialize_orm_list
from app.schemas.activity_log import ActivityLogResponse

router = APIRouter()


@router.get("/meus-dados", response_class=HTMLResponse)
async def my_data_page(
    request: Request,
    activity_page: int = Query(1, ge=1),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth

    data_report = (
        get_user_data_report(db, current_user.id, include_activities=False) or {}
    )

    deletion_check = can_delete_user_account(db, current_user.id)

    activities, activity_pagination = get_paginated_activities(
        db,
        user_id=str(current_user.id),
        page=activity_page,
        per_page=10,
        visibility_level="user",
    )

    activities_data = serialize_orm_list(ActivityLogResponse, activities)

    data_report["recent_activities"] = activities_data

    return render_template(
        request,
        "pages/my_data.html",
        {
            "data_report": data_report,
            "deletion_check": deletion_check,
            "activity_pagination": activity_pagination,
        },
        current_user,
        current_patient,
    )


@router.get("/meus-dados/export")
async def export_my_data(
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    from fastapi.responses import Response

    current_user, _ = auth

    zip_data = export_user_data_zip(db, current_user.id)

    if not zip_data:
        raise HTTPException(status_code=404, detail="Dados não encontrados")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"ss54-dados-{current_user.id}-{timestamp}.zip"

    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/meus-dados/atualizar-telefone", response_class=HTMLResponse)
async def update_phone(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
    phone: str = Form(...),
):
    current_user, current_patient = auth

    try:
        update_user_phone(db, current_user, phone)
        return RedirectResponse(
            url="/meus-dados?success=telefone_atualizado", status_code=303
        )
    except ValueError as e:
        data_report = get_user_data_report(db, current_user.id)
        deletion_check = can_delete_user_account(db, current_user.id)
        return render_template(
            request,
            "pages/my_data.html",
            {
                "data_report": data_report,
                "deletion_check": deletion_check,
                "error": str(e),
            },
            current_user,
            current_patient,
        )


@router.post("/meus-dados/atualizar-paciente", response_class=HTMLResponse)
async def update_patient(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
    patient_id: str = Form(...),
    name: str = Form(None),
    date_of_birth: str = Form(None),
):
    current_user, current_patient = auth

    patient_uuid = validate_uuid(patient_id, "ID de paciente")
    patient = get_patient_for_owner(db, patient_uuid, current_user.id)

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    try:
        dob, dob_errors = parse_brazilian_date(date_of_birth)
        if dob_errors:
            raise ValueError(dob_errors[0])

        update_patient_info(
            db=db, patient=patient, name=name or None, date_of_birth=dob
        )

        return RedirectResponse(
            url="/meus-dados?success=paciente_atualizado", status_code=303
        )

    except ValueError as e:
        data_report = get_user_data_report(db, current_user.id)
        deletion_check = can_delete_user_account(db, current_user.id)
        return render_template(
            request,
            "pages/my_data.html",
            {
                "data_report": data_report,
                "deletion_check": deletion_check,
                "error": str(e),
            },
            current_user,
            current_patient,
        )
