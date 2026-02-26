"""
Dashboard routes for SS-54 web application.
"""

from typing import Tuple

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user_cookie
from app.models.user import User
from app.models.patient import Patient
from app.repositories.process_repository import get_processes_for_patient
from app.schemas.process import ProcessResponse
from app.utils.serialization import serialize_orm_list
from app.utils.template_helpers import render_template

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth

    processes = get_processes_for_patient(db, current_patient.id)

    process_list = serialize_orm_list(ProcessResponse, processes)

    return render_template(
        request,
        "pages/dashboard.html",
        {"processes": process_list, "current_patient": current_patient},
        current_user,
        current_patient,
    )
