"""
Admin Routes Package
"""

from app.web.admin.auth_routes import router as auth_router
from app.web.admin.dashboard_routes import router as dashboard_router
from app.web.admin.process_routes import router as process_router
from app.web.admin.document_routes import router as document_router
from app.web.admin.email_routes import router as email_router
from app.web.admin.pdf_routes import router as pdf_router
from app.web.admin.settings_routes import router as settings_router
from app.web.admin.activity_routes import router as activity_router
from app.web.admin.calendar_routes import router as calendar_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "process_router",
    "document_router",
    "email_router",
    "pdf_router",
    "settings_router",
    "activity_router",
    "calendar_router",
]
