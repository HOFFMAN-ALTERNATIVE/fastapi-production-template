import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Item
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate, Page

router = APIRouter(prefix="/items", tags=["items"])


async def _owned(session: SessionDep, user: CurrentUser, item_id: uuid.UUID) -> Item:
    item = await session.get(Item, item_id)
    if item is None or item.owner_id != user.id:  # don't leak existence of others' items
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.get("", response_model=Page[ItemRead])
async def list_items(
    session: SessionDep,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ItemRead]:
    base = select(Item).where(Item.owner_id == user.id)
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = await session.scalars(
        base.order_by(Item.created_at.desc(), Item.id).limit(limit).offset(offset)
    )
    return Page[ItemRead](
        items=[ItemRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(body: ItemCreate, session: SessionDep, user: CurrentUser) -> Item:
    item = Item(**body.model_dump(), owner_id=user.id)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> Item:
    return await _owned(session, user, item_id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: uuid.UUID, body: ItemUpdate, session: SessionDep, user: CurrentUser
) -> Item:
    item = await _owned(session, user, item_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> None:
    item = await _owned(session, user, item_id)
    await session.delete(item)
    await session.commit()
