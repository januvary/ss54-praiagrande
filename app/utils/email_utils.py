"""
Email Provider Detection Utilities
Provides server-side email provider detection and mobile-aware deep linking
"""

from typing import Optional, Dict
from fastapi import Request

# Email provider configurations
EMAIL_PROVIDERS = {
    "gmail.com": {
        "name": "Gmail",
        "mobile_url": "googlegmail://",
        "web_url": "https://mail.google.com/",
    },
    "googlemail.com": {
        "name": "Gmail",
        "mobile_url": "googlegmail://",
        "web_url": "https://mail.google.com/",
    },
    "outlook.com": {
        "name": "Outlook",
        "mobile_url": "ms-outlook://",
        "web_url": "https://outlook.live.com/",
    },
    "hotmail.com": {
        "name": "Outlook",
        "mobile_url": "ms-outlook://",
        "web_url": "https://outlook.live.com/",
    },
    "live.com": {
        "name": "Outlook",
        "mobile_url": "ms-outlook://",
        "web_url": "https://outlook.live.com/",
    },
    "msn.com": {
        "name": "Outlook",
        "mobile_url": "ms-outlook://",
        "web_url": "https://outlook.live.com/",
    },
    "yahoo.com": {
        "name": "Yahoo Mail",
        "mobile_url": "ymail://",
        "web_url": "https://mail.yahoo.com/",
    },
    "yahoo.co.uk": {
        "name": "Yahoo Mail",
        "mobile_url": "ymail://",
        "web_url": "https://mail.yahoo.com/",
    },
    "yahoo.fr": {
        "name": "Yahoo Mail",
        "mobile_url": "ymail://",
        "web_url": "https://mail.yahoo.com/",
    },
    "yahoo.de": {
        "name": "Yahoo Mail",
        "mobile_url": "ymail://",
        "web_url": "https://mail.yahoo.com/",
    },
    "yahoo.com.br": {
        "name": "Yahoo Mail",
        "mobile_url": "ymail://",
        "web_url": "https://mail.yahoo.com/",
    },
    "proton.me": {
        "name": "Proton Mail",
        "mobile_url": "protonmail://",
        "web_url": "https://mail.proton.me/",
    },
    "protonmail.com": {
        "name": "Proton Mail",
        "mobile_url": "protonmail://",
        "web_url": "https://mail.proton.me/",
    },
}


def get_email_provider(email: str) -> Optional[Dict[str, str]]:
    """
    Detect email provider from email address.

    Args:
        email: Email address to check

    Returns:
        Provider dict with keys: name, mobile_url, web_url, or None if not supported
    """
    if not email or not isinstance(email, str):
        return None

    # Extract domain from email
    parts = email.split("@")
    if len(parts) != 2:
        return None

    domain = parts[1].lower().strip()

    return EMAIL_PROVIDERS.get(domain)


def get_email_link_url(email: str, request: Request) -> Optional[str]:
    """
    Get appropriate email link URL.

    Always returns webmail URL (works on all devices).

    Args:
        email: Email address
        request: FastAPI Request object (unused but kept for API consistency)

    Returns:
        URL to email inbox (webmail), or None if provider not supported
    """
    provider = get_email_provider(email)

    if not provider:
        return None

    # Always use webmail URL (works on all devices)
    return provider["web_url"]
