"""Delete ephemeral owner preview account by email (PRODUCT-01.5 security cleanup)."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import delete, select

from app.db.models import UserTable
from app.db.models.browser_session import BrowserSessionTable
from app.db.session import get_session_factory
from app.services.users_service import UserService


async def delete_by_email(email: str) -> bool:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserTable).where(UserTable.email == email.strip().lower())
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        await session.execute(
            delete(BrowserSessionTable).where(BrowserSessionTable.user_id == user.id)
        )
        service = UserService(session)
        deleted = await service.delete(user.id)
        await session.commit()
        return deleted


def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else "owner.slice-e.preview@marketsynth.local"
    deleted = asyncio.run(delete_by_email(email))
    if deleted:
        print(f"deleted preview account: {email}")
    else:
        print(f"preview account not found: {email}")


if __name__ == "__main__":
    main()
