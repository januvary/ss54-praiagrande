"""
Repository layer for SS-54 application.

Repositories encapsulate database query logic and ensure consistent
eager loading patterns to prevent N+1 queries.
"""

from app.repositories.process_repository import (
    get_process_with_documents,
    get_process_with_patient_and_documents,
    get_processes_for_patient,
    get_all_processes_paginated,
    get_recent_processes,
    get_process_for_update,
    get_dashboard_statistics,
    get_processes_by_statuses,
)

from app.repositories.document_repository import (
    get_document_by_id,
    get_document_for_download,
)

from app.repositories.activity_repository import (
    get_paginated_activities,
)

__all__ = [
    "get_process_with_documents",
    "get_process_with_patient_and_documents",
    "get_processes_for_patient",
    "get_all_processes_paginated",
    "get_recent_processes",
    "get_process_for_update",
    "get_dashboard_statistics",
    "get_processes_by_statuses",
    "get_document_by_id",
    "get_document_for_download",
    "get_paginated_activities",
]
