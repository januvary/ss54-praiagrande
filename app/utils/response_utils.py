"""
Utilitários de resposta HTTP para o SS-54.

Este módulo contém funções auxiliares para manipulação de respostas HTTP.
"""

from fastapi.responses import RedirectResponse

from app.config import settings


def set_cookie(
    response: RedirectResponse,
    key: str,
    value: str,
    max_age_days: int = 7,
) -> RedirectResponse:
    """
    Define um cookie HTTP seguro em uma resposta de redirecionamento.

    Configura cookies com atributos de segurança:
    - HttpOnly: Protege contra acesso via JavaScript (XSS)
    - Secure: Apenas transmitido via HTTPS em produção
    - SameSite=Strict: Protege contra CSRF

    Args:
        response: O RedirectResponse para definir o cookie
        key: Nome do cookie
        value: Valor do cookie
        max_age_days: Idade máxima do cookie em dias (padrão: 7)

    Returns:
        A mesma resposta com o cookie definido
    """
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=60 * 60 * 24 * max_age_days,
    )
    return response
