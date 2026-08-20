import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class CommentCreate(BaseModel):
    model_config = {
        "json_schema_extra": {"examples": [{"body": "Thanks for reporting — looking into this now."}]}
    }

    body: str = Field(min_length=1)


class CommentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    author_role: UserRole
    body: str
    created_at: datetime
