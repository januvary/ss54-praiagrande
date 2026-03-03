"""
Scheduler Jobs - Automated task implementations
"""

import logging
from datetime import datetime, date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models.process import Process, ProcessStatus, ProcessType
from app.models.batch_schedule import BatchSchedule, EmailType
from app.models.patient import Patient
from app.utils.process_helpers import filter_by_request_type
from app.services.notification_service import (
    send_drs_notification,
    send_status_notification,
)
from app.services.activity_service import log_activity
from app.services.process_service import update_process_status
from app.services.email_service import email_service
from app.content import PROCESS_TYPE_TITLES
from app.services.settings_service import SettingsService
from app.repositories.calendar_repository import get_last_batch_date

logger = logging.getLogger(__name__)

BATCH_ANCHOR_DATE = SettingsService.get_batch_anchor_date()


def _is_batch_day(db: Session, today: date) -> bool:
    """
    Determine if today is a scheduled batch day.

    Args:
        db: Database session
        today: Today's date

    Returns:
        True if today is a batch day, False otherwise
    """
    last_sent = get_last_batch_date(db)

    if last_sent:
        last_sent_date = (
            last_sent.date() if isinstance(last_sent, datetime) else last_sent
        )
        days_since_last = (today - last_sent_date).days
        return days_since_last >= SettingsService.get_batch_interval_days()
    else:
        days_since_anchor = (today - BATCH_ANCHOR_DATE).days
        return (
            days_since_anchor >= 0
            and days_since_anchor % SettingsService.get_batch_interval_days() == 0
        )


def _create_batch_schedule(
    db: Session, email_type: EmailType, batch_date: date, count: int
) -> BatchSchedule:
    """
    Create a batch schedule record.

    Args:
        db: Database session
        email_type: Email type enum
        batch_date: Date of batch
        count: Number of processes in batch

    Returns:
        BatchSchedule object (not yet added to session)
    """
    return BatchSchedule(
        email_type=email_type,
        scheduled_date=batch_date,
        sent_at=datetime.now(),
        process_count=count,
    )


def _update_batch_processes(
    db: Session,
    included: list[Process],
    email_type: EmailType,
    batch_date: date,
) -> None:
    """
    Update process status to ENVIADO and create batch schedule record.

    Args:
        db: Database session
        included: List of processes successfully sent
        email_type: Email type enum
        batch_date: Date of batch
    """
    for process in included:
        update_process_status(
            db,
            process,
            ProcessStatus.ENVIADO,
            extra_data={
                "auto_batch": True,
                "batch_date": batch_date.isoformat(),
            },
        )

    batch_schedule = _create_batch_schedule(db, email_type, batch_date, len(included))
    db.add(batch_schedule)


def job_auto_send_batches():
    """
    Auto-send batch emails on scheduled dates.

    Checks if today is a predicted batch date (14 days from last sent_at).
    If yes, sends all 'completo' processes to DRS.
    """
    logger.info("Running job: auto_send_batches")

    db = SessionLocal()
    try:
        today = date.today()

        if not _is_batch_day(db, today):
            logger.info("Not a batch day")
            return

        processes = (
            db.query(Process)
            .options(joinedload(Process.patient).joinedload(Patient.user))
            .filter(Process.status == ProcessStatus.COMPLETO)
            .all()
        )

        if not processes:
            logger.info("No processes with status 'completo' to send")
            return

        renovacao_processes, solicitacao_processes = filter_by_request_type(processes)

        for email_type_str, target_processes in (
            ("renovacao", renovacao_processes),
            ("solicitacao", solicitacao_processes),
        ):
            if not target_processes:
                continue

            email_type = (
                EmailType.RENOVACAO
                if email_type_str == "renovacao"
                else EmailType.SOLICITACAO
            )

            success, error_type, skipped = send_drs_notification(
                db, email_type_str, target_processes
            )

            if success:
                included = [p for p in target_processes if p not in skipped]

                _update_batch_processes(db, included, email_type, today)

                db.commit()
                logger.info(
                    f"Auto-sent {email_type_str} batch: {len(included)} processes, "
                    f"{len(skipped)} skipped"
                )
            else:
                logger.error(f"Failed to send {email_type_str} batch: {error_type}")
                db.rollback()

    except Exception as e:
        logger.error(f"Error in auto_send_batches job: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def job_drs_follow_up():
    """
    Send follow-up emails to DRS for processes that have been 'enviado'
    for 30 or 60 days with no status update.

    Sends ONE email to DRS containing ALL processes at each threshold.
    """
    logger.info("Running job: drs_follow_up")

    db = SessionLocal()
    try:
        today = datetime.now().date()

        for days_threshold in SettingsService.get_drs_deadline_days():
            target_date = today - timedelta(days=days_threshold)
            target_datetime_start = datetime.combine(target_date, datetime.min.time())
            target_datetime_end = datetime.combine(target_date, datetime.max.time())

            processes = (
                db.query(Process)
                .options(joinedload(Process.patient).joinedload(Patient.user))
                .filter(
                    Process.status == ProcessStatus.ENVIADO,
                    Process.sent_at >= target_datetime_start,
                    Process.sent_at <= target_datetime_end,
                )
                .all()
            )

            if not processes:
                logger.info(f"No processes at {days_threshold}-day threshold")
                continue

            renovacao_processes, solicitacao_processes = filter_by_request_type(
                processes
            )

            for email_type_str, target_processes in (
                ("renovacao", renovacao_processes),
                ("solicitacao", solicitacao_processes),
            ):
                if not target_processes:
                    continue

                success, error_type = send_drs_follow_up_notification(
                    db, email_type_str, target_processes, days_threshold
                )

                if success:
                    for process in target_processes:
                        log_activity(
                            db,
                            process.id,
                            None,
                            "drs_follow_up",
                            f"Follow-up enviado ao DRS ({days_threshold} dias)",
                            {
                                "days_threshold": days_threshold,
                                "email_type": email_type_str,
                            },
                            process=process,
                        )

                    db.commit()
                    logger.info(
                        f"Sent {days_threshold}-day follow-up for {len(target_processes)} "
                        f"{email_type_str} processes"
                    )
                else:
                    logger.error(
                        f"Failed to send {days_threshold}-day follow-up for {email_type_str}: {error_type}"
                    )
                    db.rollback()

    except Exception as e:
        logger.error(f"Error in drs_follow_up job: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def send_drs_follow_up_notification(
    db: Session,
    email_type: str,
    processes: list[Process],
    days_threshold: int,
):
    """
    Send follow-up email to DRS for processes waiting too long.

    Args:
        db: Database session
        email_type: 'renovacao' or 'solicitacao'
        processes: List of processes to include
        days_threshold: 30 or 60 days

    Returns:
        Tuple of (success: bool, error_type: Optional[str])
    """
    to_email = (
        SettingsService.get_drs_renovacao_email(db)
        if email_type == "renovacao"
        else SettingsService.get_drs_solicitacao_email(db)
    )

    email_context_processes = [
        {
            "patient_name": (
                process.patient.name if process.patient else "Não informado"
            ),
            "protocol": process.protocol_number,
            "type_label": PROCESS_TYPE_TITLES.get(
                process.type.value, process.type.value
            ),
            "sent_date": (
                process.sent_at.strftime("%d/%m/%Y") if process.sent_at else "N/A"
            ),
            "days_waiting": days_threshold,
        }
        for process in processes
    ]

    email_title = (
        "Atualização - Processos Pendentes"
        if email_type == "renovacao"
        else "Atualização - Processos Pendentes"
    )

    context = {
        "email_title": email_title,
        "sent_date": datetime.now().strftime("%d/%m/%Y às %H:%M"),
        "days_threshold": days_threshold,
        "processes": email_context_processes,
    }

    subject = f"SS-54 - {email_title}"

    success, error_type = email_service.send_email(
        to=to_email,
        subject=subject,
        template_name="drs_follow_up.html",
        context=context,
    )

    return success, error_type


def job_auto_expire_processes():
    """
    Auto-expire processes that have passed their authorization period.

    - Nutrição processes: 120 days from authorization_date
    - Other types: 180 days from authorization_date
    """
    logger.info("Running job: auto_expire_processes")

    db = SessionLocal()
    try:
        today = datetime.now().date()

        nutricao_expiry_date = today - timedelta(
            days=SettingsService.get_nutricao_expiry_days()
        )
        other_expiry_date = today - timedelta(
            days=SettingsService.get_auth_expiry_days()
        )

        nutricao_processes = (
            db.query(Process)
            .filter(
                Process.status == ProcessStatus.AUTORIZADO,
                Process.type == ProcessType.NUTRICAO,
                func.date(Process.authorization_date) <= nutricao_expiry_date,
            )
            .all()
        )

        other_processes = (
            db.query(Process)
            .filter(
                Process.status == ProcessStatus.AUTORIZADO,
                Process.type != ProcessType.NUTRICAO,
                func.date(Process.authorization_date) <= other_expiry_date,
            )
            .all()
        )

        all_processes = nutricao_processes + other_processes

        if not all_processes:
            logger.info("No processes to auto-expire")
            return

        for process in all_processes:
            expiry_days = (
                SettingsService.get_nutricao_expiry_days()
                if process.type == ProcessType.NUTRICAO
                else SettingsService.get_auth_expiry_days()
            )

            update_process_status(
                db,
                process,
                ProcessStatus.EXPIRADO,
                extra_data={"auto_expired": True, "expiry_days": expiry_days},
            )

            send_status_notification(process, "expirado")

        db.commit()
        logger.info(f"Auto-expired {len(all_processes)} processes")

    except Exception as e:
        logger.error(f"Error in auto_expire_processes job: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
