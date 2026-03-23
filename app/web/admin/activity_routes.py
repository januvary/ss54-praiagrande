"""
Admin Activity Routes - Activity log viewing
"""

from typing import Optional, List
import logging

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import joinedload, Session

from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.process import Process
from app.repositories.activity_repository import get_paginated_activities
from app.utils.uuid_utils import validate_uuid
from app.utils.template_helpers import render_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Activity"])


def _filter_activities(
    activities: List[ActivityLog], process_id: Optional[str], action_type: Optional[str]
) -> List[ActivityLog]:
    """Apply client-side filters to activities list."""
    if process_id:
        process_uuid = validate_uuid(process_id, "ID de processo")
        activities = [a for a in activities if str(a.process_id) == process_uuid]

    if action_type:
        activities = [a for a in activities if a.action == action_type]

    return activities


def _reload_with_joins(db: Session, activities: List[ActivityLog]) -> List[ActivityLog]:
    """Reload activities with process and patient eager loading."""
    activity_ids = [a.id for a in activities]
    if not activity_ids:
        return []

    return (
        db.query(ActivityLog)
        .options(joinedload(ActivityLog.process).joinedload(Process.patient))
        .filter(ActivityLog.id.in_(activity_ids))
        .order_by(ActivityLog.created_at.desc())
        .all()
    )


def _get_distinct_action_types(db: Session) -> List[str]:
    """Get distinct action types from all activity logs."""
    action_types = (
        db.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all()
    )
    return [a[0] for a in action_types]


@router.get("/activity-logs", response_class=HTMLResponse)
async def admin_activity_logs(
    request: Request,
    activity_page: int = Query(1, ge=1),
    process_id: Optional[str] = None,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Página dedicada de logs de atividade com histórico completo e filtros.
    Mostra TODAS as atividades, incluindo ações de administrador e sistema.
    """
    activities, pagination = get_paginated_activities(
        db, page=activity_page, per_page=25, visibility_level="all"
    )

    activities = _filter_activities(activities, process_id, action_type)
    activities = _reload_with_joins(db, activities)

    action_types = _get_distinct_action_types(db)

    return render_template(
        request,
        "admin/activity_logs.html",
        {
            "activities": activities,
            "pagination": pagination,
            "action_types": action_types,
            "current_filters": {
                "process_id": process_id or "",
                "action_type": action_type or "",
            },
        },
        is_admin=True,
    )
