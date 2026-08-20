import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

ALLOWED_EVENT_TYPES = {"ticket.created", "ticket.status_changed"}


class WebhookRegistrationCreate(BaseModel):
    url: HttpUrl
    event_types: list[str] = Field(min_length=1)

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, value: list[str]) -> list[str]:
        invalid = set(value) - ALLOWED_EVENT_TYPES
        if invalid:
            raise ValueError(f"Unsupported event types: {sorted(invalid)}")
        return value


class WebhookRegistrationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    agent_id: uuid.UUID
    url: str
    secret: str
    event_types: list[str]
    is_active: bool
    created_at: datetime
