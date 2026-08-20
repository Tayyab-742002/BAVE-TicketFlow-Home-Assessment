import uuid
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._ticket_rooms: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self._dashboard_room: set[WebSocket] = set()

    async def connect_to_ticket(self, ticket_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._ticket_rooms[ticket_id].add(websocket)

    def disconnect_from_ticket(self, ticket_id: uuid.UUID, websocket: WebSocket) -> None:
        self._ticket_rooms[ticket_id].discard(websocket)
        if not self._ticket_rooms[ticket_id]:
            del self._ticket_rooms[ticket_id]

    async def connect_to_dashboard(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._dashboard_room.add(websocket)

    def disconnect_from_dashboard(self, websocket: WebSocket) -> None:
        self._dashboard_room.discard(websocket)

    async def broadcast_to_ticket(self, ticket_id: uuid.UUID, message: dict[str, Any]) -> None:
        for connection in list(self._ticket_rooms.get(ticket_id, ())):
            await self._safe_send(connection, message)

    async def broadcast_to_dashboard(self, message: dict[str, Any]) -> None:
        for connection in list(self._dashboard_room):
            await self._safe_send(connection, message)

    async def _safe_send(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            # The connection's own receive loop will detect the disconnect and
            # clean up its room membership; a failed send here is not fatal.
            pass


manager = ConnectionManager()
