import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user_ws
from app.db.session import async_session_factory
from app.models.enums import UserRole
from app.models.ticket import Ticket
from app.services.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/tickets/{ticket_id}")
async def ticket_ws(websocket: WebSocket, ticket_id: uuid.UUID) -> None:
    # Session is scoped to just the handshake check, not the whole (possibly
    # long-lived) connection, so an idle subscriber doesn't hold a pooled
    # DB connection for the duration.
    async with async_session_factory() as session:
        user = await get_current_user_ws(websocket, session)
        if user is None:
            return

        ticket = await session.get(Ticket, ticket_id)
        if ticket is None or (
            user.role == UserRole.CUSTOMER and ticket.customer_id != user.id
        ):
            await websocket.close(code=4404)
            return

    await manager.connect_to_ticket(ticket_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_from_ticket(ticket_id, websocket)


@router.websocket("/dashboard")
async def dashboard_ws(websocket: WebSocket) -> None:
    async with async_session_factory() as session:
        user = await get_current_user_ws(websocket, session)
        if user is None:
            return

        if user.role != UserRole.AGENT:
            await websocket.close(code=4403)
            return

    await manager.connect_to_dashboard(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_from_dashboard(websocket)
