"""
Centralized template configuration for SS-54.
"""

import os
from fastapi.templating import Jinja2Templates

APP_DIR = os.path.dirname(os.path.dirname(__file__))


def get_templates():
    """
    Get the Jinja2 templates instance with filters registered.
    Call this once at module level in route files.
    """
    templates = Jinja2Templates(
        directory=os.path.join(APP_DIR, "templates"), auto_reload=True
    )
    from app.utils.template_filters import register_filters

    register_filters(templates)
    return templates


templates = get_templates()
