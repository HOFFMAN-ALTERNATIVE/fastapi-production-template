import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.security import (
    InvalidTokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.user import RefreshRequest, TokenPair, UserCreate, UserRead
from app.services.rate_limit import RateLimiter
from app.services.redis import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

# Defence against user enumeration: verify a dummy hash when the user is unknown.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, session: SessionDep) -> User:
    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> TokenPair:
    s = get_settings()
    limiter = RateLimiter(get_redis(), s.login_rate_limit, s.login_rate_window_seconds, "login")
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{form.username.lower()}"
    allowed, retry_after = await limiter.hit(key)
    if not allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many login attempts",
            headers={"Retry-After": str(retry_after)},
        )

    user = await session.scalar(select(User).where(User.email == form.username.lower()))
    valid = verify_password(form.password, user.hashed_password if user else _DUMMY_HASH)
    if not user or not valid or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    await limiter.reset(key)
    return _tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: SessionDep) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token, "refresh")
        user = await session.get(User, uuid.UUID(payload["sub"]))
    except (InvalidTokenError, ValueError):
        user = None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
