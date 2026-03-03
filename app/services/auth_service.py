import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.models.magic_token import MagicToken
from app.services.email_service import email_service
from app.services.patient_service import needs_patient_setup
from app.utils.uuid_utils import ensure_uuid

# ============================================================
# SEÇÃO 1: Operações de Token Mágico
# ============================================================


def cleanup_expired_magic_tokens(db: Session, batch_size: int = 100) -> int:
    """
    Delete expired and used magic tokens.

    This is a lazy cleanup that runs on token creation to prevent
    unbounded database growth. Tokens are deleted in batches to avoid
    long-running transactions.

    Args:
        db: Database session
        batch_size: Maximum number of tokens to delete in one call

    Returns:
        Number of tokens deleted
    """
    cutoff = datetime.now()
    # Get IDs of tokens to delete (with batch limit)
    token_ids = (
        db.query(MagicToken.id)
        .filter(MagicToken.used | (MagicToken.expires_at < cutoff))
        .limit(batch_size)
        .all()
    )

    if not token_ids:
        return 0

    # Delete those specific tokens
    token_ids = [tid[0] for tid in token_ids]
    result = (
        db.query(MagicToken)
        .filter(MagicToken.id.in_(token_ids))
        .delete(synchronize_session=False)
    )
    return result


def _hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.

    Args:
        token: Raw token string

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_magic_token() -> str:
    """Gera um token aleatório seguro para magic links."""
    return secrets.token_urlsafe(32)


def create_magic_token(
    db: Session, user_id, action: str | None = None
) -> Tuple[str, MagicToken]:
    """
    Cria um novo token mágico para um usuário.

    Args:
        db: Sessão do banco de dados
        user_id: UUID do usuário
        action: Ação opcional para redirecionamento

    Returns:
        Tupla (raw_token, MagicToken):
        - raw_token: Token em texto plano (para enviar por email)
        - MagicToken: Objeto ORM (para modificações em testes)
    """
    cleanup_expired_magic_tokens(db)
    raw_token = generate_magic_token()
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now() + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)

    user_id = ensure_uuid(user_id)

    db_token = MagicToken(
        token=token_hash, user_id=user_id, action=action, expires_at=expires_at
    )
    db.add(db_token)
    db.flush()
    return raw_token, db_token


def _get_magic_token(db: Session, token: str) -> Optional[MagicToken]:
    """
    Helper interno: Busca token sem modificá-lo.

    Args:
        db: Sessão do banco de dados
        token: String do token para procurar (texto plano)

    Returns:
        Objeto MagicToken se encontrado e válido, None caso contrário
    """
    token_hash = _hash_token(token)
    return (
        db.query(MagicToken)
        .filter(
            MagicToken.token == token_hash,
            MagicToken.used.is_(False),
            MagicToken.expires_at > datetime.now(),
        )
        .first()
    )


def verify_magic_token(
    db: Session, token: str, mark_used: bool = True
) -> Optional[dict]:
    """
    Verifica um token mágico e opcionalmente marca como usado.

    Args:
        db: Sessão do banco de dados
        token: String do token para verificar
        mark_used: Se True, marca token como usado (default: True)
                  Define como False para pré-validação sem consumo

    Returns:
        Dicionário com user e action se válido, None caso contrário
    """
    db_token = _get_magic_token(db, token)

    if not db_token:
        return None

    # Opcionalmente marca token como usado
    if mark_used:
        db_token.used = True

    # Obter usuário
    user = db.query(User).filter(User.id == db_token.user_id).first()

    return {"user": user, "action": db_token.action}


def send_magic_link(
    email: str, user_name: str, token: str
) -> Tuple[bool, Optional[str]]:
    """Envia um email de magic link para o usuário."""
    magic_link = f"{settings.FRONTEND_URL}/auth/verify#{token}"

    return email_service.send_email(
        to=email,
        subject="Seu link de acesso - SS-54",
        template_name="magic_link.html",
        context={
            "user_name": user_name,
            "magic_link": magic_link,
            "expires_minutes": settings.MAGIC_LINK_EXPIRE_MINUTES,
        },
    )


# ============================================================
# SEÇÃO 2: Operações JWT
# ============================================================


def create_jwt_token(user_id: str) -> str:
    """Cria um token JWT para um usuário autenticado."""
    expires = datetime.now() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode = {"sub": user_id, "exp": expires, "iat": datetime.now()}

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_jwt_token(token: str) -> Optional[str]:
    """Verifica um token JWT e retorna o user_id se válido."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except jwt.InvalidTokenError:
        return None


# ============================================================
# SEÇÃO 3: Operações de Autenticação de Usuário
# ============================================================


def get_or_create_user(db: Session, email: str) -> User:
    """Obtém usuário existente ou cria um novo usuário."""
    user = db.query(User).filter(User.email == email).first()

    if user:
        return user

    # Create new user
    user = User(email=email)
    db.add(user)
    db.flush()  # Flush to get ID
    return user


def initiate_login(
    db: Session, email: str, action: str | None = None
) -> tuple[User, bool]:
    """
    Inicia o processo de login criando e enviando um magic link.
    Retorna tupla (user, is_new_user).
    """
    existing_user = db.query(User).filter(User.email == email).first()
    is_new_user = existing_user is None

    user = get_or_create_user(db, email)

    raw_token, _ = create_magic_token(db, user.id, action)

    email_prefix = email.split("@")[0]
    send_magic_link(user.email, email_prefix, raw_token)

    return user, is_new_user


def complete_login(db: Session, token: str) -> Optional[dict]:
    """
    Completa o login verificando o token mágico.

    Esta é a etapa final do fluxo de autenticação em duas etapas.
    Verifica o token, marca como usado e cria a sessão JWT.

    Args:
        db: Sessão do banco de dados
        token: String do token mágico do link do email

    Returns:
        Dicionário com chaves:
        - user: Objeto User
        - action: Parâmetro de ação opcional para redirecionamento
        - needs_patient_setup: Booleano indicando se usuário não tem pacientes
        - jwt_token: Token de sessão JWT (sempre criado)

        Retorna None se o token for inválido/expirado.
    """
    result = verify_magic_token(db, token)
    if not result or not result["user"]:
        return None

    user = result["user"]

    # Check if user has any patients using patient service
    needs_patient_setup_flag = needs_patient_setup(db, user.id)

    # Update last login
    user.last_login = datetime.now()

    # Create JWT token
    jwt_token = create_jwt_token(str(user.id))

    return {
        "user": user,
        "action": result["action"],
        "needs_patient_setup": needs_patient_setup_flag,
        "jwt_token": jwt_token,
    }
