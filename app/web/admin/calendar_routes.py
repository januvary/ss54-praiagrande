"""
Admin Calendar Routes - Calendar view for batch tracking and deadlines
"""

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import List, TypedDict

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.process import Process
from app.utils.template_helpers import render_template
from app.repositories.calendar_repository import (
    get_sent_processes_in_range,
    get_enviado_processes,
    get_authorized_processes,
    get_last_batch_date,
)
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/admin/calendar", tags=["Admin Calendar"])


class CalendarEvent(TypedDict):
    date: str
    type: str
    count: int
    processes: List[dict]
    is_predicted: bool


def generate_predicted_batch_dates(
    last_batch: datetime | None, view_start: datetime, view_end: datetime
) -> List[date]:
    """Generate predicted batch dates based on last batch date."""
    predicted = []

    if last_batch is None:
        anchor = SettingsService.get_batch_anchor_date()
    else:
        anchor = last_batch

    current = anchor
    while current < view_end:
        if current >= view_start and current > datetime.now():
            predicted.append(current)
        current += timedelta(days=SettingsService.get_batch_interval_days())

    return predicted


def _calculate_view_window(month: str) -> tuple[datetime, datetime]:
    """
    Calculate the view window for a given month (with padding for full weeks).

    Args:
        month: Month string in format "YYYY-MM"

    Returns:
        Tuple of (view_start, view_end) as datetime objects
    """
    year, month_num = map(int, month.split("-"))
    first_day = datetime(year, month_num, 1)
    last_day = datetime(year, month_num, monthrange(year, month_num)[1])

    padding_start = first_day.weekday()
    padding_end = 6 - last_day.weekday()

    view_start = first_day - timedelta(days=padding_start)
    view_end = last_day + timedelta(days=padding_end + 1)

    return view_start, view_end


def _create_event_dict(date_str: str, event_type: str) -> dict:
    """Create a new event dictionary."""
    return {
        "date": date_str,
        "type": event_type,
        "count": 0,
        "processes": [],
    }


def _update_event_type_precedence(
    events: dict[str, dict], date_str: str, new_type: str
) -> str:
    """
    Update event type based on precedence rules.

    Precedence (highest to lowest):
    1. batch_sent
    2. deadline_30
    3. deadline_60
    4. expiry

    Args:
        events: Events dictionary
        date_str: Date key in events
        new_type: New event type to consider

    Returns:
        The resolved event type (may be new_type or existing_type if higher precedence)
    """
    precedence = {
        "batch_sent": 4,
        "deadline_30": 3,
        "deadline_60": 2,
        "expiry": 1,
        "predicted_batch": 0,
    }

    if date_str not in events:
        return new_type

    existing_type = events[date_str]["type"]
    existing_priority = precedence.get(existing_type, 0)
    new_priority = precedence.get(new_type, 0)

    return existing_type if existing_priority > new_priority else new_type


def _add_sent_process_event(events: dict[str, dict], process: Process):
    """Add a batch sent event for a process."""
    if process.sent_at is None:
        return
    date_str = process.sent_at.strftime("%Y-%m-%d")

    event_type = _update_event_type_precedence(events, date_str, "batch_sent")

    if date_str not in events:
        events[date_str] = _create_event_dict(date_str, event_type)

    events[date_str]["count"] += 1
    events[date_str]["processes"].append(
        {
            "id": str(process.id),
            "protocol": process.protocol_number,
            "patient_name": process.patient.name if process.patient else None,
            "status": process.status.value,
            "type": "sent",
            "days_ago": (
                (datetime.now() - process.sent_at).days if process.sent_at else None
            ),
        }
    )


def _add_predicted_events(events: dict[str, dict], predicted_dates: List[date]):
    """Add predicted batch events to the events dict."""
    for predicted_date in predicted_dates:
        date_str = predicted_date.strftime("%Y-%m-%d")

        event_type = _update_event_type_precedence(events, date_str, "predicted_batch")

        if date_str not in events:
            events[date_str] = _create_event_dict(date_str, event_type)

        events[date_str]["is_predicted"] = True
        events[date_str]["processes"].append(
            {
                "type": "predicted",
                "date": date_str,
            }
        )


def _add_deadline_event(
    events: dict[str, dict],
    process: Process,
    deadline_date: datetime,
    deadline_type: str,
    view_start: datetime,
    view_end: datetime,
):
    """
    Add a deadline event (30 or 60 days) for a process.

    Args:
        events: Events dictionary
        process: Process object
        deadline_date: Calculated deadline date
        deadline_type: "deadline_30" or "deadline_60"
        view_start: View window start date
        view_end: View window end date
    """
    if process.sent_at is None:
        return
    if not (view_start <= deadline_date < view_end):
        return

    date_str = deadline_date.strftime("%Y-%m-%d")

    event_type = _update_event_type_precedence(events, date_str, deadline_type)

    if date_str not in events:
        events[date_str] = _create_event_dict(date_str, event_type)

    events[date_str]["count"] += 1
    events[date_str]["processes"].append(
        {
            "id": str(process.id),
            "protocol": process.protocol_number,
            "patient_name": process.patient.name if process.patient else None,
            "status": process.status.value,
            "type": "drs_30" if deadline_type == "deadline_30" else "drs_60",
            "days_since_sent": (deadline_date - process.sent_at).days,
            "deadline_date": date_str,
        }
    )


def _add_deadline_events_for_process(
    events: dict[str, dict], process: Process, view_start: datetime, view_end: datetime
):
    """Add both 30 and 60 day deadline events for a process."""
    if not process.sent_at:
        return

    deadline_30 = process.sent_at + timedelta(
        days=SettingsService.get_drs_deadline_days()[0]
    )
    deadline_60 = process.sent_at + timedelta(
        days=SettingsService.get_drs_deadline_days()[1]
    )

    _add_deadline_event(
        events, process, deadline_30, "deadline_30", view_start, view_end
    )
    _add_deadline_event(
        events, process, deadline_60, "deadline_60", view_start, view_end
    )


def _add_expiry_event(
    events: dict[str, dict],
    process: Process,
    expiry_date: datetime,
    warning_date: datetime,
    view_start: datetime,
    view_end: datetime,
):
    """
    Add expiry events for a process.

    Adds events for both the expiry date and the warning date (if configured).

    Args:
        events: Events dictionary
        process: Process object
        expiry_date: Full expiry date (180 days after authorization)
        warning_date: Warning date (configurable days before expiry)
        view_start: View window start date
        view_end: View window end date
    """
    if process.authorization_date is None:
        return
    for event_date, event_type_key in (
        (warning_date, "expiry_warning"),
        (expiry_date, "expiry"),
    ):
        if view_start <= event_date < view_end:
            date_str = event_date.strftime("%Y-%m-%d")

            # For expiry, use "expiry" type (same for warning and actual expiry)
            final_event_type = "expiry"

            resolved_type = _update_event_type_precedence(
                events, date_str, final_event_type
            )

            if date_str not in events:
                events[date_str] = _create_event_dict(date_str, resolved_type)

            events[date_str]["count"] += 1
            events[date_str]["processes"].append(
                {
                    "id": str(process.id),
                    "protocol": process.protocol_number,
                    "patient_name": process.patient.name if process.patient else None,
                    "status": process.status.value,
                    "type": "auth_expiry",
                    "days_since_auth": (
                        datetime.now() - process.authorization_date
                    ).days,
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "is_warning": event_type_key == "expiry_warning",
                    "days_until_expiry": (
                        (expiry_date - datetime.now()).days
                        if event_type_key == "expiry_warning"
                        else 0
                    ),
                }
            )


def _add_expiry_events_for_process(
    events: dict[str, dict], process: Process, view_start: datetime, view_end: datetime
):
    """Add expiry events for a process."""
    if not process.authorization_date:
        return

    expiry_warning_days = SettingsService.get_auth_expiry_warning_days()

    expiry_date = process.authorization_date + timedelta(
        days=SettingsService.get_auth_expiry_days()
    )
    warning_date = expiry_date - timedelta(days=expiry_warning_days)

    _add_expiry_event(events, process, expiry_date, warning_date, view_start, view_end)


@router.get("", response_class=HTMLResponse)
async def calendar_view(request: Request, db: Session = Depends(get_db)):
    """
    Calendar admin page showing batches, DRS deadlines, and authorization expiry.
    """
    return render_template(
        request,
        "admin/calendar.html",
        {},
        is_admin=True,
    )


@router.get("/events", response_class=JSONResponse)
async def get_calendar_events(
    request: Request,
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
):
    """
    Get calendar events for a specific month.

    Returns events for:
    - Batch sent dates (processes sent to DRS)
    - Predicted batch dates
    - DRS 30-day deadline approaching
    - DRS 60-day deadline
    - Authorization expiry warnings (configurable days before 180-day expiry)
    - Authorization expiry dates
    """
    view_start, view_end = _calculate_view_window(month)

    events: dict[str, dict] = {}

    sent_processes = get_sent_processes_in_range(db, view_start, view_end)
    for process in sent_processes:
        _add_sent_process_event(events, process)

    last_batch = get_last_batch_date(db)
    predicted_dates = generate_predicted_batch_dates(last_batch, view_start, view_end)
    _add_predicted_events(events, predicted_dates)

    enviado_processes = get_enviado_processes(db)
    for process in enviado_processes:
        _add_deadline_events_for_process(events, process, view_start, view_end)

    authorized_processes = get_authorized_processes(db)
    for process in authorized_processes:
        _add_expiry_events_for_process(events, process, view_start, view_end)

    return {"events": list(events.values())}
