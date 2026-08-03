"""Auth service — API key lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.api_key import ApiKeyTable
from app.db.models.user import UserTable
from app.db.repositories.api_key_repo import ApiKeyRepository
from app.db.repositories.user_repo import UserRepository
from app.security.auth import KEY_PREFIX_LENGTH, generate_api_key, verify_api_key
from app.services.transaction import transactional


@dataclass(frozen=True)
class CreatedApiKey:
    api_key: ApiKeyTable
    plain_key: str


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._api_keys = ApiKeyRepository(session)
        self._users = UserRepository(session)

    async def create_api_key(self, user_id: UUID, name: str) -> CreatedApiKey:
        plain_key, prefix, key_hash = generate_api_key()
        row = ApiKeyTable(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=prefix,
            is_active=True,
        )
        async with transactional(self._session):
            created = await self._api_keys.create(row)
        return CreatedApiKey(api_key=created, plain_key=plain_key)

    async def authenticate_api_key(self, plain_key: str) -> tuple[UserTable, ApiKeyTable] | None:
        if not plain_key.startswith("bfz_") or len(plain_key) < KEY_PREFIX_LENGTH:
            return None

        prefix = plain_key[:KEY_PREFIX_LENGTH]
        api_key = await self._api_keys.get_by_prefix(prefix)
        if api_key is None:
            return None
        if not api_key.is_active or api_key.revoked_at is not None:
            return None
        if not verify_api_key(plain_key, api_key.key_hash):
            return None

        user = await self._users.get_by_id(api_key.user_id)
        if user is None:
            return None

        async with transactional(self._session):
            api_key.last_used_at = utc_now()
            await self._api_keys.update(api_key)

        return user, api_key

    async def revoke_api_key(self, api_key_id: UUID, user_id: UUID) -> bool:
        row = await self._api_keys.get_by_id_for_user(api_key_id, user_id)
        if row is None or row.revoked_at is not None:
            return False

        async with transactional(self._session):
            row.is_active = False
            row.revoked_at = utc_now()
            await self._api_keys.update(row)
        return True

    async def list_api_keys(self, user_id: UUID) -> list[ApiKeyTable]:
        return await self._api_keys.list_by_user(user_id)
