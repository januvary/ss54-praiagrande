"""
Home and static page routes for SS-54 web application.
"""

from typing import Optional, Tuple

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import get_current_user_optional
from app.models.user import User
from app.models.patient import Patient
from app.utils.template_helpers import render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    auth: Optional[Tuple[User, Patient]] = Depends(get_current_user_optional),
):
    user, patient = auth or (None, None)
    return render_template(request, "pages/home.html", {}, user, patient)


@router.get("/privacidade", response_class=HTMLResponse)
async def privacy_policy(
    request: Request,
    auth: Optional[Tuple[User, Patient]] = Depends(get_current_user_optional),
):
    user, patient = auth or (None, None)
    return render_template(request, "pages/privacy.html", {}, user, patient)


@router.get("/exames", response_class=HTMLResponse)
async def exam_requirements(
    request: Request,
    auth: Optional[Tuple[User, Patient]] = Depends(get_current_user_optional),
):
    from app.content import MEDICATION_EXAM_REQUIREMENTS

    user, patient = auth or (None, None)
    return render_template(
        request,
        "pages/exam_requirements.html",
        {"medication_exam_requirements": MEDICATION_EXAM_REQUIREMENTS},
        user,
        patient,
    )


@router.get("/favicon.ico")
async def favicon():
    return RedirectResponse(
        url="/static/img/brasao_prefeitura_color.svg", status_code=302
    )
