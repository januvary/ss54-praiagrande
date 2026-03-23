from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Obtém um usuário por email.

    Args:
        db: Sessão do banco de dados
        email: Email do usuário

    Returns:
        Objeto User ou None se não encontrado
    """
    return db.query(User).filter(User.email == email).first()


def update_user_email(db: Session, user_id: UUID, new_email: str) -> User:
    """
    Atualiza o email de um usuário.

    Args:
        db: Sessão do banco de dados
        user_id: UUID do usuário
        new_email: Novo email

    Returns:
        Objeto User atualizado

    Raises:
        ValueError: Se o novo email já estiver em uso por outro usuário
    """
    existing_user = (
        db.query(User).filter(User.email == new_email, User.id != user_id).first()
    )

    if existing_user:
        raise ValueError("Email já está em uso por outro usuário")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Usuário não encontrado")

    user.email = new_email
    db.flush()

    return user
