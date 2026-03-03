"""
Middleware de Lista Branca de IP de Admin
Protege rotas /admin/* permitindo acesso apenas de IPs autorizados.
Retorna 404 Not Found para IPs não autorizados (por segurança, para não revelar a existência do painel admin).

Suporta:
- IPv4 e IPv6
- CIDR notation (ex: 192.168.1.0/24)
- Normalização automática de IPs
- Validação de proxy confiável
"""

import ipaddress
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import List, Union
from app.config import settings
from app.utils.ip_utils import get_client_ip

logger = logging.getLogger(__name__)


class AdminWhitelistMiddleware:
    """
    Middleware que restringe acesso a rotas /admin/* apenas a IPs autorizados.

    MODELO DE SEGURANÇA:
    - Acesso público via domínio/nginx → BLOQUEADO (IP não está na whitelist)
    - Acesso localhost (direto ou túnel SSH) → PERMITIDO (se IP na whitelist)

    Métodos de Acesso de Admin:
    1. Túnel SSH: ssh -L 8000:localhost:8000 user@server
       Então navegar: http://localhost:8000/admin

    2. Acesso direto ao servidor: curl http://localhost:8000/admin

    3. Console do servidor: Navegador no servidor para http://localhost:8000/admin

    IPs configurados via variável de ambiente ADMIN_ALLOWED_IPS.
    Suporta IPv4, IPv6 e CIDR notation.
    Padrão: "127.0.0.1,::1" (localhost IPv4 e IPv6)

    IMPORTANTE: Nginx deve ser configurado para definir header X-Real-IP.
    O header X-Real-IP só é confiável se a requisição vier de um proxy confiável (localhost).
    """

    def __init__(self, app):
        self.app = app
        self.allowed_ips = self._parse_allowed_ips()

    def _parse_allowed_ips(
        self,
    ) -> List[
        Union[
            ipaddress.IPv4Network,
            ipaddress.IPv6Network,
            ipaddress.IPv4Address,
            ipaddress.IPv6Address,
        ]
    ]:
        """
        Analisa IPs/CIDRs separados por vírgula da configuração.

        Suporta:
        - IPv4: 127.0.0.1
        - IPv6: ::1, 2001:db8::1
        - CIDR IPv4: 192.168.1.0/24
        - CIDR IPv6: 2001:db8::/32

        Returns:
            Lista de endereços IP ou redes CIDR normalizadas
        """
        ips_str = getattr(settings, "ADMIN_ALLOWED_IPS", "127.0.0.1,::1")
        allowed: List[
            Union[
                ipaddress.IPv4Network,
                ipaddress.IPv6Network,
                ipaddress.IPv4Address,
                ipaddress.IPv6Address,
            ]
        ] = []

        for entry in ips_str.split(","):
            entry = entry.strip()
            if not entry:
                continue

            try:
                if "/" in entry:
                    # CIDR notation - parse as network
                    allowed.append(ipaddress.ip_network(entry, strict=False))
                else:
                    # Single IP address
                    allowed.append(ipaddress.ip_address(entry))
            except ValueError as e:
                logger.warning(f"Invalid IP/CIDR in ADMIN_ALLOWED_IPS: '{entry}' - {e}")

        if not allowed:
            logger.warning(
                "No valid IPs in ADMIN_ALLOWED_IPS, defaulting to localhost only"
            )
            allowed = [
                ipaddress.ip_address("127.0.0.1"),
                ipaddress.ip_address("::1"),
            ]

        logger.info(f"Admin whitelist configured with {len(allowed)} IP/range(s)")
        return allowed

    def _is_ip_allowed(self, client_ip: str) -> bool:
        """
        Verifica se um IP está na whitelist.

        Suporta matching contra:
        - Endereços IP individuais (IPv4/IPv6)
        - Redes CIDR (IPv4/IPv6)

        Args:
            client_ip: IP do cliente (string)

        Returns:
            True se o IP está autorizado
        """
        try:
            ip = ipaddress.ip_address(client_ip)
        except ValueError:
            logger.warning(f"Invalid client IP format: '{client_ip}'")
            return False

        for allowed in self.allowed_ips:
            if isinstance(allowed, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                # CIDR matching - check if IP is in network
                if ip in allowed:
                    return True
            else:
                # Direct IP matching
                if ip == allowed:
                    return True

        return False

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Only check /admin/* routes
        if path.startswith("/admin"):
            request = Request(scope, receive)
            client_ip = get_client_ip(request)

            if not self._is_ip_allowed(client_ip):
                logger.info(f"Blocked admin access attempt from IP: {client_ip}")
                response = JSONResponse(
                    content={"detail": "Not Found"},
                    status_code=404,
                )
                await response(scope, receive, send)
                return

        # Allow request through
        await self.app(scope, receive, send)
