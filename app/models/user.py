import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.item import Item


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    items: Mapped[list["Item"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
