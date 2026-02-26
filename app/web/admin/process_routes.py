"""
Admin Process Routes - Process listing, details, status, notes, bulk operations
"""

from datetime import datetime
from typing import List
from uuid import UUID
import logging

from fastapi import APIRouter, Request, Depends, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.csrf import validate_csrf_token
from app.models.process import ProcessStatus, Process
from app.schemas.process import ProcessResponse
from app.schemas.activity_log import ActivityLogResponse
from app.utils.serialization import serialize_orm_list
from app.repositories.activity_repository import get_paginated_activities
from app.utils.uuid_utils import validate_uuid
from app.utils.template_helpers import render_template
from app.utils.process_helpers import get_required_doc_types
from app.services.notification_service import send_status_notification
from app.services.activity_service import log_activity
from app.services.process_service import (
    update_process_status,
    update_process_status_by_id,
    ProcessNotFoundError,
)
from app.services.pdf_generation_service import ensure_combined_pdf
from app.repositories.process_repository import (
    get_all_processes_paginated,
    get_process_with_patient_and_documents,
    get_process_for_update,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Processes"])


def _auto_generate_pdf_if_complete(
    db: Session, process: Process, new_status: ProcessStatus
):
    """Auto-generate PDF when status changes to 'completo'.

    Args:
        db: Database session
        process: Process object
        new_status: New ProcessStatus enum value
    """
    if new_status != ProcessStatus.COMPLETO:
        return

    try:
        result = ensure_combined_pdf(db, process.id)
        if result.generated:
            logger.info(f"Auto-generated PDF for process {process.protocol_number}")
        elif result.skipped:
            logger.info(
                f"Skipped PDF generation for {process.protocol_number}: "
                f"{result.skip_reason}"
            )
    except Exception as e:
        logger.error(f"Error ensuring PDF for process {process.protocol_number}: {e}")


def _send_status_notification_email(
    process: Process,
    new_status_str: str,
    status_note: str | None,
    redirect_url: str,
    db: Session,
) -> RedirectResponse | None:
    """Send email notification for status change.

    Returns warning redirect if email fails, None otherwise.

    Args:
        process: Process object
        new_status_str: New status value as string
        status_note: Status change note
        redirect_url: URL to redirect after update
        db: Database session
    """
    if new_status_str == "enviado":
        return None

    email_success, email_error_type, email_error_msg = send_status_notification(
        process, new_status_str, status_note, db=db
    )

    if not email_success:
        separator = "&" if "?" in redirect_url else "?"
        warning_url = f"{redirect_url}{separator}email_warning=1&email_error_type={email_error_type or 'delivery'}"
        return RedirectResponse(url=warning_url, status_code=303)

    return None


def _update_process_status(
    db: Session,
    process_id: UUID,
    new_status_str: str,
    note: str,
    redirect_url: str,
    request: Request,
) -> RedirectResponse:
    """
    Shared helper for updating process status.

    Handles validation, status change, logging, email notification,
    and PDF auto-generation when status changes to 'completo'.

    Args:
        db: Database session
        process_id: Process UUID
        new_status_str: New status value as string
        note: Optional note for status change
        redirect_url: URL to redirect after successful update
        request: Request object for email context

    Returns:
        RedirectResponse to specified URL (with warning if email fails)
    """
    try:
        process = update_process_status_by_id(db, process_id, new_status_str, note)
    except ProcessNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    new_status = ProcessStatus(new_status_str)
    status_note = note.strip() if note else None

    _auto_generate_pdf_if_complete(db, process, new_status)

    warning_redirect = _send_status_notification_email(
        process, new_status_str, status_note, redirect_url, db
    )
    if warning_redirect:
        return warning_redirect

    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/processes", response_class=HTMLResponse)
async def admin_process_list(
    request: Request,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista todos os processos com filtragem e paginação opcionais."""

    processes, total = get_all_processes_paginated(
        db, status=status, search=search, page=page, per_page=per_page
    )

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    statuses = [s.value for s in ProcessStatus]

    process_list = serialize_orm_list(ProcessResponse, processes)

    return render_template(
        request,
        "admin/process_list.html",
        {
            "processes": process_list,
            "statuses": statuses,
            "current_status": status,
            "search": search,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
        is_admin=True,
    )


@router.get("/processes/{process_id}", response_class=HTMLResponse)
async def admin_process_detail(
    request: Request,
    process_id: UUID,
    activity_page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    """Visualiza detalhes do processo com documentos e atividades."""
    process = get_process_with_patient_and_documents(db, process_id)

    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    activities, activity_pagination = get_paginated_activities(
        db,
        process_id=str(process_id),
        page=activity_page,
        per_page=10,
        visibility_level="user",
    )

    process_data = ProcessResponse.model_validate(process).model_dump()
    process_data["activities"] = serialize_orm_list(ActivityLogResponse, activities)

    required_doc_types = get_required_doc_types(process)

    return render_template(
        request,
        "admin/process_detail.html",
        {
            "process": process_data,
            "all_statuses": [s.value for s in ProcessStatus],
            "activity_pagination": activity_pagination,
            "current_path": request.url.path,
            "required_doc_types": required_doc_types,
        },
        is_admin=True,
    )


@router.post("/processes/{process_id}/status")
async def admin_update_status(
    request: Request,
    process_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    status: str = Form(...),
    note: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Atualiza o status do processo."""
    return _update_process_status(
        db=db,
        process_id=process_id,
        new_status_str=status,
        note=note,
        redirect_url=f"/admin/processes/{process_id}",
        request=request,
    )


@router.post("/processes/{process_id}/quick-status")
async def admin_quick_status(
    request: Request,
    process_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    status: str = Form(...),
    note: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """
    Quick status change for process detail page with email notification.
    Redirects back to /admin/processes instead of process detail.
    """
    return _update_process_status(
        db=db,
        process_id=process_id,
        new_status_str=status,
        note=note,
        redirect_url="/admin/processes",
        request=request,
    )


@router.post("/processes/{process_id}/notes")
async def admin_add_note(
    request: Request,
    process_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    note: str = Form(...),
    is_internal: str = Form(default="false"),
    db: Session = Depends(get_db),
):
    """Adiciona uma nota ao processo."""
    process = get_process_for_update(db, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    note_with_timestamp = f"[{timestamp}] {note}"

    if is_internal == "true":
        process.admin_notes = (
            f"{process.admin_notes or ''}\n{note_with_timestamp}".lstrip()
        )
    else:
        process.notes = f"{process.notes or ''}\n{note_with_timestamp}".lstrip()

    db.flush()

    log_activity(
        db,
        process.id,
        None,
        "note_added",
        "Nota adicionada",
        {"is_internal": is_internal == "true"},
        process=process,
    )

    return RedirectResponse(url=f"/admin/processes/{process_id}", status_code=303)


@router.post("/processes/{process_id}/details")
async def admin_update_details(
    request: Request,
    process_id: UUID,
    csrf_protected: None = Depends(validate_csrf_token),
    details: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Atualiza os detalhes do processo."""
    process = get_process_for_update(db, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    process.details = details.strip()
    db.commit()

    return RedirectResponse(url=f"/admin/processes/{process_id}", status_code=303)


@router.get("/processes/{process_id}/pdf")
async def admin_process_pdf(process_id: UUID, db: Session = Depends(get_db)):
    """
    View or generate combined PDF for a process.

    Uses ensure_combined_pdf to:
    - Return existing PDF if valid (file present)
    - Regenerate PDF if file is missing (stale data)
    - Generate new PDF if no record exists
    - Return error if no valid documents exist

    Raises 400 if PDF cannot be generated (no valid documents).
    """
    process = get_process_for_update(db, process_id)

    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    result = ensure_combined_pdf(db, process.id)

    if result.exists and result.pdf:
        if result.generated:
            db.commit()

        return RedirectResponse(
            url=f"/admin/documents/{result.pdf.id}/download", status_code=302
        )

    raise HTTPException(
        status_code=400,
        detail="Não é possível gerar PDF: o processo não possui documentos válidos",
    )


@router.post("/processes/bulk-mark-sent")
async def admin_bulk_mark_sent(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    db: Session = Depends(get_db),
    process_ids: List[str] = Form(default=[]),
):
    """
    Bulk mark processes as sent (completo -> enviado).
    """

    if not process_ids:
        return RedirectResponse(url="/admin/processes", status_code=303)

    for process_id_str in process_ids:
        try:
            process_uuid = validate_uuid(process_id_str, "ID de processo")

            process = get_process_for_update(db, process_uuid)
            if not process:
                continue

            if process.status != ProcessStatus.COMPLETO:
                continue

            update_process_status(
                db,
                process,
                ProcessStatus.ENVIADO,
                extra_data={"bulk_action": True},
            )

        except Exception as e:
            logger.error(f"Error in bulk mark sent for process {process_id_str}: {e}")

    return RedirectResponse(url="/admin/processes", status_code=303)


@router.post("/processes/bulk-status")
async def admin_bulk_status(
    request: Request,
    csrf_protected: None = Depends(validate_csrf_token),
    db: Session = Depends(get_db),
    process_ids: List[str] = Form(default=[]),
    status: str = Form(...),
):
    """
    Bulk update process status.
    Accepts any valid status and sends email notifications when applicable.
    """
    if not process_ids:
        return RedirectResponse(
            url="/admin/processes?error=Nenhum processo selecionado", status_code=303
        )

    try:
        ProcessStatus(status)
    except ValueError:
        return RedirectResponse(
            url="/admin/processes?error=Status inválido", status_code=303
        )

    success_count = 0
    email_errors = 0

    for process_id_str in process_ids:
        try:
            process_uuid = validate_uuid(process_id_str, "ID de processo")

            process = update_process_status_by_id(
                db,
                process_uuid,
                status,
                note=None,
                extra_data={"bulk_action": True},
                user_id=None,
            )

            if status != "enviado":
                email_success, _, _ = send_status_notification(
                    process, status, None, db=db
                )
                if not email_success:
                    email_errors += 1

            success_count += 1

        except Exception as e:
            logger.error(f"Error in bulk status for process {process_id_str}: {e}")

    db.commit()

    redirect_url = f"/admin/processes?success={success_count} processo(s) atualizado(s)"
    if email_errors > 0:
        redirect_url += f"&error={email_errors} email(s) falharam"

    return RedirectResponse(url=redirect_url, status_code=303)
