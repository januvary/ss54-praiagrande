"""
Admin Dashboard Routes - Dashboard display with statistics and recent activity
"""

import logging

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.process import ProcessResponse
from app.utils.serialization import serialize_orm_list
from app.repositories.activity_repository import get_paginated_activities
from app.utils.template_helpers import render_template
from app.repositories.process_repository import (
    get_recent_processes,
    get_dashboard_statistics,
)
from app.content import PROCESS_TYPE_TITLES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, activity_page: int = Query(1, ge=1), db: Session = Depends(get_db)
):
    """Painel de admin com estatísticas e atividade recente."""

    stats = get_dashboard_statistics(db)

    pending_review = stats["status_counts"].get("em_revisao", 0)
    ready_to_send = stats["status_counts"].get("completo", 0)
    sent_count = stats["status_counts"].get("enviado", 0)

    recent_processes_orm = get_recent_processes(db, limit=10)
    recent_processes = serialize_orm_list(ProcessResponse, recent_processes_orm)

    recent_activity, activity_pagination = get_paginated_activities(
        db,
        page=activity_page,
        per_page=7,
        visibility_level="user",
    )

    return render_template(
        request,
        "admin/dashboard.html",
        {
            "status_counts": stats["status_counts"],
            "total_processes": stats["total_processes"],
            "total_patients": stats["total_patients"],
            "total_documents": stats["total_documents"],
            "recent_processes": recent_processes,
            "recent_activity": recent_activity,
            "processes_this_week": stats["processes_this_week"],
            "processes_this_month": stats["processes_this_month"],
            "pending_review": pending_review,
            "ready_to_send": ready_to_send,
            "sent_count": sent_count,
            "activity_pagination": activity_pagination,
            "type_labels": PROCESS_TYPE_TITLES,
        },
        is_admin=True,
    )
