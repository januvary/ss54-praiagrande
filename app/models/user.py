from uuid import UUID as PyUUID
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid
from app.database import Base


class User(Base):
    """Contas de usuários - usadas apenas para autenticação.

    Pacientes são gerenciados através da model Patient, permitindo
    múltiplos pacientes por conta de email (ex: pais com múltiplos filhos).
    """

    __tablename__ = "users"

    id: Mapped[PyUUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Phone number belongs to the user (account holder)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # Soft delete support
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    patients = relationship(
        "Patient", back_populates="user", cascade="all, delete-orphan"
    )
    activities = relationship("ActivityLog", back_populates="user")

    @property
    def is_deleted(self) -> bool:
        """Verifica se o usuário foi soft deletado"""
        return self.deleted_at is not None

    def __repr__(self):
        # Mask email for privacy: j***@example.com
        if self.email and "@" in self.email:
            local, domain = self.email.split("@", 1)
            masked_local = local[0] + "***" if local else "***"
            return f"<User {masked_local}@{domain}>"
        return f"<User {self.id}>"
