"""
Settings Service - Centralized runtime settings access

Provides type-safe methods to retrieve settings from the database
with fallback to config.py defaults. All operational settings
should be accessed through this service.
"""

import json
import logging
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy.orm import Session

from app.config import settings
from app.repositories.setting_repository import get_setting

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Centralized service for accessing runtime settings.

    All settings are read from the database with fallback to config.py.
    This allows administrators to modify settings at runtime without
    requiring application restarts.
    """

    @staticmethod
    def _get_bool(db: Session, key: str, default: bool) -> bool:
        """Helper: Get boolean setting from database."""
        value = get_setting(db, key, str(default))
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    @staticmethod
    def _get_int(db: Session, key: str, default: int) -> int:
        """Helper: Get integer setting from database."""
        value = get_setting(db, key, str(default))
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _get_str(db: Session, key: str, default: str) -> str:
        """Helper: Get string setting from database."""
        return get_setting(db, key, default) or default

    @staticmethod
    def _get_list(db: Session, key: str, default: List[int]) -> List[int]:
        """Helper: Get list setting (stored as JSON) from database."""
        value = get_setting(db, key, json.dumps(default))
        if value is None:
            return default
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [int(x) for x in parsed]
            return default
        except (json.JSONDecodeError, ValueError, TypeError):
            return default

    @staticmethod
    def _get_date(db: Session, key: str, default: str) -> date:
        """Helper: Get date setting from database (stored as YYYY-MM-DD)."""
        value = get_setting(db, key, default)
        if value is None:
            value = default
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return datetime.strptime(default, "%Y-%m-%d").date()

    # ============================================
    # MASTER SCHEDULER CONTROLS
    # ============================================

    @staticmethod
    def get_scheduler_enabled(db: Optional[Session] = None) -> bool:
        """Get scheduler master enable/disable status."""
        if db:
            return SettingsService._get_bool(
                db, "SCHEDULER_ENABLED", settings.SCHEDULER_ENABLED
            )
        return settings.SCHEDULER_ENABLED

    @staticmethod
    def get_scheduler_timezone(db: Optional[Session] = None) -> str:
        """Get scheduler timezone."""
        if db:
            return SettingsService._get_str(
                db, "SCHEDULER_TIMEZONE", settings.SCHEDULER_TIMEZONE
            )
        return settings.SCHEDULER_TIMEZONE

    @staticmethod
    def get_batch_anchor_date(db: Optional[Session] = None) -> date:
        """Get batch anchor date."""

        if db:
            return SettingsService._get_date(
                db, "BATCH_ANCHOR_DATE", settings.BATCH_ANCHOR_DATE
            )
        return datetime.strptime(settings.BATCH_ANCHOR_DATE, "%Y-%m-%d").date()

    # ============================================
    # JOB TIMING & TOGGLES
    # ============================================

    @staticmethod
    def get_batch_send_hour(db: Optional[Session] = None) -> int:
        """Get batch send hour (0-23)."""
        if db:
            return SettingsService._get_int(
                db, "BATCH_SEND_HOUR", settings.BATCH_SEND_HOUR
            )
        return settings.BATCH_SEND_HOUR

    @staticmethod
    def get_batch_send_enabled(db: Optional[Session] = None) -> bool:
        """Get batch send job enabled status."""
        if db:
            return SettingsService._get_bool(
                db, "BATCH_SEND_ENABLED", settings.BATCH_SEND_ENABLED
            )
        return settings.BATCH_SEND_ENABLED

    @staticmethod
    def get_drs_followup_hour(db: Optional[Session] = None) -> int:
        """Get DRS follow-up hour (0-23)."""
        if db:
            return SettingsService._get_int(
                db, "DRS_FOLLOWUP_HOUR", settings.DRS_FOLLOWUP_HOUR
            )
        return settings.DRS_FOLLOWUP_HOUR

    @staticmethod
    def get_drs_followup_enabled(db: Optional[Session] = None) -> bool:
        """Get DRS follow-up job enabled status."""
        if db:
            return SettingsService._get_bool(
                db, "DRS_FOLLOWUP_ENABLED", settings.DRS_FOLLOWUP_ENABLED
            )
        return settings.DRS_FOLLOWUP_ENABLED

    @staticmethod
    def get_auto_expire_hour(db: Optional[Session] = None) -> int:
        """Get auto expire hour (0-23)."""
        if db:
            return SettingsService._get_int(
                db, "AUTO_EXPIRE_HOUR", settings.AUTO_EXPIRE_HOUR
            )
        return settings.AUTO_EXPIRE_HOUR

    @staticmethod
    def get_auto_expire_enabled(db: Optional[Session] = None) -> bool:
        """Get auto expire job enabled status."""
        if db:
            return SettingsService._get_bool(
                db, "AUTO_EXPIRE_ENABLED", settings.AUTO_EXPIRE_ENABLED
            )
        return settings.AUTO_EXPIRE_ENABLED

    # ============================================
    # BUSINESS RULES
    # ============================================

    @staticmethod
    def get_batch_interval_days(db: Optional[Session] = None) -> int:
        """Get batch interval in days."""
        if db:
            return SettingsService._get_int(
                db, "BATCH_INTERVAL_DAYS", settings.BATCH_INTERVAL_DAYS
            )
        return settings.BATCH_INTERVAL_DAYS

    @staticmethod
    def get_drs_deadline_days(db: Optional[Session] = None) -> List[int]:
        """Get DRS deadline days list (e.g., [30, 60])."""
        if db:
            return SettingsService._get_list(
                db, "DRS_DEADLINE_DAYS", settings.DRS_DEADLINE_DAYS
            )
        return settings.DRS_DEADLINE_DAYS

    @staticmethod
    def get_auth_expiry_days(db: Optional[Session] = None) -> int:
        """Get authorization expiry days."""
        if db:
            return SettingsService._get_int(
                db, "AUTH_EXPIRY_DAYS", settings.AUTH_EXPIRY_DAYS
            )
        return settings.AUTH_EXPIRY_DAYS

    @staticmethod
    def get_auth_expiry_warning_days(db: Optional[Session] = None) -> int:
        """Get authorization expiry warning days."""
        if db:
            return SettingsService._get_int(
                db, "AUTH_EXPIRY_WARNING_DAYS", settings.AUTH_EXPIRY_WARNING_DAYS
            )
        return settings.AUTH_EXPIRY_WARNING_DAYS

    @staticmethod
    def get_nutricao_expiry_days(db: Optional[Session] = None) -> int:
        """Get nutrição authorization expiry days."""
        if db:
            return SettingsService._get_int(
                db, "NUTRICAO_EXPIRY_DAYS", settings.NUTRICAO_EXPIRY_DAYS
            )
        return settings.NUTRICAO_EXPIRY_DAYS

    # ============================================
    # DATA RETENTION
    # ============================================

    @staticmethod
    def get_data_retention_years(db: Optional[Session] = None) -> int:
        """Get data retention years."""
        if db:
            return SettingsService._get_int(
                db, "DATA_RETENTION_YEARS", settings.DATA_RETENTION_YEARS
            )
        return settings.DATA_RETENTION_YEARS

    @staticmethod
    def get_data_retention_enabled(db: Optional[Session] = None) -> bool:
        """Get data retention cleanup enabled status."""
        if db:
            return SettingsService._get_bool(
                db, "DATA_RETENTION_ENABLED", settings.DATA_RETENTION_ENABLED
            )
        return settings.DATA_RETENTION_ENABLED

    # ============================================
    # EMAIL SETTINGS
    # ============================================

    @staticmethod
    def get_drs_renovacao_email(db: Optional[Session] = None) -> str:
        """Get DRS renewal email address."""
        if db:
            return SettingsService._get_str(
                db, "DRS_RENOVACAO_EMAIL", settings.DRS_RENOVACAO_EMAIL
            )
        return settings.DRS_RENOVACAO_EMAIL

    @staticmethod
    def get_drs_solicitacao_email(db: Optional[Session] = None) -> str:
        """Get DRS solicitation email address."""
        if db:
            return SettingsService._get_str(
                db, "DRS_SOLICITACAO_EMAIL", settings.DRS_SOLICITACAO_EMAIL
            )
        return settings.DRS_SOLICITACAO_EMAIL

    @staticmethod
    def get_emails_from_email(db: Optional[Session] = None) -> str:
        """Get email 'from' address."""
        if db:
            return SettingsService._get_str(
                db, "EMAILS_FROM_EMAIL", settings.EMAILS_FROM_EMAIL
            )
        return settings.EMAILS_FROM_EMAIL

    @staticmethod
    def get_emails_from_name(db: Optional[Session] = None) -> str:
        """Get email 'from' name."""
        if db:
            return SettingsService._get_str(
                db, "EMAILS_FROM_NAME", settings.EMAILS_FROM_NAME
            )
        return settings.EMAILS_FROM_NAME

    # ============================================
    # APP CONFIG SETTINGS
    # ============================================

    @staticmethod
    def get_app_name(db: Optional[Session] = None) -> str:
        """Get application name."""
        if db:
            return SettingsService._get_str(db, "APP_NAME", settings.APP_NAME)
        return settings.APP_NAME

    @staticmethod
    def get_frontend_url(db: Optional[Session] = None) -> str:
        """Get frontend URL."""
        if db:
            return SettingsService._get_str(db, "FRONTEND_URL", settings.FRONTEND_URL)
        return settings.FRONTEND_URL

    @staticmethod
    def get_allowed_origins(db: Optional[Session] = None) -> str:
        """Get allowed CORS origins (comma-separated string)."""
        if db:
            return SettingsService._get_str(
                db, "ALLOWED_ORIGINS", settings.ALLOWED_ORIGINS
            )
        return settings.ALLOWED_ORIGINS

    @staticmethod
    def get_allowed_origins_list(db: Optional[Session] = None) -> List[str]:
        """Get allowed CORS origins as list."""
        origins = SettingsService.get_allowed_origins(db)
        return [origin.strip() for origin in origins.split(",")]

    # ============================================
    # CONVENIENCE METHODS
    # ============================================

    @staticmethod
    def get_all_scheduler_config(db: Session) -> dict:
        """
        Get all scheduler-related settings as a single dict.

        Useful for initializing or reloading the scheduler.
        """
        return {
            # Master Controls
            "scheduler_enabled": SettingsService.get_scheduler_enabled(db),
            "scheduler_timezone": SettingsService.get_scheduler_timezone(db),
            # Job Timing & Toggles
            "batch_send_hour": SettingsService.get_batch_send_hour(db),
            "batch_send_enabled": SettingsService.get_batch_send_enabled(db),
            "drs_followup_hour": SettingsService.get_drs_followup_hour(db),
            "drs_followup_enabled": SettingsService.get_drs_followup_enabled(db),
            "auto_expire_hour": SettingsService.get_auto_expire_hour(db),
            "auto_expire_enabled": SettingsService.get_auto_expire_enabled(db),
            # Business Rules
            "batch_interval_days": SettingsService.get_batch_interval_days(db),
            "drs_deadline_days": SettingsService.get_drs_deadline_days(db),
            "auth_expiry_days": SettingsService.get_auth_expiry_days(db),
            "auth_expiry_warning_days": SettingsService.get_auth_expiry_warning_days(
                db
            ),
            "nutricao_expiry_days": SettingsService.get_nutricao_expiry_days(db),
        }

    @staticmethod
    def get_all_email_config(db: Session) -> dict:
        """
        Get all email-related settings as a single dict.

        Replaces the get_email_config() function in setting_repository.py.
        """
        return {
            "drs_renovacao_email": SettingsService.get_drs_renovacao_email(db),
            "drs_solicitacao_email": SettingsService.get_drs_solicitacao_email(db),
            "emails_from_email": SettingsService.get_emails_from_email(db),
            "emails_from_name": SettingsService.get_emails_from_name(db),
        }
