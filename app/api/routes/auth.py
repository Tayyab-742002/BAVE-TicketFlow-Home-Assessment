import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import AccessToken, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: SessionDep) -> User:
    existing = await session.exec(select(User).where(User.email == payload.email))
    if existing.first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # Public registration always creates a Customer; the Agent account is seeded, not self-served.
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.CUSTOMER,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
) -> TokenPair:
    result = await session.exec(select(User).where(User.email == form_data.username))
    user = result.first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    return TokenPair(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id, user.role.value),
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh(payload: RefreshRequest, session: SessionDep) -> AccessToken:
    try:
        claims = decode_token(payload.refresh_token)
    except (ExpiredSignatureError, InvalidTokenError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    if claims.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not a refresh token")

    user = await session.get(User, uuid.UUID(claims["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")

    return AccessToken(access_token=create_access_token(user.id, user.role.value))
