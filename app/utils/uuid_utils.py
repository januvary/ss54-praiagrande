"""
UUID Utilities - Helper functions for UUID handling.

Provides consistent UUID conversion and validation across the codebase.

Two complementary functions:
- ensure_uuid(): Data conversion (raises ValueError if invalid)
- validate_uuid(): Route validation (raises HTTPException if invalid)
"""

from typing import Union
from uuid import UUID

from fastapi import HTTPException


def ensure_uuid(value: Union[str, UUID]) -> UUID:
    """
    Convert string to UUID if needed.

    This helper eliminates the repetitive pattern of checking if a value
    is a string and converting it to UUID. Use this for internal data
    processing where you want ValueError on invalid input.

    Args:
        value: Either a UUID string or UUID object

    Returns:
        UUID object

    Raises:
        ValueError: If value is an invalid UUID string

    Example:
        >>> ensure_uuid("12345678-1234-5678-1234-567812345678")
        UUID('12345678-1234-5678-1234-567812345678')

        >>> ensure_uuid(UUID("12345678-1234-5678-1234-567812345678"))
        UUID('12345678-1234-5678-1234-567812345678')
    """
    if isinstance(value, str):
        return UUID(value)
    return value


def validate_uuid(id_str: str, entity_name: str = "ID") -> UUID:
    """
    Validate and convert a string to UUID, raising HTTPException for routes.

    This is the route-layer counterpart to ensure_uuid(). Use this in
    FastAPI route handlers where you want HTTPException 400 on invalid input
    instead of ValueError.

    Args:
        id_str: String to convert to UUID
        entity_name: Entity name for error message (e.g., "processo", "documento")

    Returns:
        UUID object

    Raises:
        HTTPException: 400 if the string is not a valid UUID

    Example:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> validate_uuid("invalid", entity_name="processo")
        HTTPException(status_code=400, detail="processo inválido")
    """
    try:
        return UUID(id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{entity_name} inválido")
