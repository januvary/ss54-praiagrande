from uuid import UUID as PyUUID
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from app.database import Base


class MagicToken(Base):
    """Magic link tokens for passwordless authentication"""

    __tablename__ = "magic_tokens"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    user_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # 'new' for new process, None for dashboard
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    used: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="check_expiry_future"),
        Index("ix_magic_tokens_user_expires", "user_id", "expires_at"),
        Index("ix_magic_tokens_used_expires", "used", "expires_at"),
    )

    def __repr__(self):
        token_preview = self.token[:8] + "..." if self.token else "None"
        return f"<MagicToken {token_preview} ({self.id})>"
