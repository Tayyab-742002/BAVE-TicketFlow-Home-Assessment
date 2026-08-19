from enum import Enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"


class TicketCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    GENERAL = "general"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


def pg_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """Postgres ENUM storing member .value ('open'), not .name ('OPEN')."""
    return SAEnum(enum_cls, name=name, values_callable=lambda x: [e.value for e in x])
