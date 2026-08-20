import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import TokenType, decode_token
from app.db.redis import get_redis
from app.db.session import get_session
from app.models.enums import UserRole
from app.models.ticket import Ticket
from app.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        raise credentials_error

    if claims.get("type") != TokenType.ACCESS.value:
        raise credentials_error

    user = await session.get(User, uuid.UUID(claims["sub"]))
    if user is None:
        raise credentials_error

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permissions")
        return user

    return dependency


RequireAgent = Annotated[User, Depends(require_role(UserRole.AGENT))]


async def get_visible_ticket(
    ticket_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    # Customers get a 404 (not 403) for tickets they don't own, so the API doesn't
    # confirm/deny existence of tickets outside their access.
    if current_user.role == UserRole.CUSTOMER and ticket.customer_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


VisibleTicket = Annotated[Ticket, Depends(get_visible_ticket)]


async def get_current_user_ws(websocket: WebSocket, session: AsyncSession) -> User | None:
    """Browser WebSocket clients can't set an Authorization header, so the access
    token travels as a query param instead (?token=...). Closes the socket with a
    4401 app-level code and returns None on any failure rather than raising —
    there's no HTTP response to attach an error to once the handshake is underway."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return None

    try:
        claims = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        await websocket.close(code=4401)
        return None

    if claims.get("type") != TokenType.ACCESS.value:
        await websocket.close(code=4401)
        return None

    user = await session.get(User, uuid.UUID(claims["sub"]))
    if user is None:
        await websocket.close(code=4401)
        return None

    return user
