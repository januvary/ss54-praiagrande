from uuid import UUID as PyUUID
from sqlalchemy import String, Text, DateTime, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid
from app.database import Base


class SyncStatus:
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


class DocumentSyncState(Base):
    __tablename__ = "document_sync_state"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SyncStatus.PENDING
    )
    sync_attempts: Mapped[int] = mapped_column(default=0)
    last_sync_attempt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    remote_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    document = relationship("Document", backref="sync_state", uselist=False)

    __table_args__ = (
        Index("idx_sync_status", "sync_status"),
        Index(
            "idx_sync_pending",
            "sync_status",
            postgresql_where="sync_status = 'pending'",
        ),
    )

    def __repr__(self):
        return f"<DocumentSyncState {self.document_id}: {self.sync_status}>"


class SyncConfig(Base):
    __tablename__ = "sync_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_sync_files_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    def __repr__(self):
        return "<SyncConfig>"
