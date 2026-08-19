import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.core.time import utcnow
from app.models.enums import UserRole, pg_enum

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class Comment(SQLModel, table=True):
    __tablename__ = "comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_id: uuid.UUID = Field(foreign_key="tickets.id", index=True)
    author_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    author_role: UserRole = Field(
        sa_column=Column(pg_enum(UserRole, "user_role"), nullable=False)
    )
    body: str

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    ticket: "Ticket" = Relationship(back_populates="comments")
    author: "User" = Relationship(back_populates="comments")
