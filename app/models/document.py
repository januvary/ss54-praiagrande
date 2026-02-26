from uuid import UUID as PyUUID
from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid
import enum
from app.database import Base


class DocumentType(str, enum.Enum):
    FORMULARIO = "formulario"
    DECLARACAO = "declaracao"
    RECEITA = "receita"
    RELATORIO = "relatorio"
    DOCUMENTO_PESSOAL = "documento_pessoal"
    EXAME = "exame"
    PDF_COMBINADO = "pdf_combinado"
    OUTRO = "outro"


class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    process_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("processes.id"), nullable=False, index=True
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # File information
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Validation
    validation_status: Mapped[ValidationStatus] = mapped_column(
        SQLEnum(ValidationStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ValidationStatus.PENDING,
        index=True,
    )
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    process = relationship("Process", back_populates="documents")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "file_size > 0 AND file_size <= 10485760", name="check_file_size"
        ),
        CheckConstraint(
            "mime_type IN ('application/pdf', 'image/jpeg', 'image/png')",
            name="check_mime_type",
        ),
        Index("ix_documents_process_status", "process_id", "validation_status"),
    )

    def __repr__(self):
        return f"<Document {self.document_type} ({self.validation_status})>"
