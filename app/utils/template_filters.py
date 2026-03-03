"""
Filtros de template Jinja2 compartilhados para aplicação SS-54.
"""

from datetime import datetime


def date_filter(value, format_string="%d/%m/%Y"):
    """Formata datetime para string (usa hora local do sistema)"""
    if value == "now":
        value = datetime.now()
    if value:
        # Handle ISO format strings from JSON serialization
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value  # Return as-is if parsing fails
        return value.strftime(format_string)
    return ""


def filesizeformat(value):
    """Formata tamanho de arquivo para string legível"""
    if value is None:
        return "0 B"
    value = int(value)
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def uuid_truncate(value, length=8):
    """Trunca UUID mostrando apenas os primeiros caracteres"""
    if value is None:
        return ""
    value_str = str(value)
    if len(value_str) > length:
        return value_str[:length] + "..."
    return value_str


def phone_format(value):
    """Format Brazilian phone numbers: (XX) XXXXX-XXXX or (XX) XXXX-XXXX"""
    if not value:
        return ""
    digits = "".join(filter(str.isdigit, str(value)))
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return value


def register_filters(templates):
    """
    Registra filtros Jinja2 customizados em uma instância Jinja2Templates.

    Uso:
        from app.utils.template_filters import register_filters
        templates = Jinja2Templates(directory="templates")
        register_filters(templates)
    """
    templates.env.filters["date"] = date_filter
    templates.env.filters["filesizeformat"] = filesizeformat
    templates.env.filters["uuid_truncate"] = uuid_truncate
    templates.env.filters["phone_format"] = phone_format
    templates.env.filters["min"] = min
