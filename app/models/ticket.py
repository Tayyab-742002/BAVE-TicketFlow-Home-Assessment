import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.core.time import utcnow
from app.models.enums import TicketCategory, TicketPriority, TicketStatus

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.user import User


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(index=True)
    description: str
    category: TicketCategory = Field(index=True)
    priority: TicketPriority = Field(index=True)
    status: TicketStatus = Field(default=TicketStatus.OPEN, index=True)

    customer_id: uuid.UUID = Field(foreign_key="users.id", index=True)

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utcnow),
    )

    customer: "User" = Relationship(back_populates="tickets")
    comments: list["Comment"] = Relationship(back_populates="ticket", cascade_delete=True)
