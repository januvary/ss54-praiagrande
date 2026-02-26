"""
Security Utilities - URL validation and sanitization for security.

This module provides security-focused utilities to prevent common
web vulnerabilities, particularly open redirect attacks.

Functions:
- is_safe_redirect: Validate that a redirect URL is safe (internal only)
- sanitize_redirect: Sanitize a redirect URL, returning a safe default if unsafe
"""

from typing import List

DANGEROUS_URL_PREFIXES: List[str] = [
    "/http:",
    "/https:",
    "/ftp:",
    "javascript:",
    "/javascript:",
]


def is_safe_redirect(url: str) -> bool:
    """
    Check if a redirect URL is safe (internal only).

    Prevents open redirect attacks by ensuring the URL:
    - Is relative (starts with /)
    - Is not protocol-relative (doesn't start with //)
    - Doesn't contain encoded protocol prefixes

    Args:
        url: The URL to validate

    Returns:
        True if the URL is safe for redirection, False otherwise

    Examples:
        >>> is_safe_redirect("/admin")
        True
        >>> is_safe_redirect("//evil.com")
        False
        >>> is_safe_redirect("https://evil.com")
        False
        >>> is_safe_redirect("/path?next=https://evil.com")
        False
    """
    if not url:
        return False

    url = url.strip()

    if not url.startswith("/"):
        return False

    if url.startswith("//"):
        return False

    if url.startswith("/\\"):
        return False

    lower_url = url.lower()
    for prefix in DANGEROUS_URL_PREFIXES:
        if prefix in lower_url:
            return False

    return True


def sanitize_redirect(url: str, default: str = "/admin") -> str:
    """
    Sanitize a redirect URL, returning a safe default if unsafe.

    Convenience function that wraps is_safe_redirect() for direct use
    in redirections.

    Args:
        url: The URL to sanitize
        default: Default URL to return if unsafe (default: "/admin")

    Returns:
        Safe URL for redirection, or default URL if the original is unsafe

    Examples:
        >>> sanitize_redirect("/admin/users")
        '/admin/users'
        >>> sanitize_redirect("https://evil.com")
        '/admin'
        >>> sanitize_redirect("//evil.com", default="/home")
        '/home'
    """
    return url if is_safe_redirect(url) else default
