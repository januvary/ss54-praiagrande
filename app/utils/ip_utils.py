"""
IP Address Utilities

Provides utilities for extracting and validating client IP addresses,
with proper proxy header validation to prevent IP spoofing.
"""

import ipaddress
from typing import List, Union
from fastapi import Request

TRUSTED_PROXIES: List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]] = [
    ipaddress.ip_address("127.0.0.1"),
    ipaddress.ip_address("::1"),
]


def is_trusted_proxy(client_ip: str) -> bool:
    """
    Check if a request came from a trusted proxy.

    Only localhost connections are considered trusted proxies,
    as we assume nginx runs on the same server.

    Args:
        client_ip: Direct connection IP address

    Returns:
        True if the IP is a trusted proxy
    """
    try:
        ip = ipaddress.ip_address(client_ip)
        return ip in TRUSTED_PROXIES
    except ValueError:
        return False


def get_client_ip(request: Request) -> str:
    """
    Get the client IP with trusted proxy validation.

    Priority:
    1. If connection is from trusted proxy (localhost) → trust X-Real-IP
    2. Otherwise → use direct connection IP

    This prevents X-Real-IP header spoofing by external attackers.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address (normalized)
    """
    direct_ip = request.client.host if request.client else "unknown"

    if is_trusted_proxy(direct_ip):
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    return direct_ip


def normalize_ip_for_rate_limit(ip: str) -> str:
    """
    Normalize IP address for rate limiting purposes.

    Ensures equivalent IPs (e.g., IPv4 and IPv6 localhost) map to the same
    rate limit bucket, preventing users from getting 2x attempts via dual-stack.

    Normalizations:
    - ::1 (IPv6 localhost) → 127.0.0.1
    - ::ffff:x.x.x.x (IPv4-mapped IPv6) → x.x.x.x

    Args:
        ip: IP address string

    Returns:
        Normalized IP address string
    """
    if not ip or ip == "unknown":
        return ip

    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip

    if isinstance(addr, ipaddress.IPv6Address):
        if addr == ipaddress.IPv6Address("::1"):
            return "127.0.0.1"
        if addr.ipv4_mapped:
            return str(addr.ipv4_mapped)

    return str(addr)
