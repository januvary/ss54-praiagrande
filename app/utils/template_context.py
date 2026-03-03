"""
Template Context Builder for SS-54 Application

Provides lazy-loaded, cached template context data.
All data from content.py is immutable at runtime and safe to cache globally.

This eliminates redundant dictionary creation on every template render,
improving performance and reducing memory usage.
"""

from typing import Optional, Dict, Any
from fastapi import Request
from app.models.user import User


class TemplateDataContext:
    """
    Singleton cache for immutable template context data.

    All static data from content.py (STATUS_LABELS, VALIDATION_COLORS, etc.)
    is loaded once and cached for the lifetime of the application.
    Request-specific data (csrf_token, user) is added per-request.
    """

    _instance: Optional["TemplateDataContext"] = None
    _static_data: Optional[Dict[str, Any]] = None

    def __new__(cls) -> "TemplateDataContext":
        """Ensure singleton pattern - only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_static_context(cls) -> Dict[str, Any]:
        """
        Get cached static data from content.py (lazy-loaded once).

        This data is immutable and safe to cache globally:
        - Status labels and colors
        - Document type information
        - Process type information
        - Validation colors and labels
        - Site information

        Returns:
            Dictionary with all static template context data
        """
        if cls._static_data is None:
            from app.content import (
                STATUS_LABELS,
                DOCUMENT_TYPE_ORDER,
                DOCUMENT_TYPE_TITLES,
                PROCESS_TYPE_TITLES,
                REQUEST_TYPE_TITLES,
                VALIDATION_COLORS,
                VALIDATION_LABELS,
                COLOR_CLASSES,
                SITE,
                PROCESS_TYPES,
                ORIENTATION,
                COMMON_LABELS,
                ADMIN_SECTION_TITLES,
                EMAIL_ERRORS,
            )

            cls._static_data = {
                "status_labels": STATUS_LABELS,
                "doc_type_order": DOCUMENT_TYPE_ORDER,
                "doc_type_titles": DOCUMENT_TYPE_TITLES,
                "process_type_titles": PROCESS_TYPE_TITLES,
                "request_type_titles": REQUEST_TYPE_TITLES,
                "type_labels": PROCESS_TYPE_TITLES,  # Alias for consistency
                "validation_colors": VALIDATION_COLORS,
                "validation_labels": VALIDATION_LABELS,
                "color_classes": COLOR_CLASSES,
                "site": SITE,
                "process_types": PROCESS_TYPES,
                "orientation": ORIENTATION,
                "common_labels": COMMON_LABELS,
                "admin_section_titles": ADMIN_SECTION_TITLES,
                "email_errors": EMAIL_ERRORS,
            }

        return cls._static_data

    @classmethod
    def build_context(
        cls,
        request: Request,
        user: Optional[User] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build complete template context with static + request-specific data.

        Args:
            request: FastAPI request object
            user: Optional user object for authenticated requests
            extra_context: Optional additional context to merge

        Returns:
            Complete template context dictionary
        """
        # Start with cached static data (copy to avoid mutation)
        context = cls.get_static_context().copy()

        # Add request-specific data
        context.update(
            {
                "request": request,
                "user": user,
                "csrf_token": request.cookies.get("csrf_token", ""),
                "csp_nonce": getattr(request.state, "csp_nonce", ""),
            }
        )

        # Merge any additional context
        if extra_context:
            context.update(extra_context)

        return context
