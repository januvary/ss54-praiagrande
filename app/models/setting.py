"""
Database model for runtime configuration settings.
Allows administrators to modify certain settings without restarting the application.
"""

from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.database import Base


class Setting(Base):
    """
    Configuration settings that can be modified at runtime.

    Settings stored here override environment variables for:
    - Email addresses (DRS_RENOVACAO_EMAIL, DRS_SOLICITACAO_EMAIL)
    - Other configurable values as needed
    """

    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value}')>"
