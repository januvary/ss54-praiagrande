from uuid import UUID as PyUUID
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid
from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    process_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("processes.id"), nullable=False, index=True
    )
    user_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )  # Nullable for system actions

    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # created, document_uploaded, status_changed, etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[dict] = mapped_column(
        JSON, nullable=True
    )  # Additional data (e.g., old_status, new_status)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False, index=True
    )

    # Relationships
    process = relationship("Process", back_populates="activities")
    user = relationship("User", back_populates="activities")

    # Composite index for timeline queries
    __table_args__ = (Index("ix_activity_process_created", "process_id", "created_at"),)

    def __repr__(self):
        return f"<ActivityLog {self.action} at {self.created_at}>"
