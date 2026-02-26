from pydantic import BaseModel, computed_field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from app.models.process import ProcessType, ProcessStatus, RequestType
from app.models.document import DocumentType
from app.schemas.patient import PatientBrief
from app.schemas.document import DocumentResponse
from app.schemas.activity_log import ActivityLogResponse
from app.schemas.base import BaseResponseSchema
from app.content import PROCESS_TYPE_TITLES, REQUEST_TYPE_TITLES


class ProcessBase(BaseModel):
    type: ProcessType
    notes: Optional[str] = None
    details: Optional[str] = None


class ProcessResponse(ProcessBase, BaseResponseSchema):
    """
    Schema unificado de resposta de processo com relacionamentos opcionais.
    Funciona para todos os casos de uso - relacionamentos são populados quando carregados ansiosamente.
    """

    id: UUID
    protocol_number: str
    patient_id: UUID
    status: ProcessStatus
    request_type: RequestType
    created_at: datetime
    updated_at: datetime
    authorization_date: Optional[datetime] = None

    patient: Optional[PatientBrief] = None
    documents: List[DocumentResponse] = []
    activities: List[ActivityLogResponse] = []
    admin_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @computed_field
    def type_title(self) -> str:
        type_value = self.type.value if hasattr(self.type, "value") else str(self.type)
        request_value = (
            self.request_type.value
            if hasattr(self.request_type, "value")
            else str(self.request_type)
        )

        process_title = PROCESS_TYPE_TITLES.get(type_value, type_value)
        request_title = REQUEST_TYPE_TITLES.get(request_value, request_value)

        return f"{process_title} - {request_title}"

    @computed_field
    def document_count(self) -> int:
        return len(
            [d for d in self.documents if d.document_type != DocumentType.PDF_COMBINADO]
        )

    @computed_field
    def can_be_deleted(self) -> bool:
        if self.status in ("autorizado", "em_revisao"):
            return False

        reference_date = self.authorization_date or self.created_at
        five_years_later = datetime(
            reference_date.year + 5, reference_date.month, reference_date.day
        )
        return datetime.now() >= five_years_later

    @computed_field
    def document_previews(self) -> List[dict]:
        return [doc.model_dump() for doc in self.documents[:5]]
