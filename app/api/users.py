"""Users CRUD API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.mappers import user_to_contract
from app.schemas.contracts import User
from app.schemas.crud import UserCreate, UserUpdate
from app.services.users_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    service = UserService(session)
    created = await service.create(body)
    return user_to_contract(created)


@router.get("", response_model=list[User])
async def list_users(
    session: AsyncSession = Depends(get_session),
    offset: int = 0,
    limit: int = 100,
) -> list[User]:
    service = UserService(session)
    rows = await service.list(offset=offset, limit=limit)
    return [user_to_contract(row) for row in rows]


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> User:
    service = UserService(session)
    row = await service.get_by_id(user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_to_contract(row)


@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> User:
    service = UserService(session)
    updated = await service.update(user_id, body)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_to_contract(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    service = UserService(session)
    deleted = await service.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
