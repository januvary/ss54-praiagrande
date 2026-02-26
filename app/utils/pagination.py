"""
Generic pagination utilities for consistent pagination across the application.

This module provides reusable pagination calculation functions that are
independent of any specific domain model.

For domain-specific paginated queries, see the appropriate repository:
- ActivityLog: app.repositories.activity_repository
"""

from typing import TypedDict


class PaginationInfo(TypedDict):
    """
    Pagination metadata returned by pagination functions.

    Attributes:
        page: Current page number (1-indexed)
        per_page: Number of items per page
        total: Total number of items across all pages
        total_pages: Total number of pages
        offset: Offset for database query (0-indexed)
    """

    page: int
    per_page: int
    total: int
    total_pages: int
    offset: int


def calculate_pagination(page: int, per_page: int, total: int) -> PaginationInfo:
    """
    Calculate pagination metadata from total count.

    This is a pure function that performs pagination math without
    any database queries or model dependencies.

    Args:
        page: Current page number (1-indexed, must be >= 1)
        per_page: Items per page (must be >= 1)
        total: Total number of items (must be >= 0)

    Returns:
        PaginationInfo dict with calculated metadata

    Example:
        >>> pagination = calculate_pagination(page=2, per_page=10, total=95)
        >>> pagination["total_pages"]
        10
        >>> pagination["offset"]
        10
        >>> pagination["page"]
        2

    Note:
        - Empty result sets (total=0) return total_pages=1, not 0
        - Ceiling division ensures partial pages are counted
    """
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    offset = (page - 1) * per_page

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "offset": offset,
    }
