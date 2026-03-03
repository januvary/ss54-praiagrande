"""
Repository functions for managing runtime configuration settings.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.setting import Setting


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a setting value from the database.

    Args:
        db: Database session
        key: Setting key to retrieve
        default: Default value if setting not found

    Returns:
        Setting value or default if not found
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        return setting.value
    return default


def set_setting(db: Session, key: str, value: str) -> Setting:
    """
    Set a setting value in the database (create or update).

    Args:
        db: Database session
        key: Setting key to set
        value: Value to set

    Returns:
        The created or updated Setting object
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
        setting.updated_at = None  # Let the default trigger
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


def get_email_config(db: Session) -> dict:
    """
    Get all email configuration from database or fallback to environment variables.

    Args:
        db: Database session

    Returns:
        Dictionary with email configuration values
    """
    from app.config import settings

    return {
        "drs_renovacao_email": get_setting(
            db, "DRS_RENOVACAO_EMAIL", settings.DRS_RENOVACAO_EMAIL
        ),
        "drs_solicitacao_email": get_setting(
            db, "DRS_SOLICITACAO_EMAIL", settings.DRS_SOLICITACAO_EMAIL
        ),
        "emails_from_email": get_setting(
            db, "EMAILS_FROM_EMAIL", settings.EMAILS_FROM_EMAIL
        ),
        "emails_from_name": get_setting(
            db, "EMAILS_FROM_NAME", settings.EMAILS_FROM_NAME
        ),
    }
