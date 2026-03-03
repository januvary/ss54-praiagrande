"""
Template Helper Functions for SS-54 Application

Provides simplified access to cached template context.
Static data is lazy-loaded and cached for optimal performance.
"""

from typing import Optional, Any
from fastapi import Request
from app.models.user import User
from app.models.patient import Patient
from app.utils.template_config import templates


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    user: Optional[User] = None,
    patient: Optional[Patient] = None,
    is_admin: bool = False,
):
    common_context = get_common_context(request, user)

    if patient:
        common_context["current_patient"] = patient

    if is_admin:
        from app.content import STATUS_INFO

        common_context["status_info"] = STATUS_INFO

    common_context.update(context)

    # Remove "request" from context since it's passed as first argument in new signature
    common_context.pop("request", None)

    # Pass context as dict, not unpacked (new signature handles request separately)
    return templates.TemplateResponse(request, template_name, common_context)


def get_common_context(request: Request, user: Optional[User] = None) -> dict:
    """
    Build common template context for all routes using cached data.

    This function now uses the TemplateDataContext class which caches
    all immutable data from content.py, eliminating redundant dictionary
    creation on every request.

    Args:
        request: FastAPI request object
        user: Optional user object for authenticated requests

    Returns:
        Dictionary with common template variables (static + request-specific)
    """
    from app.utils.template_context import TemplateDataContext

    return TemplateDataContext.build_context(request, user)


def convert_enums_to_values(obj: Any) -> Any:
    """
    Recursively convert enum objects to their string values for templates.

    This ensures that enum values can be properly serialized and used in
    Jinja2 templates without needing to call .value everywhere.

    Args:
        obj: Any object (dict, list, enum, primitive)

    Returns:
        Object with all enums converted to their string values
    """
    if isinstance(obj, dict):
        return {k: convert_enums_to_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_enums_to_values(item) for item in obj]
    if hasattr(obj, "value"):  # Enum
        return obj.value
    return obj
