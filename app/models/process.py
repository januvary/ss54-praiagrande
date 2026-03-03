from uuid import UUID as PyUUID
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid
import enum
from app.database import Base


class ProcessType(str, enum.Enum):
    MEDICAMENTO = "medicamento"
    NUTRICAO = "nutricao"
    BOMBA = "bomba"
    OUTRO = "outro"


class RequestType(str, enum.Enum):
    PRIMEIRA_SOLICITACAO = "primeira_solicitacao"
    RENOVACAO = "renovacao"


class ProcessStatus(str, enum.Enum):
    RASCUNHO = "rascunho"
    EM_REVISAO = "em_revisao"
    INCOMPLETO = "incompleto"
    COMPLETO = "completo"
    ENVIADO = "enviado"
    CORRECAO_SOLICITADA = "correcao_solicitada"
    AUTORIZADO = "autorizado"
    NEGADO = "negado"
    EXPIRADO = "expirado"
    OUTRO = "outro"


class Process(Base):
    __tablename__ = "processes"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    protocol_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    patient_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    type: Mapped[ProcessType] = mapped_column(
        SQLEnum(ProcessType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    request_type: Mapped[RequestType] = mapped_column(
        SQLEnum(RequestType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RequestType.PRIMEIRA_SOLICITACAO,
    )
    status: Mapped[ProcessStatus] = mapped_column(
        SQLEnum(ProcessStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ProcessStatus.RASCUNHO,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Internal notes (patient cannot see)
    original_process_id: Mapped[PyUUID | None] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("processes.id"), nullable=True, index=True
    )
    authorization_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    was_renewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    patient = relationship("Patient", back_populates="processes")
    documents = relationship(
        "Document", back_populates="process", cascade="all, delete-orphan"
    )
    activities = relationship(
        "ActivityLog", back_populates="process", cascade="all, delete-orphan"
    )
    original_process = relationship(
        "Process", remote_side=[id], foreign_keys=[original_process_id]
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_processes_patient_created", "patient_id", "created_at"),
        Index("ix_processes_status_created", "status", "created_at"),
    )

    def __repr__(self):
        return f"<Process {self.protocol_number} ({self.status})>"
