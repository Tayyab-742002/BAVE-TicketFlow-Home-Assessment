from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_
from sqlmodel import select

from app.api.deps import (
    CurrentUser,
    RedisDep,
    RequireAgent,
    SessionDep,
    VisibleTicket,
    rate_limit_by_user,
)
from app.models.enums import TicketCategory, TicketPriority, TicketStatus, UserRole
from app.models.ticket import Ticket
from app.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketRead,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services.cache_service import (
    TICKET_LIST_TTL_SECONDS,
    build_ticket_list_cache_key,
    get_cached,
    invalidate_ticket_caches,
    set_cached,
)
from app.services.ticket_service import InvalidStatusTransition, apply_status_transition
from app.services.webhook_service import dispatch_event
from app.services.websocket_manager import manager

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_by_user("ticket_create", limit=30, window_seconds=60))],
)
async def create_ticket(
    payload: TicketCreate,
    session: SessionDep,
    redis: RedisDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
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
    await invalidate_ticket_caches(redis)

    background_tasks.add_task(
        dispatch_event, "ticket.created", TicketRead.model_validate(ticket).model_dump(mode="json")
    )

    return ticket


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    session: SessionDep,
    redis: RedisDep,
    current_user: CurrentUser,
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = Query(default=None),
    category: TicketCategory | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TicketListResponse:
    cache_key = build_ticket_list_cache_key(
        role=current_user.role.value,
        customer_id=str(current_user.id) if current_user.role == UserRole.CUSTOMER else None,
        status=status_filter,
        priority=priority,
        category=category,
        search=search,
        page=page,
        page_size=page_size,
    )
    cached = await get_cached(redis, cache_key)
    if cached is not None:
        return TicketListResponse.model_validate(cached)

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

    response = TicketListResponse(items=result.all(), total=total, page=page, page_size=page_size)
    await set_cached(redis, cache_key, response.model_dump(mode="json"), TICKET_LIST_TTL_SECONDS)
    return response


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket: VisibleTicket) -> Ticket:
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketRead)
async def change_ticket_status(
    payload: TicketStatusUpdate,
    ticket: VisibleTicket,
    session: SessionDep,
    redis: RedisDep,
    agent: RequireAgent,
    background_tasks: BackgroundTasks,
) -> Ticket:
    try:
        apply_status_transition(ticket, payload.status)
    except InvalidStatusTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    await invalidate_ticket_caches(redis)

    ticket_data = TicketRead.model_validate(ticket).model_dump(mode="json")
    ws_event = {"event": "ticket.status_changed", "ticket_id": str(ticket.id), "data": ticket_data}
    await manager.broadcast_to_ticket(ticket.id, ws_event)
    await manager.broadcast_to_dashboard(ws_event)

    background_tasks.add_task(dispatch_event, "ticket.status_changed", ticket_data)

    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    payload: TicketUpdate,
    ticket: VisibleTicket,
    session: SessionDep,
    redis: RedisDep,
    current_user: CurrentUser,
) -> Ticket:
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the customer who owns a ticket can edit it"
        )

    if ticket.status != TicketStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ticket can only be edited while Open")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    await invalidate_ticket_caches(redis)
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket: VisibleTicket, session: SessionDep, redis: RedisDep, current_user: CurrentUser
) -> None:
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the customer who owns a ticket can delete it"
        )

    if ticket.status != TicketStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ticket can only be deleted while Open")

    await session.delete(ticket)
    await session.commit()
    await invalidate_ticket_caches(redis)
