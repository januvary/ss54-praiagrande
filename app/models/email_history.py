from uuid import UUID as PyUUID
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from app.database import Base


class EmailHistory(Base):
    __tablename__ = "email_history"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    old_email: Mapped[str] = mapped_column(String(255), nullable=False)
    new_email: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    def __repr__(self):
        return (
            f"<EmailHistory {self.old_email} -> {self.new_email} at {self.changed_at}>"
        )
