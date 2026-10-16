import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_session
from app.models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(session: SessionDep, token: Annotated[str, Depends(oauth2)]) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode_token(token, "access")
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, ValueError):
        raise unauthorized from None
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
