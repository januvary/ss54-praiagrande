"""
Patient management routes for SS-54 web application.
Handles patient selection and creation.
"""

from uuid import UUID

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user_cookie_no_registration_check
from app.models.user import User
from app.repositories.patient_repository import (
    get_patients_for_user,
    get_patient_for_owner,
)
from app.services.patient_service import create_patient_profile
from app.utils.uuid_utils import validate_uuid
from app.utils.validators import validate_name, validate_phone
from app.utils.response_utils import set_cookie
from app.utils.date_utils import parse_brazilian_date
from app.utils.template_helpers import render_template

router = APIRouter()


@router.get("/select-patient", response_class=HTMLResponse)
async def select_patient_page(
    request: Request,
    current_user: User = Depends(get_current_user_cookie_no_registration_check),
    db: Session = Depends(get_db),
):
    patients = get_patients_for_user(db, current_user.id)

    return render_template(
        request, "pages/select_patient.html", {"patients": patients}, current_user
    )


@router.post("/create-patient", response_class=HTMLResponse)
async def create_patient_post(
    request: Request,
    current_user: User = Depends(get_current_user_cookie_no_registration_check),
    db: Session = Depends(get_db),
    name: str = Form(...),
    phone: str = Form(None),
    date_of_birth: str = Form(None),
):
    name_clean, name_errors = validate_name(name)
    if name_errors:
        return render_template(
            request,
            "pages/select_patient.html",
            {
                "errors": name_errors,
                "name": name,
                "phone": phone,
                "date_of_birth": date_of_birth,
            },
            current_user,
        )

    dob, dob_errors = parse_brazilian_date(date_of_birth)
    if dob_errors:
        return render_template(
            request,
            "pages/select_patient.html",
            {
                "errors": dob_errors,
                "name": name,
                "phone": phone,
                "date_of_birth": date_of_birth,
            },
            current_user,
        )

    if phone:
        phone_clean, phone_errors = validate_phone(phone)
        if phone_errors:
            return render_template(
                request,
                "pages/select_patient.html",
                {
                    "errors": phone_errors,
                    "name": name,
                    "phone": phone,
                    "date_of_birth": date_of_birth,
                },
                current_user,
            )

        if not current_user.phone:
            current_user.phone = phone_clean
            db.flush()

    patient = create_patient_profile(
        db=db, user_id=UUID(str(current_user.id)), name=name_clean, date_of_birth=dob
    )

    response = RedirectResponse(url="/dashboard", status_code=303)
    response = set_cookie(response, "selected_patient_id", str(patient.id))
    return response


@router.post("/select-patient", response_class=HTMLResponse)
async def select_patient_post(
    request: Request,
    current_user: User = Depends(get_current_user_cookie_no_registration_check),
    db: Session = Depends(get_db),
    patient_id: str = Form(...),
):
    patient_uuid = validate_uuid(patient_id, "ID de paciente")

    patient = get_patient_for_owner(db, patient_uuid, current_user.id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    response = RedirectResponse(url="/dashboard", status_code=303)
    response = set_cookie(response, "selected_patient_id", str(patient.id))
    return response
