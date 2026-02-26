"""
Serviço de Limitação de Taxa
Limitação de taxa em memória para endpoints de API.

Para produção, considere usar Redis ou um cache distribuído.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from threading import Lock

from app.utils.ip_utils import normalize_ip_for_rate_limit


@dataclass
class RateLimitEntry:
    """Rastreia contagens de requisições para limitação de taxa."""

    count: int
    window_start: float


class RateLimiter:
    """
    Limitador de taxa simples em memória usando janela deslizante.

    Implementação thread-safe para rastrear limites de requisição.
    """

    def __init__(self):
        self._lock = Lock()
        # Key -> RateLimitEntry mapping
        self._requests: Dict[str, RateLimitEntry] = defaultdict(
            lambda: RateLimitEntry(0, 0)
        )
        self._operation_count = 0  # Track operations since last cleanup

    def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Verifica se uma requisição é permitida sob o limite de taxa.

        Args:
            key: Identificador único (ex: endereço IP ou email)
            max_requests: Máximo de requisições permitidas na janela
            window_seconds: Janela de tempo em segundos

        Returns:
            Tupla de (is_allowed, retry_after_seconds)
        """
        with self._lock:
            self._operation_count += 1

            # Lazy cleanup: every 100 operations, check if cleanup needed
            if self._operation_count >= 100 and len(self._requests) > 1000:
                self._cleanup_old_entries_unlocked(max_age_seconds=7200)  # 2 hours

            current_time = time.time()
            window_start = current_time - window_seconds

            entry = self._requests[key]

            # Reset if outside window
            if entry.window_start < window_start:
                entry.count = 0
                entry.window_start = current_time

            # Check limit
            if entry.count >= max_requests:
                # Calculate retry-after
                retry_after = int(entry.window_start + window_seconds - current_time)
                return False, max(1, retry_after)

            # Increment and allow
            entry.count += 1
            return True, None

    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """Remove entradas antigas para prevenir vazamento de memória."""
        with self._lock:
            self._cleanup_old_entries_unlocked(max_age_seconds)

    def _cleanup_old_entries_unlocked(self, max_age_seconds: int = 3600):
        """
        Remove entradas antigas. Deve ser chamado com lock já mantido.

        Args:
            max_age_seconds: Remove entradas mais antigas que isso (padrão 1 hora)
        """
        current_time = time.time()
        keys_to_remove = [
            key
            for key, entry in self._requests.items()
            if current_time - entry.window_start > max_age_seconds
        ]
        for key in keys_to_remove:
            del self._requests[key]
        self._operation_count = 0


# Global rate limiter instance
login_rate_limiter = RateLimiter()


def check_login_rate_limit(
    identifier: str, identifier_type: str = "email"
) -> Tuple[bool, Optional[int]]:
    """
    Verifica limite de taxa para tentativas de login.

    Limites:
    - Email: 5 requisições por 15 minutos
    - IP: 20 requisições por hora

    Args:
        identifier: Endereço de email ou IP
        identifier_type: "email" ou "ip"

    Returns:
        Tupla de (is_allowed, retry_after_seconds)
    """
    if identifier_type == "email":
        return login_rate_limiter.is_allowed(
            key=f"email:{identifier}", max_requests=5, window_seconds=15 * 60
        )
    else:
        normalized_ip = normalize_ip_for_rate_limit(identifier)
        return login_rate_limiter.is_allowed(
            key=f"ip:{normalized_ip}", max_requests=20, window_seconds=60 * 60
        )


def check_token_verification_rate_limit(ip: str) -> Tuple[bool, Optional[int]]:
    """
    Verifica limite de taxa para tentativas de verificação de magic token.

    Limites: 5 tentativas por IP por 5 minutos.
    Alinhado com limite de email de login para consistência.

    Args:
        ip: Endereço IP do cliente

    Returns:
        Tupla de (is_allowed, retry_after_seconds)
    """
    normalized_ip = normalize_ip_for_rate_limit(ip)
    return login_rate_limiter.is_allowed(
        key=f"token_verify:{normalized_ip}", max_requests=5, window_seconds=5 * 60
    )


def check_admin_login_rate_limit(ip: str) -> Tuple[bool, Optional[int]]:
    """
    Verifica limite de taxa para tentativas de login admin.

    Limites: 5 tentativas por IP por 15 minutos.
    Mesmo limite que login de usuário para consistência.

    Args:
        ip: Endereço IP do cliente

    Returns:
        Tupla de (is_allowed, retry_after_seconds)
    """
    normalized_ip = normalize_ip_for_rate_limit(ip)
    return login_rate_limiter.is_allowed(
        key=f"admin_login:{normalized_ip}", max_requests=5, window_seconds=15 * 60
    )
