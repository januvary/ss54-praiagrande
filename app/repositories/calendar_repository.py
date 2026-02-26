"""
Calendar Repository - Calendar event queries for admin dashboard.
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.process import Process, ProcessStatus
from app.models.patient import Patient


def get_sent_processes_in_range(
    db: Session, start: datetime, end: datetime
) -> List[Process]:
    """
    Get processes that were sent to DRS within the specified date range.

    Args:
        db: Database session
        start: Start date (inclusive)
        end: End date (exclusive)

    Returns:
        List of Process objects with Patient loaded
    """
    return (
        db.query(Process)
        .options()
        .join(Patient, Process.patient_id == Patient.id)
        .filter(
            Process.sent_at.isnot(None),
            Process.sent_at >= start,
            Process.sent_at < end,
        )
        .all()
    )


def get_enviado_processes(db: Session) -> List[Process]:
    """
    Get all processes with 'enviado' status.

    Used for calculating DRS deadline events (30 and 60 days).

    Args:
        db: Database session

    Returns:
        List of Process objects with Patient loaded
    """
    return (
        db.query(Process)
        .options()
        .join(Patient, Process.patient_id == Patient.id)
        .filter(
            Process.status == ProcessStatus.ENVIADO,
            Process.sent_at.isnot(None),
        )
        .all()
    )


def get_authorized_processes(db: Session) -> List[Process]:
    """
    Get all processes with 'autorizado' status.

    Used for calculating authorization expiry events (180 days).

    Args:
        db: Database session

    Returns:
        List of Process objects with Patient loaded
    """
    return (
        db.query(Process)
        .options()
        .join(Patient, Process.patient_id == Patient.id)
        .filter(
            Process.status == ProcessStatus.AUTORIZADO,
            Process.authorization_date.isnot(None),
        )
        .all()
    )


def get_last_batch_date(db: Session) -> Optional[datetime]:
    """
    Get the date of the most recent batch sent to DRS.

    Args:
        db: Database session

    Returns:
        Datetime of last sent batch, or None if no batches sent
    """
    result = (
        db.query(func.max(Process.sent_at)).filter(Process.sent_at.isnot(None)).scalar()
    )
    return result
