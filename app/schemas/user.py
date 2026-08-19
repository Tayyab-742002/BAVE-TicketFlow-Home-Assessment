import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import UserRole


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    created_at: datetime
