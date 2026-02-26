"""
Notification Service - Domain-specific notification logic

Handles status change notifications and DRS email workflows.
Integrates with email_service.py for actual email sending.
"""

import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from sqlalchemy.orm import Session

from app.services.settings_service import SettingsService
from app.models.process import Process
from app.services.email_service import email_service
from app.services.pdf_generation_service import ensure_combined_pdfs_batch
from app.repositories.calendar_repository import get_last_batch_date
from app.utils.file_utils import file_exists

logger = logging.getLogger(__name__)

MONTHS_PT = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

BATCH_ANCHOR_DATE = SettingsService.get_batch_anchor_date()


def _format_date_pt(date_obj: date | datetime) -> str:
    """Format date as '13 de Fevereiro' in Portuguese."""
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    return f"{date_obj.day} de {MONTHS_PT[date_obj.month - 1]}"


def get_next_batch_date(db: Session) -> date:
    """
    Calculate the next scheduled batch date.

    Returns:
        Next scheduled batch date (14 days from last sent, or next scheduled from anchor)
    """
    last_sent = get_last_batch_date(db)

    today = date.today()

    if last_sent:
        last_sent_date = (
            last_sent.date() if isinstance(last_sent, datetime) else last_sent
        )
        next_batch = last_sent_date + timedelta(
            days=SettingsService.get_batch_interval_days()
        )
        if next_batch <= today:
            next_batch = today + timedelta(
                days=SettingsService.get_batch_interval_days()
                - (today - last_sent_date).days
                % SettingsService.get_batch_interval_days()
            )
        return next_batch

    anchor = BATCH_ANCHOR_DATE
    next_batch = anchor
    while next_batch <= today:
        next_batch += timedelta(days=SettingsService.get_batch_interval_days())

    return next_batch


def get_status_description_with_date(
    status: str, db: Session, process_sent_at: datetime | None = None
) -> str:
    """
    Get status description with [data] placeholder replaced.

    Args:
        status: Status key (e.g., 'completo', 'enviado')
        db: Database session for querying last batch date
        process_sent_at: The process's sent_at date (for 'enviado' status)

    Returns:
        Status description with [data] replaced by appropriate date
    """
    from app.content import STATUS_LABELS

    status_description = STATUS_LABELS.get(status, {}).get("description", "")

    if "[data]" not in status_description:
        return status_description

    if status == "enviado" and process_sent_at:
        return status_description.replace("[data]", _format_date_pt(process_sent_at))

    if status == "completo":
        next_batch = get_next_batch_date(db)
        return status_description.replace("[data]", _format_date_pt(next_batch))

    return status_description


def send_status_notification(
    process, status: str, note: Optional[str] = None, db: Session | None = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Send status update notification email for a process.

    Centralizes email notification logic for consistency across all admin routes.

    Args:
        process: Process object with patient.user.email, patient.name, protocol_number, id
        status: New status value (e.g., 'completo', 'enviado', 'correcao_solicitada')
        note: Optional status change note
        db: Optional database session (required for 'completo' status to calculate next batch date)

    Returns:
        Tuple of (success: bool, error_type: Optional[str], error_message: Optional[str])
        error_type can be: 'config', 'connection', 'template', 'delivery', or None
    """
    from app.content import STATUS_LABELS

    status_info = STATUS_LABELS.get(status, {})
    status_label = status_info.get("label", status)
    status_description = status_info.get("description", "")

    if db and "[data]" in status_description:
        status_description = get_status_description_with_date(
            status, db, getattr(process, "sent_at", None)
        )

    process_url = (
        f"{SettingsService.get_frontend_url()}/processo/{process.id}"
        if hasattr(process, "id")
        else SettingsService.get_frontend_url()
    )

    context = {
        "user_name": process.patient.name or "Paciente",
        "protocol_number": process.protocol_number,
        "status_label": status_label,
        "status_description": status_description,
        "note": note,
        "process_url": process_url,
    }

    subject = f"Atualização do seu processo {process.protocol_number} - SS-54"

    patient_email = process.patient.email
    if not patient_email:
        logger.error(f"Patient {process.patient.id} has no associated user/email")
        return False, "config", "Paciente sem email cadastrado"

    try:
        success, error_type = email_service.send_email(
            patient_email, subject, "status_update.html", context
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in send_status_notification: {e}", exc_info=True
        )
        return False, "delivery", str(e)

    if success:
        return True, None, None

    error_messages = {
        "config": "Verifique as configurações de SMTP",
        "connection": "Problema de conexão com servidor de email",
        "template": "Erro ao gerar conteúdo do email",
        "delivery": "Erro ao enviar mensagem",
    }
    error_message = (
        error_messages.get(error_type, "Falha ao enviar email")
        if error_type
        else "Falha ao enviar email"
    )
    return False, error_type, error_message


def _prepare_drs_email_data(
    results: Dict, processes: List[Process]
) -> Tuple[List[dict], List[dict], List[Process]]:
    """
    Prepare email context, attachments, and skipped processes.

    Iterates through processes once to build:
    - email_context_processes: dicts for email template
    - attachments: PDF file dicts for email
    - skipped_processes: Process objects with no valid PDFs

    Args:
        results: Dictionary mapping process_id to PDFEnsureResult
        processes: List of Process objects to process

    Returns:
        Tuple of (email_context_processes, attachments, skipped_processes)
    """
    from app.content import PROCESS_TYPE_TITLES

    email_context_processes = []
    attachments = []
    skipped_processes = []

    for process in processes:
        result = results.get(process.id)

        if not result or not result.exists:
            if result and result.skipped:
                skipped_processes.append(process)
            continue

        email_context_processes.append(
            {
                "patient_name": process.patient.name if process.patient else None,
                "type_label": PROCESS_TYPE_TITLES.get(
                    process.type.value, process.type.value
                ),
                "description": process.details or "",
            }
        )

        if result.pdf and file_exists(result.pdf.file_path):
            attachments.append(
                {
                    "path": result.pdf.file_path,
                    "filename": result.pdf.original_filename,
                }
            )

    return email_context_processes, attachments, skipped_processes


def _get_drs_email_config(db: Session, email_type: str) -> Tuple[str, str]:
    """
    Get DRS email configuration.

    Args:
        db: Database session
        email_type: Either 'renovacao' or 'solicitacao'

    Returns:
        Tuple of (to_email, email_title)
    """
    to_email = (
        SettingsService.get_drs_renovacao_email(db)
        if email_type == "renovacao"
        else SettingsService.get_drs_solicitacao_email(db)
    )

    email_title = (
        "Renovação - SS-54"
        if email_type == "renovacao"
        else "Primeira Solicitação - SS-54"
    )

    return to_email, email_title


def send_drs_notification(
    db: Session,
    email_type: str,
    processes: List[Process],
) -> Tuple[bool, Optional[str], List[Process]]:
    """
    Send notification email to DRS with PDF attachments.

    NOTE: Caller is responsible for filtering processes by request_type.

    Args:
        db: Database session
        email_type: Either 'renovacao' or 'solicitacao'
        processes: Pre-filtered list of processes to send

    Returns:
        Tuple of (success: bool, error_type: Optional[str], skipped_processes: List[Process])
    """
    if not processes:
        return False, "no_processes", []

    process_ids = [p.id for p in processes]
    results = ensure_combined_pdfs_batch(db, process_ids)

    email_context_processes, attachments, skipped_processes = _prepare_drs_email_data(
        results, processes
    )

    if not email_context_processes:
        logger.warning(
            f"No processes with valid PDFs to send (skipped {len(skipped_processes)})"
        )
        return False, "no_valid_pdfs", skipped_processes

    if skipped_processes:
        logger.info(
            f"Skipped {len(skipped_processes)} processes from DRS email: "
            f"{', '.join(p.protocol_number for p in skipped_processes)}"
        )

    to_email, email_title = _get_drs_email_config(db, email_type)

    context = {
        "email_title": email_title,
        "sent_date": datetime.now().strftime("%d/%m/%Y às %H:%M"),
        "processes": email_context_processes,
    }

    subject = email_title

    success, error_type = email_service.send_email_with_attachments(
        to=to_email,
        subject=subject,
        template_name="drs_notification.html",
        context=context,
        attachments=attachments,
    )

    if success:
        return True, None, skipped_processes
    return False, error_type, skipped_processes
