import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models.enums import TicketCategory, TicketPriority, TicketStatus, UserRole
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketListResponse, TicketRead, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])


async def _get_owned_ticket(
    session: SessionDep, current_user: CurrentUser, ticket_id: uuid.UUID
) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    # Customers get a 404 (not 403) for tickets they don't own, so the API doesn't
    # confirm/deny existence of tickets outside their access.
    if current_user.role == UserRole.CUSTOMER and ticket.customer_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate, session: SessionDep, current_user: CurrentUser
) -> Ticket:
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only customers can open tickets")

    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        customer_id=current_user.id,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    session: SessionDep,
    current_user: CurrentUser,
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = Query(default=None),
    category: TicketCategory | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TicketListResponse:
    conditions = []
    if current_user.role == UserRole.CUSTOMER:
        conditions.append(Ticket.customer_id == current_user.id)
    if status_filter is not None:
        conditions.append(Ticket.status == status_filter)
    if priority is not None:
        conditions.append(Ticket.priority == priority)
    if category is not None:
        conditions.append(Ticket.category == category)
    if search:
        pattern = f"%{search}%"
        conditions.append(or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern)))

    base_query = select(Ticket)
    count_query = select(func.count()).select_from(Ticket)
    if conditions:
        base_query = base_query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total = (await session.exec(count_query)).one()

    result = await session.exec(
        base_query.order_by(Ticket.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return TicketListResponse(items=result.all(), total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> Ticket:
    return await _get_owned_ticket(session, current_user, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: uuid.UUID, payload: TicketUpdate, session: SessionDep, current_user: CurrentUser
) -> Ticket:
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the customer who owns a ticket can edit it"
        )

    ticket = await _get_owned_ticket(session, current_user, ticket_id)
    if ticket.status != TicketStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ticket can only be edited while Open")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> None:
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the customer who owns a ticket can delete it"
        )

    ticket = await _get_owned_ticket(session, current_user, ticket_id)
    if ticket.status != TicketStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ticket can only be deleted while Open")

    await session.delete(ticket)
    await session.commit()
