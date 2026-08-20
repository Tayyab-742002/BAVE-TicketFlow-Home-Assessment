import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TicketCategory, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Can't access my invoice",
                    "description": "The invoice PDF link in my email returns a 404.",
                    "category": "billing",
                    "priority": "high",
                }
            ]
        }
    }

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: TicketCategory
    priority: TicketPriority


class TicketUpdate(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"priority": "medium"}]}}

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    category: TicketCategory | None = None
    priority: TicketPriority | None = None


class TicketStatusUpdate(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"status": "in_progress"}]}}

    status: TicketStatus


class TicketRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    customer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: list[TicketRead]
    total: int
    page: int
    page_size: int
