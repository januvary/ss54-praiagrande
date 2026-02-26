"""
Process routes for SS-54 web application.
Handles process creation, renovation, and detail views.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, cast, Any
from uuid import UUID

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user_cookie
from app.dependencies.csrf import validate_csrf_token
from app.models.user import User
from app.models.patient import Patient
from app.models.process import Process, ProcessType, ProcessStatus, RequestType
from app.repositories.activity_repository import get_paginated_activities
from app.repositories.process_repository import (
    get_process_with_documents,
    get_process_for_owner_update_or_404,
    get_expired_processes_for_patient,
)
from app.services.process_service import (
    create_process,
    transition_to_em_revisao_if_applicable,
)
from app.services.activity_service import log_activity
from app.services.document_service import (
    create_document,
    map_document_id_to_type,
)
from app.services.file_service import FileValidationError
from app.services.notification_service import get_status_description_with_date
from app.utils.uuid_utils import ensure_uuid, validate_uuid
from app.utils.process_helpers import get_required_doc_types, get_document_requirements
from app.schemas.process import ProcessResponse
from app.utils.validators import (
    validate_process_type,
    validate_process_expired,
)
from app.utils.template_helpers import render_template
from app.utils.serialization import serialize_orm_list
from app.schemas.activity_log import ActivityLogResponse

from app.content import PROCESS_TYPES, PROCESS_TYPE_TITLES

router = APIRouter()


@dataclass
class ProcessCreationContext:
    db: Session
    patient_id: str
    user_id: str
    process_type_str: str
    form_data: Any
    is_renovation: bool = False
    original_process_id: Optional[str] = None
    protocol_suffix: Optional[str] = None


def _upload_files_for_document_type(
    db: Session,
    process_id: UUID,
    doc_id: int,
    doc_req: dict,
    files: list,
) -> tuple[int, list[str]]:
    count = 0
    errors = []

    for file in files:
        if getattr(file, "filename", None):
            try:
                doc_type = map_document_id_to_type(doc_id)
                from fastapi import UploadFile

                create_document(db, process_id, doc_type, cast(UploadFile, file))
                count += 1
            except FileValidationError as e:
                errors.append(f"{doc_req['title']}: {e}")

    return count, errors


def _upload_documents_by_requirements(
    db: Session,
    process_id: UUID,
    documents_required: list,
    form_data: Any,
    is_renovation: bool,
) -> tuple[int, list[str]]:
    uploaded_count = 0
    errors = []

    for doc_req in documents_required:
        doc_id = doc_req["id"]

        if is_renovation and doc_id == 6:
            continue

        field_name = f"doc_{doc_id}"
        files = form_data.getlist(field_name)

        if files:
            count, doc_errors = _upload_files_for_document_type(
                db, process_id, doc_id, doc_req, files
            )
            uploaded_count += count
            errors.extend(doc_errors)

            if count == 0 and doc_req.get("required"):
                errors.append(f"{doc_req['title']}: Arquivo obrigatório não enviado")
        elif doc_req.get("required"):
            errors.append(f"{doc_req['title']}: Arquivo obrigatório não enviado")

    return uploaded_count, errors


def _handle_process_creation_with_docs(
    ctx: ProcessCreationContext,
) -> tuple[Optional[Process], list[str], int]:
    type_mapping = {
        "medicamento": ProcessType.MEDICAMENTO,
        "nutricao": ProcessType.NUTRICAO,
        "bomba": ProcessType.BOMBA,
    }
    process_type_enum = type_mapping.get(ctx.process_type_str, ProcessType.OUTRO)

    request_type = (
        RequestType.RENOVACAO if ctx.is_renovation else RequestType.PRIMEIRA_SOLICITACAO
    )

    original_process_id_uuid = (
        UUID(ctx.original_process_id) if ctx.original_process_id else None
    )

    try:
        new_process = create_process(
            db=ctx.db,
            patient_id=ctx.patient_id,
            process_type=process_type_enum,
            status=ProcessStatus.RASCUNHO,
            request_type=request_type,
            original_process_id=original_process_id_uuid,
            protocol_suffix=ctx.protocol_suffix,
        )
    except Exception:
        return None, ["Erro ao gerar número de protocolo. Tente novamente."], 0

    log_activity(
        ctx.db,
        new_process.id,
        ensure_uuid(ctx.user_id),
        "process_created",
        "Processo criado",
        process=new_process,
    )

    documents_required = get_document_requirements(
        ctx.process_type_str, ctx.is_renovation
    )

    uploaded_count, errors = _upload_documents_by_requirements(
        ctx.db, new_process.id, documents_required, ctx.form_data, ctx.is_renovation
    )

    if uploaded_count > 0:
        transition_to_em_revisao_if_applicable(
            ctx.db, new_process.id, UUID(ctx.user_id)
        )

    return new_process, errors, uploaded_count


def _handle_renovation_request(
    db: Session,
    patient_id: str,
    user_id: str,
    process_type: str,
    original_process_id: Optional[str],
    form_data,
) -> tuple[Optional[Process], list[str], int, Optional[Process]]:
    original_process = None

    if original_process_id:
        process_uuid = validate_uuid(original_process_id, "ID de processo")
        original_process = get_process_with_documents(db, process_uuid)

        if not original_process or original_process.patient_id != patient_id:
            return None, ["Processo original não encontrado"], 0, None

        if original_process.status != ProcessStatus.EXPIRADO:
            return None, ["Apenas processos expirados podem ser renovados"], 0, None

    new_process, errors, uploaded_count = _handle_process_creation_with_docs(
        ProcessCreationContext(
            db=db,
            patient_id=patient_id,
            user_id=user_id,
            process_type_str=process_type,
            form_data=form_data,
            is_renovation=True,
            original_process_id=(
                str(original_process_id) if original_process_id else None
            ),
            protocol_suffix="R",
        )
    )

    if original_process and new_process:
        original_process.was_renewed = True
        log_activity(
            db,
            original_process.id,
            ensure_uuid(user_id),
            "process_renewed",
            f"Processo renovado: {new_process.protocol_number}",
            process=original_process,
        )

    return new_process, errors, uploaded_count, original_process


def _render_upload_error(
    request: Request,
    process_type: str,
    errors: list[str],
    user: User,
    patient: Patient,
    is_renovation: bool = False,
    original_process_id: Optional[str] = None,
) -> HTMLResponse:
    type_info = PROCESS_TYPES[process_type]
    documents = get_document_requirements(process_type, is_renovation)
    template = "pages/renovar_upload.html" if is_renovation else "pages/upload.html"
    context = {
        "type_key": process_type,
        "process_type": type_info,
        "documents": documents,
        "errors": errors or ["Erro ao gerar número de protocolo. Tente novamente."],
    }
    if is_renovation and original_process_id:
        context["original_process_id"] = original_process_id
    return render_template(request, template, context, user, patient)


def _success_redirect(protocol_number: str, process_id: str) -> RedirectResponse:
    from urllib.parse import urlencode

    params = urlencode(
        {
            "protocol": protocol_number,
            "pid": process_id,
        }
    )

    url = f"/sucesso?{params}"
    response = RedirectResponse(url=url, status_code=303)
    response.headers["HX-Redirect"] = url
    return response


@router.get("/novo", response_class=HTMLResponse)
async def select_type(
    request: Request, auth: Tuple[User, Patient] = Depends(get_current_user_cookie)
):
    current_user, current_patient = auth
    return render_template(
        request, "pages/select_type.html", {}, current_user, current_patient
    )


@router.get("/renovar", response_class=HTMLResponse)
async def renovar_select_type(
    request: Request,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth
    expired_processes = get_expired_processes_for_patient(db, current_patient.id)

    expired_list = [
        {
            "id": str(p.id),
            "protocol_number": p.protocol_number,
            "type": p.type.value,
            "created_at": p.created_at.strftime("%d/%m/%Y"),
        }
        for p in expired_processes
    ]

    return render_template(
        request,
        "pages/renovar_select_type.html",
        {
            "expired_processes": expired_list,
            "process_types": PROCESS_TYPES,
            "process_type_titles": PROCESS_TYPE_TITLES,
        },
        current_user,
        current_patient,
    )


@router.get("/renovar/{process_type}", response_class=HTMLResponse)
async def renovar_novo_upload(
    request: Request,
    process_type: str,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
):
    current_user, current_patient = auth
    validate_process_type(process_type)

    type_info = PROCESS_TYPES[process_type]
    documents = get_document_requirements(process_type, is_renovation=True)

    return render_template(
        request,
        "pages/renovar_upload.html",
        {
            "type_key": process_type,
            "process_type": type_info,
            "documents": documents,
            "original_process_id": None,
        },
        current_user,
        current_patient,
    )


@router.post("/renovar/{process_type}", response_class=HTMLResponse)
async def create_standalone_renovation_process(
    request: Request,
    process_type: str,
    csrf_protected: None = Depends(validate_csrf_token),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth
    validate_process_type(process_type)

    form = await request.form()

    new_process, errors, uploaded_count, _ = _handle_renovation_request(
        db=db,
        patient_id=str(current_patient.id),
        user_id=str(current_user.id),
        process_type=process_type,
        original_process_id=None,
        form_data=form,
    )

    if not new_process or errors:
        db.rollback()
        return _render_upload_error(
            request,
            process_type,
            errors,
            current_user,
            current_patient,
            is_renovation=True,
            original_process_id=None,
        )

    return _success_redirect(new_process.protocol_number, str(new_process.id))


@router.get("/novo/{process_type}", response_class=HTMLResponse)
async def upload_page(
    request: Request,
    process_type: str,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
):
    current_user, current_patient = auth
    validate_process_type(process_type)

    type_info = PROCESS_TYPES[process_type]
    documents = get_document_requirements(process_type, is_renovation=False)

    return render_template(
        request,
        "pages/upload.html",
        {"type_key": process_type, "process_type": type_info, "documents": documents},
        current_user,
        current_patient,
    )


@router.post("/novo/{process_type}", response_class=HTMLResponse)
async def create_process_route(
    request: Request,
    process_type: str,
    csrf_protected: None = Depends(validate_csrf_token),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth
    validate_process_type(process_type)

    form = await request.form()

    new_process, errors, uploaded_count = _handle_process_creation_with_docs(
        ProcessCreationContext(
            db=db,
            patient_id=str(current_patient.id),
            user_id=str(current_user.id),
            process_type_str=process_type,
            form_data=form,
        )
    )

    if not new_process or errors:
        db.rollback()
        return _render_upload_error(
            request,
            process_type,
            errors,
            current_user,
            current_patient,
            is_renovation=False,
        )

    return _success_redirect(new_process.protocol_number, str(new_process.id))


@router.get("/sucesso", response_class=HTMLResponse)
async def success_page(
    request: Request,
    protocol: Optional[str] = None,
    pid: Optional[str] = None,
    process_id: Optional[str] = None,
    id: Optional[str] = None,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
):
    current_user, current_patient = auth

    id_to_validate = pid or process_id or id

    if not protocol:
        protocol = request.query_params.get("protocol", "")
    if not id_to_validate:
        id_to_validate = (
            request.query_params.get("pid")
            or request.query_params.get("process_id")
            or request.query_params.get("id")
        )

    valid_process_id = None
    if id_to_validate:
        try:
            from uuid import UUID

            UUID(str(id_to_validate))
            valid_process_id = str(id_to_validate)
        except (ValueError, TypeError):
            valid_process_id = None

    return render_template(
        request,
        "pages/success.html",
        {
            "protocol": protocol or "",
            "email": current_user.email,
            "process_id": valid_process_id,
        },
        current_user,
        current_patient,
    )


@router.get("/processo/{process_id}", response_class=HTMLResponse)
async def process_detail(
    request: Request,
    process_id: UUID,
    activity_page: int = Query(1, ge=1),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth

    process = get_process_for_owner_update_or_404(db, process_id, current_patient.id)

    activities, activity_pagination = get_paginated_activities(
        db,
        process_id=str(process_id),
        page=activity_page,
        per_page=5,
        visibility_level="user",
    )

    process_data = ProcessResponse.model_validate(process).model_dump()

    activities_data = serialize_orm_list(ActivityLogResponse, activities)

    process_data["activities"] = activities_data

    can_renew = process.status == ProcessStatus.EXPIRADO

    required_doc_types = get_required_doc_types(process)

    status_description = get_status_description_with_date(
        process.status.value, db, process.sent_at
    )

    return render_template(
        request,
        "pages/process_detail.html",
        {
            "process": process_data,
            "activity_pagination": activity_pagination,
            "current_path": request.url.path,
            "can_renew": can_renew,
            "required_doc_types": required_doc_types,
            "status_description": status_description,
        },
        current_user,
        current_patient,
    )


@router.get("/renovar/{process_id}", response_class=HTMLResponse)
async def renovar_select_type_for_process(
    request: Request,
    process_id: UUID,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth

    process = get_process_for_owner_update_or_404(db, process_id, current_patient.id)

    validate_process_expired(process)

    return render_template(
        request,
        "pages/renovar_select_type.html",
        {},
        current_user,
        current_patient,
    )


@router.get("/renovar/{process_id}/{process_type}", response_class=HTMLResponse)
async def renovar_upload(
    request: Request,
    process_id: UUID,
    process_type: str,
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth

    original_process = get_process_for_owner_update_or_404(
        db, process_id, current_patient.id
    )

    validate_process_expired(original_process)
    validate_process_type(process_type)

    type_info = PROCESS_TYPES[process_type]
    documents = get_document_requirements(process_type, is_renovation=True)

    return render_template(
        request,
        "pages/renovar_upload.html",
        {
            "type_key": process_type,
            "process_type": type_info,
            "documents": documents,
            "original_process_id": str(process_id),
        },
        current_user,
        current_patient,
    )


@router.post("/renovar/{process_id}/{process_type}", response_class=HTMLResponse)
async def create_renovation_route(
    request: Request,
    process_id: UUID,
    process_type: str,
    csrf_protected: None = Depends(validate_csrf_token),
    auth: Tuple[User, Patient] = Depends(get_current_user_cookie),
    db: Session = Depends(get_db),
):
    current_user, current_patient = auth
    validate_process_type(process_type)

    form = await request.form()

    new_process, errors, uploaded_count, _ = _handle_renovation_request(
        db=db,
        patient_id=str(current_patient.id),
        user_id=str(current_user.id),
        process_type=process_type,
        original_process_id=str(process_id),
        form_data=form,
    )

    if not new_process or errors:
        db.rollback()
        return _render_upload_error(
            request,
            process_type,
            errors,
            current_user,
            current_patient,
            is_renovation=True,
            original_process_id=str(process_id),
        )

    return _success_redirect(new_process.protocol_number, str(new_process.id))
