from app.models.enums import TicketStatus
from app.models.ticket import Ticket

ALLOWED_STATUS_TRANSITIONS: dict[TicketStatus, TicketStatus] = {
    TicketStatus.OPEN: TicketStatus.IN_PROGRESS,
    TicketStatus.IN_PROGRESS: TicketStatus.RESOLVED,
    TicketStatus.RESOLVED: TicketStatus.CLOSED,
}


class InvalidStatusTransition(Exception):
    def __init__(self, current: TicketStatus, requested: TicketStatus) -> None:
        self.current = current
        self.requested = requested
        super().__init__(f"Cannot move ticket from {current.value} to {requested.value}")


def apply_status_transition(ticket: Ticket, new_status: TicketStatus) -> Ticket:
    if ALLOWED_STATUS_TRANSITIONS.get(ticket.status) != new_status:
        raise InvalidStatusTransition(ticket.status, new_status)
    ticket.status = new_status
    return ticket
