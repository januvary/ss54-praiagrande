"""
Activity Log Repository - Data access layer for ActivityLog queries.

This module handles all database queries related to activity logs,
including pagination and visibility-based filtering.

Responsibilities:
- Retrieving paginated activity logs
- Applying visibility filters based on user roles
- Efficient eager loading of related entities

Visibility Levels:
- 'user': User-facing actions only (process_created, process_renewed,
          document_uploaded, status_changed)
- 'admin': User + admin actions (excludes only pdf_generated)
- 'all': No filtering
"""

from typing import Tuple, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.activity_log import ActivityLog
from app.models.process import Process
from app.models.patient import Patient
from app.utils.pagination import PaginationInfo, calculate_pagination
from app.utils.uuid_utils import ensure_uuid

USER_VISIBLE_ACTIONS = frozenset(
    ["process_created", "process_renewed", "document_uploaded", "status_changed"]
)

ADMIN_HIDDEN_ACTIONS = frozenset(["pdf_generated"])


def get_paginated_activities(
    db: Session,
    process_id: Optional[str] = None,
    user_id: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    visibility_level: str = "user",
) -> Tuple[list, PaginationInfo]:
    """
    Retrieve paginated activity logs with optional filtering.

    Args:
        db: Database session
        process_id: Optional UUID string to filter by process
        user_id: Optional UUID string to filter by user (via Process-Patient join)
        page: Page number (1-indexed)
        per_page: Items per page
        visibility_level: 'user', 'admin', or 'all'

    Returns:
        Tuple of (activities list, pagination metadata)

    Example:
        >>> activities, pagination = get_paginated_activities(
        ...     db,
        ...     user_id=str(current_user.id),
        ...     page=1,
        ...     per_page=10,
        ...     visibility_level="user",
        ... )
    """
    count_query = _apply_visibility_filter(
        _apply_base_filter(db.query(func.count(ActivityLog.id)), process_id, user_id),
        visibility_level,
    )
    total = count_query.scalar() or 0

    pagination = calculate_pagination(page, per_page, total)

    activities = (
        _apply_visibility_filter(
            _apply_base_filter(db.query(ActivityLog), process_id, user_id),
            visibility_level,
        )
        .options(joinedload(ActivityLog.process).joinedload(Process.patient))
        .order_by(ActivityLog.created_at.desc())
        .offset(pagination["offset"])
        .limit(per_page)
        .all()
    )

    return activities, pagination


def _apply_base_filter(query, process_id: Optional[str], user_id: Optional[str]):
    """
    Apply base filtering by process_id or user_id.

    Args:
        query: SQLAlchemy query object
        process_id: Optional process UUID string
        user_id: Optional user UUID string

    Returns:
        Query with base filters applied
    """
    if process_id:
        process_uuid = ensure_uuid(process_id)
        return query.filter(ActivityLog.process_id == process_uuid)

    if user_id:
        user_uuid = ensure_uuid(user_id)
        return query.join(Process).join(Patient).filter(Patient.user_id == user_uuid)

    return query


def _apply_visibility_filter(query, visibility_level: str):
    """
    Apply visibility-based filtering to activity query.

    Visibility levels control which actions are visible:
    - 'user': Only USER_VISIBLE_ACTIONS (process_created, process_renewed,
              document_uploaded, status_changed)
    - 'admin': All except ADMIN_HIDDEN_ACTIONS (pdf_generated)
    - 'all': No filtering

    Note on 'user' visibility:
        status_changed includes admin-initiated status changes (where user_id
        is None). Users need to see these to track their process progress.

    Args:
        query: SQLAlchemy query object
        visibility_level: 'user', 'admin', or 'all'

    Returns:
        Query with visibility filter applied
    """
    if visibility_level == "user":
        return query.filter(ActivityLog.action.in_(USER_VISIBLE_ACTIONS))

    if visibility_level == "admin":
        return query.filter(ActivityLog.action.notin_(ADMIN_HIDDEN_ACTIONS))

    return query
