"""
Admin Email Routes - Email preparation, sending, DRS notifications
"""

import logging
from typing import Any

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.csrf import validate_csrf_token
from app.models.process import ProcessStatus, Process
from app.models.patient import Patient
from app.utils.template_helpers import render_template
from app.utils.process_helpers import filter_by_request_type
from app.services.notification_service import (
    send_drs_notification,
)
from app.services.activity_service import log_activity
from app.services.process_service import update_process_status
from app.services.pdf_generation_service import ensure_combined_pdfs_batch
from app.repositories.process_repository import (
    get_processes_by_statuses,
)
from app.repositories.setting_repository import get_email_config
from app.content import PROCESS_TYPE_TITLES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Email"])


def _build_email_process_dict(process: Process, pdf_result: Any | None) -> dict:
    """Build process dict for email preview page."""
    combined_pdf = pdf_result.pdf if pdf_result and pdf_result.exists else None

    return {
        "id": str(process.id),
        "protocol_number": process.protocol_number,
        "type": process.type.value,
        "type_label": PROCESS_TYPE_TITLES.get(process.type.value, process.type.value),
        "request_type": process.request_type.value if process.request_type else None,
        "details": process.details or "",
        "patient": _build_patient_dict(process.patient) if process.patient else None,
        "combined_pdf": _build_pdf_dict(combined_pdf) if combined_pdf else None,
    }


def _build_patient_dict(patient: Patient) -> dict:
    """Build patient dict for email preview."""
    return {
        "id": str(patient.id),
        "name": patient.name,
        "email": patient.email,
        "phone": patient.phone,
    }


def _build_pdf_dict(pdf: Any) -> dict:
    """Build PDF dict for email preview."""
    return {
        "id": str(pdf.id),
        "filename": pdf.original_filename,
        "file_path": pdf.file_path,
        "file_size": pdf.file_size,
    }


@router.get("/preparar-emails", response_class=HTMLResponse)
async def admin_preparar_emails(request: Request, db: Session = Depends(get_db)):
    """
    Página de preparação de emails para envio ao DRS.
    Mostra preview dos emails de renovação e solicitação com tabelas e PDFs.
    """
    processes = get_processes_by_statuses(db, ["completo"])
    email_config = get_email_config(db)

    process_ids = [p.id for p in processes]
    results = ensure_combined_pdfs_batch(db, process_ids)

    renovacao_processes, solicitacao_processes = filter_by_request_type(processes)

    renovacao_dicts = [
        _build_email_process_dict(process, results.get(process.id))
        for process in renovacao_processes
    ]
    solicitacao_dicts = [
        _build_email_process_dict(process, results.get(process.id))
        for process in solicitacao_processes
    ]

    for result in results.values():
        if result and result.generated:
            db.commit()

    return render_template(
        request,
        "admin/preparar-emails.html",
        {
            "renovacao_processes": renovacao_dicts,
            "solicitacao_processes": solicitacao_dicts,
            "renovacao_email": email_config["drs_renovacao_email"],
            "solicitacao_email": email_config["drs_solicitacao_email"],
        },
        is_admin=True,
    )


@router.post("/enviar-emails", response_class=HTMLResponse)
async def admin_enviar_emails(
    request: Request,
    email_type: str = Form(...),
    db: Session = Depends(get_db),
    _: bool = Depends(validate_csrf_token),
):
    """
    Envia emails para o DRS com anexos PDF.
    """
    processes = get_processes_by_statuses(db, ["completo"])

    renovacao_processes, solicitacao_processes = filter_by_request_type(processes)
    target_processes = (
        renovacao_processes if email_type == "renovacao" else solicitacao_processes
    )

    success, error_type, skipped_processes = send_drs_notification(
        db, email_type, target_processes
    )

    if error_type == "no_processes":
        return _build_error_redirect("/admin/preparar-emails", "no_processes")

    if error_type == "no_valid_pdfs":
        return _build_error_redirect("/admin/preparar-emails", "no_valid_pdfs")

    if success:
        return _handle_email_success(
            db, target_processes, skipped_processes, email_type
        )

    logger.error(f"Failed to send DRS email: {error_type}")
    return _build_error_redirect("/admin/preparar-emails", error_type or "unknown")


def _build_error_redirect(base_url: str, error_type: str) -> RedirectResponse:
    """Build redirect with error parameter."""
    return RedirectResponse(url=f"{base_url}?error={error_type}", status_code=303)


def _handle_email_success(
    db: Session,
    target_processes: list[Process],
    skipped_processes: list[Process],
    email_type: str,
) -> RedirectResponse:
    """Handle successful email sending: update statuses and log skipped."""
    included_processes = [p for p in target_processes if p not in skipped_processes]

    _update_included_process_statuses(db, included_processes)
    _log_skipped_processes(db, skipped_processes)

    db.commit()
    logger.info(
        f"DRS email sent: {email_type} with {len(included_processes)} process(es)"
    )

    return RedirectResponse(
        url=f"/admin/preparar-emails?success={email_type}",
        status_code=303,
    )


def _update_included_process_statuses(db: Session, processes: list[Process]):
    """Update statuses for processes successfully included in email."""
    for process in processes:
        update_process_status(
            db,
            process,
            ProcessStatus.ENVIADO,
            extra_data={"drs_email": True},
        )


def _log_skipped_processes(db: Session, processes: list[Process]):
    """Log activity for processes skipped from email."""
    for process in processes:
        log_activity(
            db,
            process.id,
            None,
            "email_skipped",
            "Processo não incluído no email DRS",
            {"reason": "no_valid_documents"},
            process=process,
        )
