from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional, Any
from app.schemas.base import BaseResponseSchema


class ActivityLogBase(BaseModel):
    action: str
    description: str
    extra_data: Optional[dict[str, Any]] = None


class ActivityLogResponse(ActivityLogBase, BaseResponseSchema):
    id: UUID
    process_id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
