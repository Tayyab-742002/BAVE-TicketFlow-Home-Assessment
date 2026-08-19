import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.core.time import utcnow

if TYPE_CHECKING:
    from app.models.user import User


class WebhookRegistration(SQLModel, table=True):
    __tablename__ = "webhook_registrations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    url: str
    secret: str
    event_types: list[str] = Field(sa_column=Column(JSON, nullable=False))
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    agent: "User" = Relationship(back_populates="webhook_registrations")
    deliveries: list["WebhookDelivery"] = Relationship(
        back_populates="webhook_registration", cascade_delete=True
    )


class WebhookDelivery(SQLModel, table=True):
    __tablename__ = "webhook_deliveries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    webhook_registration_id: uuid.UUID = Field(
        foreign_key="webhook_registrations.id", index=True
    )
    event_type: str = Field(index=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    response_status_code: int | None = None
    success: bool = Field(default=False, index=True)

    attempted_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    webhook_registration: "WebhookRegistration" = Relationship(back_populates="deliveries")
