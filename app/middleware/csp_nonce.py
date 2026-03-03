"""
CSP Nonce Middleware
Generates a cryptographically secure nonce for each request.
"""

import secrets
from starlette.middleware.base import BaseHTTPMiddleware


class CSPNonceMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates a CSP nonce for each request.

    The nonce is stored in request.state.csp_nonce and can be used:
    1. In CSP headers (script-src 'nonce-XXX', style-src 'nonce-XXX')
    2. In templates (nonce="{{ csp_nonce }}")
    3. For HTMX configuration (htmx.config.inlineScriptNonce)
    """

    async def dispatch(self, request, call_next):
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        return response
