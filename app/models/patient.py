from uuid import UUID as PyUUID
from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, date
import uuid
from app.database import Base


class Patient(Base):
    """
    Perfil de paciente vinculado a uma conta de usuário.

    Um usuário (email) pode ter múltiplos pacientes associados
    (ex: pais gerenciando processos para múltiplos filhos).
    """

    __tablename__ = "patients"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="patients")
    processes = relationship(
        "Process", back_populates="patient", cascade="all, delete-orphan"
    )

    @property
    def email(self) -> str | None:
        """Get email from associated user."""
        return self.user.email if self.user else None

    @property
    def phone(self) -> str | None:
        """Get phone from associated user."""
        return self.user.phone if self.user else None

    def __repr__(self):
        # Mask name for privacy: Jo***
        if self.name:
            visible = self.name[:2] if len(self.name) >= 2 else self.name[0]
            return f"<Patient {visible}***>"
        return f"<Patient {self.id}>"
