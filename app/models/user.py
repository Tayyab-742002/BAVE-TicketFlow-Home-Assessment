import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.core.time import utcnow
from app.models.enums import UserRole, pg_enum

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.ticket import Ticket
    from app.models.webhook import WebhookRegistration


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str
    role: UserRole = Field(
        sa_column=Column(pg_enum(UserRole, "user_role"), nullable=False, index=True)
    )
    full_name: str

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utcnow),
    )

    tickets: list["Ticket"] = Relationship(back_populates="customer")
    comments: list["Comment"] = Relationship(back_populates="author")
    webhook_registrations: list["WebhookRegistration"] = Relationship(back_populates="agent")
