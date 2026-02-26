"""
Date utility functions for common date operations.
"""

from datetime import datetime, timedelta, date


def get_days_ago(days: int) -> datetime:
    """Returns a datetime object representing N days ago from now."""
    return datetime.now() - timedelta(days=days)


def parse_brazilian_date(date_str: str | None) -> tuple[date | None, list[str]]:
    """
    Parse a date from Brazilian DD/MM/YYYY format.

    Args:
        date_str: Date string in DD/MM/YYYY format, or None

    Returns:
        Tuple of (parsed_date, error_list). Returns (None, []) if date_str is None/empty.
    """
    if not date_str:
        return None, []

    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date(), []
    except ValueError:
        return None, ["Data de nascimento inválida. Use o formato DD/MM/AAAA."]
