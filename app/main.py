from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from app.config import settings
from app.database import init_db, close_db
from app.web.auth_routes import router as auth_router
from app.web.home_routes import router as home_router
from app.web.dashboard_routes import router as dashboard_router
from app.web.lgpd_routes import router as lgpd_router
from app.web.process_routes import router as process_router
from app.web.document_routes import router as document_router
from app.web.patient_routes import router as patient_router
from app.web.admin.auth_routes import router as admin_auth_router
from app.web.admin.dashboard_routes import router as admin_dashboard_router
from app.web.admin.process_routes import router as admin_process_router
from app.web.admin.document_routes import router as admin_document_router
from app.web.admin.email_routes import router as admin_email_router
from app.web.admin.pdf_routes import router as admin_pdf_router
from app.web.admin.settings_routes import router as admin_settings_router
from app.web.admin.activity_routes import router as admin_activity_router
from app.web.admin.calendar_routes import router as admin_calendar_router
from app.services.csrf_service import CSRFMiddleware
from app.middleware.admin_whitelist import AdminWhitelistMiddleware
from app.middleware.admin_auth import AdminAuthMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.csp_nonce import CSPNonceMiddleware
from app.scheduler import init_scheduler, shutdown_scheduler
from app.services.storage_service import (
    init_storage_checker,
    verify_storage_on_startup,
)
from contextlib import asynccontextmanager
from pathlib import Path

import logging

_log_dir = Path(__file__).parent.parent.parent / "logs"
_log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(_log_dir / "app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown events"""
    logger.info("[>>] Starting SS-54 Backend...")
    init_db()
    logger.info("[OK] Database initialized")

    storage_ok = verify_storage_on_startup(settings.UPLOAD_DIR)
    if settings.STORAGE_STARTUP_REQUIRED and not storage_ok:
        logger.error("[FAIL] Storage unavailable and STORAGE_STARTUP_REQUIRED=True")
        raise RuntimeError("Storage unavailable at startup")
    elif not storage_ok:
        logger.warning(
            "[WARN] Storage unavailable but continuing (STORAGE_STARTUP_REQUIRED=False)"
        )

    init_storage_checker(settings.UPLOAD_DIR, settings.STORAGE_HEALTHCHECK_INTERVAL)
    logger.info("[OK] Storage health checker initialized")

    init_scheduler()
    yield
    logger.info("[<<] Shutting down SS-54 Backend...")
    shutdown_scheduler()
    close_db()
    logger.info("[OK] Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for SS-54 Pharmaceutical Assistance System",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Registra todas as exceções não tratadas"""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    return PlainTextResponse(
        "Internal Server Error. Please contact support if the problem persists.",
        status_code=500,
    )


# CSP Nonce Middleware (must be first to generate nonce for CSP)
app.add_middleware(CSPNonceMiddleware)

# Security Headers Middleware (uses nonce from CSPNonceMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CSRF Middleware (must be added before CORS)
app.add_middleware(CSRFMiddleware)

# Admin Session Authentication (after IP whitelist in request order)
app.add_middleware(AdminAuthMiddleware)

# Admin IP Whitelist Middleware (first admin check - fail fast for external IPs)
app.add_middleware(AdminWhitelistMiddleware)

# Configure CORS
# Note: Restrictive configuration for same-origin deployment.
# Only allows specific methods and headers needed by the application.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Content-Type",
        "X-CSRF-Token",
        "HX-Request",
        "HX-Current-URL",
        "HX-Trigger",
        "HX-Target",
    ],
)


# Health check endpoint (API only)
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


APP_DIR = Path(__file__).parent

# Mount static files
static_dir = APP_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount files directory (PDFs)
files_dir = APP_DIR / "files"
if files_dir.exists():
    app.mount("/files", StaticFiles(directory=str(files_dir)), name="files")


# Include web routes (HTML pages)
app.include_router(home_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(lgpd_router)
app.include_router(process_router)
app.include_router(document_router)
app.include_router(patient_router)

# Include admin routes
app.include_router(admin_auth_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_process_router)
app.include_router(admin_document_router)
app.include_router(admin_email_router)
app.include_router(admin_pdf_router)
app.include_router(admin_settings_router)
app.include_router(admin_activity_router)
app.include_router(admin_calendar_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
