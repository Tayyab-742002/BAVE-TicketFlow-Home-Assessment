import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

ALLOWED_EVENT_TYPES = {"ticket.created", "ticket.status_changed"}


class WebhookRegistrationCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://webhook.site/your-unique-id",
                    "event_types": ["ticket.created", "ticket.status_changed"],
                }
            ]
        }
    }

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


class WebhookDeliveryRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    webhook_registration_id: uuid.UUID
    event_type: str
    payload: dict[str, Any]
    response_status_code: int | None
    success: bool
    idempotency_key: str | None
    attempt_number: int
    attempted_at: datetime
