"""
Schema base com campos e métodos comuns.
"""

from pydantic import BaseModel, field_serializer


class BaseResponseSchema(BaseModel):
    """
    Schema base para todos os schemas de resposta.
    Fornece serialização de enums para templates.
    """

    @field_serializer("*")
    def serialize_enum(self, v):
        """Serializa campos enum para seus valores string para templates."""
        if hasattr(v, "value"):
            return v.value
        return v
