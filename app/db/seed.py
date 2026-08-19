import asyncio

from sqlmodel import select

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.enums import UserRole
from app.models.user import User

SEED_AGENT_EMAIL = "agent@ticketflow.dev"
SEED_AGENT_PASSWORD = "AgentPass123!"


async def seed_agent() -> None:
    async with async_session_factory() as session:
        result = await session.exec(select(User).where(User.email == SEED_AGENT_EMAIL))
        if result.first() is not None:
            print(f"Agent already seeded: {SEED_AGENT_EMAIL}")
            return

        agent = User(
            email=SEED_AGENT_EMAIL,
            hashed_password=hash_password(SEED_AGENT_PASSWORD),
            full_name="Support Agent",
            role=UserRole.AGENT,
        )
        session.add(agent)
        await session.commit()
        print(f"Seeded agent: {SEED_AGENT_EMAIL} / {SEED_AGENT_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed_agent())
