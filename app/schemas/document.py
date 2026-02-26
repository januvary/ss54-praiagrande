from pydantic import BaseModel, computed_field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.models.document import DocumentType, ValidationStatus
from app.schemas.base import BaseResponseSchema

# Note: DOCUMENT_TYPE_TITLES is defined in app/content.py


class DocumentBase(BaseModel):
    document_type: DocumentType


class DocumentResponse(DocumentBase, BaseResponseSchema):
    """
    Resposta unificada de documento - inclui todos os campos para templates.
    Usado para toda serialização de documentos em respostas.
    """

    id: UUID
    process_id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    validation_status: ValidationStatus
    validation_notes: Optional[str] = None
    uploaded_at: datetime
    validated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def type_value(self) -> str:
        """Obtém tipo de documento como valor string para buscas em templates"""
        return (
            self.document_type.value
            if hasattr(self.document_type, "value")
            else str(self.document_type)
        )
