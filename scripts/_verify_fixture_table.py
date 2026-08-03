"""One-off: verify biv_e2e_deterministic_fixtures table exists."""
import asyncio

from sqlalchemy import text

from app.db.session import get_session_factory, init_db


async def main() -> None:
    await init_db()
    async with get_session_factory()() as session:
        result = await session.execute(
            text("SELECT to_regclass('public.biv_e2e_deterministic_fixtures')"),
        )
        print({"biv_e2e_deterministic_fixtures": result.scalar()})


asyncio.run(main())
