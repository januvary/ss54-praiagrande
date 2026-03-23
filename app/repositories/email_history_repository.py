"""
Email History Repository - Lógica centralizada de histórico de emails.

Gerencia operações de banco de dados para a entidade EmailHistory.
"""

from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.email_history import EmailHistory


def get_email_history(db: Session, user_id: UUID) -> List[EmailHistory]:
    """
    Obtém todo o histórico de alterações de email para um usuário.

    Args:
        db: Sessão do banco de dados
        user_id: UUID do usuário

    Returns:
        Lista de objetos EmailHistory, ordenados por data (mais recente primeiro)
    """
    return (
        db.query(EmailHistory)
        .filter(EmailHistory.user_id == user_id)
        .order_by(EmailHistory.changed_at.desc())
        .all()
    )


def log_email_change(
    db: Session,
    user_id: UUID,
    old_email: str,
    new_email: str,
) -> EmailHistory:
    """
    Registra uma alteração de email no histórico.

    Args:
        db: Sessão do banco de dados
        user_id: UUID do usuário
        old_email: Email anterior
        new_email: Novo email

    Returns:
        Objeto EmailHistory criado
    """
    history = EmailHistory(
        user_id=user_id,
        old_email=old_email,
        new_email=new_email,
    )
    db.add(history)
    db.flush()

    return history
