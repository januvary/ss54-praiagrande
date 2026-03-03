"""
Activity Log Service - Centralized activity logging.

Consolidates ActivityLog creation pattern to eliminate code duplication
across routes.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.activity_log import ActivityLog
from app.models.process import Process, ProcessStatus


def log_activity(
    db: Session,
    process_id: UUID,
    user_id: Optional[UUID],
    action: str,
    description: str,
    extra_data: Optional[dict] = None,
    process: Optional[Process] = None,
) -> ActivityLog:
    """
    Create and add an activity log entry.

    This helper function eliminates the repetitive pattern of creating
    ActivityLog objects throughout the codebase.

    Args:
        db: Database session
        process_id: Process UUID
        user_id: User UUID (None for system actions)
        action: Action type (e.g., "process_created", "status_changed")
        description: Human-readable description
        extra_data: Optional dictionary for additional metadata
        process: Optional Process object to avoid redundant queries

    Returns:
        The created ActivityLog object

    Example:
        >>> log_activity(
        ...     db, process_id, user_id,
        ...     "status_changed",
        ...     "Status alterado",
        ...     {"old_status": "rascunho", "new_status": "em_revisao"}
        ... )
    """
    activity = ActivityLog(
        process_id=process_id,
        user_id=user_id,
        action=action,
        description=description,
        extra_data=extra_data or {},
    )
    db.add(activity)

    # Set authorization_date when status changes to AUTORIZADO
    if action == "status_changed" and extra_data:
        new_status = extra_data.get("new_status")
        if new_status == ProcessStatus.AUTORIZADO:
            target_process = (
                process or db.query(Process).filter(Process.id == process_id).first()
            )

            if target_process:
                target_process.authorization_date = datetime.now()

    return activity
