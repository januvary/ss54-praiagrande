from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.schemas.base import BaseResponseSchema


class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None


class UserResponse(UserBase, BaseResponseSchema):
    """Resposta completa de usuário com todos os campos"""

    id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
