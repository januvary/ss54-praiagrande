"""
Generic filesystem utility functions.

Provides reusable filesystem operations that are not specific to sanitization.
"""

import logging

logger = logging.getLogger(__name__)


def file_exists(file_path: str | None) -> bool:
    """
    Check if a file exists on disk.

    Args:
        file_path: Path to check, or None

    Returns:
        True if file exists, False otherwise (including if path is None)
    """
    if not file_path:
        return False
    from pathlib import Path

    return Path(file_path).exists()


def get_file_if_exists(file_path: str | None) -> str | None:
    """
    Return the file path if it exists, None otherwise.

    Useful for safely checking PDF/document files before use.

    Args:
        file_path: Path to check, or None

    Returns:
        file_path if exists, None otherwise
    """
    return file_path if file_exists(file_path) else None
