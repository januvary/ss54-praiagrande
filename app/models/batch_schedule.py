import uuid
import enum
from datetime import datetime, date
from sqlalchemy import Date, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class EmailType(str, enum.Enum):
    RENOVACAO = "renovacao"
    SOLICITACAO = "solicitacao"


class BatchSchedule(Base):
    __tablename__ = "batch_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email_type: Mapped[EmailType] = mapped_column(
        SQLEnum(EmailType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    process_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    def __repr__(self):
        return f"<BatchSchedule {self.scheduled_date} ({self.email_type.value})>"
