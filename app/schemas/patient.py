from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from uuid import UUID
from typing import Optional
from app.schemas.base import BaseResponseSchema


class PatientBase(BaseModel):
    name: str
    date_of_birth: Optional[date] = None


class PatientResponse(PatientBase, BaseResponseSchema):
    """Resposta completa de paciente com todos os campos"""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientBrief(BaseResponseSchema):
    """Informações breves de paciente para respostas aninhadas"""

    id: UUID
    name: str
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
